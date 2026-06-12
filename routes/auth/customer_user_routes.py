from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
import jwt
from sqlalchemy.orm.attributes import flag_modified
import os
from datetime import datetime, timedelta

from db import get_db
from models.auth.customer_user_models import CustomerUser
from services.auth.customer.customer_id_generator import generate_customer_id
from services.auth.customer.profile_photo_upload import upload_profile_photo

VALID_CUSTOMER_STATUSES = {"active", "suspended", "terminated"}

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# Pydantic Request Models
class PhoneCheckRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to check")

class SendOTPRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to send OTP to")

class AddressInput(BaseModel):
    address_1: Optional[str] = Field(None, description="Primary address line")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    street_address: str = Field(..., description="Street address")


class PaginatedCustomerResponse(BaseModel):
    total: int = Field(..., description="Total number of customers")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    data: List[dict] = Field(..., description="List of customers")


def normalize_customer_status(status: Optional[str]) -> str:
    normalized_status = (status or "active").strip().lower()

    if normalized_status not in VALID_CUSTOMER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="status must be one of: active, suspended, or terminated"
        )

    return normalized_status


def build_saved_address(address_data: AddressInput, address_id: int) -> dict:
    address_1 = address_data.address_1.strip() if address_data.address_1 else ""

    if not address_1:
        raise HTTPException(status_code=400, detail="address_1 is required")

    return {
        "id": address_id,
        "address_1": address_1,
        "latitude": address_data.latitude,
        "longitude": address_data.longitude,
        "street_address": address_data.street_address.strip(),
        "created_at": datetime.utcnow().isoformat()
    }

class VerifyOTPRequest(BaseModel):
    token: str = Field(..., description="Firebase ID token")
    phone_number: str = Field(..., description="Phone number")
    full_name: Optional[str] = Field(None, description="Full name (required for signup)")
    email: Optional[str] = Field(None, description="Email address")
    alternative_phone_no: Optional[str] = Field(None, description="Alternative phone number")
    saved_addresses: Optional[List[dict]] = Field(None, description="List of saved addresses")
    status: Optional[str] = Field("active", description="Customer status: active, suspended, or terminated")

router = APIRouter(prefix="/customers", tags=["Customer Auth"])


@router.get("/get-all")
async def get_all_customers(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get all customers with pagination
    
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Number of items per page (default: 10, max: 100)
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    # Get total count
    total_count = db.query(CustomerUser).count()
    
    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Fetch paginated results
    customers = db.query(CustomerUser).offset(offset).limit(limit).all()
    
    # Convert to dict
    customers_data = [customer.to_dict() for customer in customers]
    
    return PaginatedCustomerResponse(
        total=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
        data=customers_data
    )


@router.post("/check-phone")
async def check_phone(
    request: PhoneCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check if a phone number is registered in the system
    """
    phone_number = request.phone_number.replace(" ", "").replace("-", "")
    
    # Ensure phone has country code
    if not phone_number.startswith("+"):
        phone_number = "+91" + phone_number.lstrip("0")
    
    user = db.query(CustomerUser).filter(CustomerUser.phone_number == phone_number).first()
    
    return {
        "message": "Phone check completed",
        "phone_number": phone_number,
        "exists": user is not None,
        "user_id": user.customer_id if user else None,
        "status": user.status if user else None
    }


@router.post("/send-otp")
async def send_otp(
    request: SendOTPRequest
):
    """
    Trigger OTP sending to the customer's phone number.
    NOTE: The actual OTP is sent by Firebase from the client-side.
    This endpoint verifies the phone number format and returns a confirmation.
    """
    phone_number = request.phone_number.replace(" ", "").replace("-", "")
    
    if not phone_number or len(phone_number) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    # Ensure phone number has country code
    if not phone_number.startswith("+"):
        phone_number = "+91" + phone_number.lstrip("0")
    
    return {
        "message": "OTP will be sent to your phone",
        "phone_number": phone_number,
        "instruction": "Enter the OTP received on your phone number"
    }


@router.post("/verify-otp")
async def verify_otp(
    token: str = Form(...),
    phone_number: str = Form(...),
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    alternative_phone_no: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    profile_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Verify Firebase ID token and authenticate user.
    
    For new users (signup):
        - Requires: token, phone_number, full_name
        - Optional: email, alternative_phone_no, profile_photo, status
    
    For existing users (login):
        - Requires: token, phone_number
        - Note: Suspended and terminated accounts cannot login
    
    Status values: "active", "suspended", or "terminated"
    """
    
    if not FIREBASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Firebase not configured")
    
    try:
        # Verify the Firebase ID token
        decoded_token = firebase_auth.verify_id_token(token)
        firebase_phone = decoded_token.get("phone_number", "")
        firebase_uid = decoded_token.get("uid", "")
        
        if not firebase_uid:
            raise HTTPException(status_code=401, detail="Invalid Firebase token: missing uid")
        
        # Normalize both phone numbers for comparison
        # Remove spaces and dashes
        firebase_phone_normalized = firebase_phone.replace(" ", "").replace("-", "")
        phone_normalized = phone_number.replace(" ", "").replace("-", "")
        
        # Ensure incoming phone has country code (+91 for India)
        if not phone_normalized.startswith("+"):
            phone_normalized = "+91" + phone_normalized.lstrip("0")
        
        # Compare normalized versions
        if firebase_phone_normalized != phone_normalized:
            raise HTTPException(
                status_code=401, 
                detail=f"Phone number mismatch. Token: {firebase_phone_normalized}, Provided: {phone_normalized}"
            )
        
        # Store the normalized phone number for database
        phone_number = phone_normalized
        
        # Check if user exists by phone number
        user = db.query(CustomerUser).filter(
            CustomerUser.phone_number == phone_number
        ).first()
        
        if user:
            # LOGIN FLOW: User exists
            # Validate that the firebase_uid matches
            if user.firebase_uid != firebase_uid:
                raise HTTPException(
                    status_code=401, 
                    detail="Firebase UID mismatch. This phone number is associated with a different account."
                )
            
            if user.status == "suspended":
                raise HTTPException(status_code=403, detail="Customer account is suspended")
            
            if user.status == "terminated":
                raise HTTPException(status_code=403, detail="Customer account is terminated")

            # Generate backend token
            backend_token = generate_backend_token(user.customer_id)
            
            return {
                "message": "Login successful",
                "status": "login",
                "user": user.to_dict(),
                "backend_token": backend_token
            }
        
        else:
            # SIGNUP FLOW: New user
            if not full_name or full_name.strip() == "":
                raise HTTPException(
                    status_code=400, 
                    detail="Full name is required for new user registration"
                )

            # Check if firebase_uid already exists (user registered with different phone)
            existing_firebase_user = db.query(CustomerUser).filter(
                CustomerUser.firebase_uid == firebase_uid
            ).first()
            
            if existing_firebase_user:
                raise HTTPException(
                    status_code=400, 
                    detail="This Firebase account is already registered with a different phone number"
                )

            # New signups always start active; status can be changed later by admin/update flows.
            customer_status = "active"
            
            # Generate customer ID
            customer_id = generate_customer_id()
            
            # Upload profile photo if provided
            profile_photo_url = None
            if profile_photo:
                try:
                    profile_photo_url = upload_profile_photo(profile_photo, customer_id)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to upload photo: {str(e)}")
            
            # Create new customer user
            new_user = CustomerUser(
                customer_id=customer_id,
                firebase_uid=firebase_uid,
                phone_number=phone_number,
                full_name=full_name.strip(),
                email=email,
                alternative_phone_no=alternative_phone_no,
                status=customer_status,
                saved_addresses=[],
                profile_photo=profile_photo_url
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # Generate backend token
            backend_token = generate_backend_token(new_user.customer_id)
            
            return {
                "message": "Registration successful",
                "status": "signup",
                "user": new_user.to_dict(),
                "backend_token": backend_token
            }
    
    except HTTPException as e:
        # Re-raise HTTP exceptions as-is (401, 400, 404, etc.)
        raise e
    except firebase_admin.exceptions.FirebaseError as e:
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid Firebase token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authorization error: {str(e)}")


@router.get("/get-profile/{customer_id}")
async def get_profile(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Get customer profile by customer ID
    """
    user = db.query(CustomerUser).filter(CustomerUser.customer_id == customer_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "message": "Profile retrieved successfully",
        "user": user.to_dict()
    }


@router.put("/profile/{customer_id}")
async def update_profile(
    customer_id: str,
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    alternative_phone_no: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    profile_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Update customer profile information
    
    Parameters:
    - full_name: Customer's full name (optional)
    - email: Customer's email address (optional)
    - alternative_phone_no: Alternative phone number (optional)
    - status: Customer status - "active", "suspended", or "terminated" (optional)
    - profile_photo: Profile photo file (optional)
    """
    user = db.query(CustomerUser).filter(CustomerUser.customer_id == customer_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update full name if provided
    if full_name and full_name.strip():
        user.full_name = full_name.strip()
    
    # Update email if provided
    if email:
        user.email = email
    
    # Update alternative phone number if provided
    if alternative_phone_no:
        user.alternative_phone_no = alternative_phone_no

    # Update status if provided
    if status is not None:
        user.status = normalize_customer_status(status)
    
    # Update profile photo if provided
    if profile_photo:
        try:
            new_photo_url = upload_profile_photo(profile_photo, customer_id)
            user.profile_photo = new_photo_url
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to upload photo: {str(e)}")
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Profile updated successfully",
        "user": user.to_dict()
    }


@router.post("/add-addresses/{customer_id}")
async def add_address(
    customer_id: str,
    address_data: AddressInput,
    db: Session = Depends(get_db)
):
    """
    Add a new address to customer's saved addresses
    
    address_type can be: home, office, other
    """
    user = db.query(CustomerUser).filter(CustomerUser.customer_id == customer_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Initialize saved_addresses if None
    if user.saved_addresses is None:
        user.saved_addresses = []
    
    # Create new address entry
    new_address = build_saved_address(address_data, len(user.saved_addresses) + 1)
    
    user.saved_addresses.append(new_address)
    flag_modified(user, "saved_addresses")
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Address added successfully",
        "address": new_address,
        "user": user.to_dict()
    }


@router.delete("/delete-address/{customer_id}/{address_id}")
async def delete_address(
    customer_id: str,
    address_id: int,
    db: Session = Depends(get_db),
    token: str = Header(..., description="Firebase ID token")
):
    """
    Delete a saved address by address ID
    """
    # Verify Firebase token and ownership
    if not FIREBASE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Firebase not configured")

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        firebase_phone = decoded_token.get("phone_number", "")
        firebase_phone_normalized = firebase_phone.replace(" ", "").replace("-", "")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")

    user = db.query(CustomerUser).filter(CustomerUser.customer_id == customer_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Ensure token belongs to the same user
    phone_normalized = user.phone_number.replace(" ", "").replace("-", "")
    if not phone_normalized.startswith("+"):
        phone_normalized = "+91" + phone_normalized.lstrip("0")

    if firebase_phone_normalized != phone_normalized:
        raise HTTPException(status_code=403, detail="Token does not belong to the specified customer")
    
    if not user.saved_addresses:
        raise HTTPException(status_code=404, detail="No addresses found")
    
    user.saved_addresses = [addr for addr in user.saved_addresses if addr.get("id") != address_id]
    flag_modified(user, "saved_addresses")
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Address deleted successfully",
        "user": user.to_dict()
    }

# Utility function to generate JWT token for backend authentication
def generate_backend_token(customer_id: str) -> str:
    """
    Generate a JWT token for backend authentication
    """
    secret_key = os.getenv("JWT_SECRET", "your-secret-key")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    
    payload = {
        "customer_id": customer_id,
        "exp": datetime.utcnow() + timedelta(days=30),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token
