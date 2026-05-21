from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from db import get_db
from models.lab_test.test_package_booking_models import TestPackageBooking
from models.auth.customer_user_models import CustomerUser
from models.auth.patho_lab_user_models import PathoLabUser
from services.lab_test.booking_id_generator import generate_booking_id
from services.lab_test.report_upload import upload_report, upload_multiple_reports
from services.razorpay.razorpay_services import client as razorpay_client

router = APIRouter(prefix="/test-package-bookings", tags=["Test Package Bookings"])


# =====================================================
# PYDANTIC MODELS FOR REQUEST/RESPONSE
# =====================================================

class CreateBookingRequest(BaseModel):
    customer_id: str
    lab_id: str
    booking_type: str  # "single_test" or "package"
    booked_items: List[Dict[str, Any]]
    patient_details: List[Dict[str, Any]]
    sample_collection_address: Dict[str, Any]
    sub_total_amount: float
    total_discount_amount: float
    platform_fee: float
    tax_amount: float
    total_amount_to_be_paid: float
    payment_mode: str  # "online" or "cash"
    transaction_id: Optional[str] = None
    transaction_hash: Optional[str] = None
    customer_note: Optional[str] = None


class UpdateBookingRequest(BaseModel):
    booking_status: Optional[str] = None
    cancellation_reason: Optional[str] = None
    lab_note: Optional[str] = None


class BookingResponse(BaseModel):
    booking_id: str
    customer_id: str
    lab_id: str
    booking_status: str
    total_amount_to_be_paid: float
    payment_mode: str
    transaction_id: Optional[str]
    transaction_status: str


class BookingDetailResponse(BaseModel):
    # Booking Details
    booking_id: str
    customer_id: str
    lab_id: str
    booking_type: str
    booking_status: str
    
    # Booked Items & Patient Info
    booked_items: List[Dict[str, Any]]
    patient_details: List[Dict[str, Any]]
    sample_collection_address: Dict[str, Any]
    
    # Report URLs
    report_urls: Optional[List[str]]
    
    # Pricing Details
    sub_total_amount: float
    total_discount_amount: float
    platform_fee: float
    tax_amount: float
    total_amount_to_be_paid: float
    lab_payable_amount: float
    
    # Payment Details
    payment_mode: str
    transaction_id: Optional[str]
    transaction_hash: Optional[str]
    transaction_status: str
    paid_amount: float
    paid_at: Optional[datetime]
    
    # Notes
    customer_note: Optional[str]
    lab_note: Optional[str]
    cancellation_reason: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Lab Details
    lab_name: Optional[str]
    lab_address: Optional[str]
    lab_phone: Optional[str]
    lab_email: Optional[str]



# =====================================================
# HELPER FUNCTIONS
# =====================================================

def calculate_lab_payable_amount(
    sub_total: float,
    discount: float,
    platform_fee: float,
    tax: float
) -> float:
    """Calculate amount payable to lab after platform fee and discounts"""
    payable = sub_total - discount - platform_fee + tax
    return max(0, payable)


# =====================================================
# 1. POST - CREATE BOOKING
# =====================================================

@router.post("/create-booking", response_model=BookingResponse)
async def create_booking(
    request: CreateBookingRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new lab test or package booking.
    
    - **customer_id**: Customer placing the booking
    - **lab_id**: Pathology lab ID
    - **booking_type**: "single_test" or "package"
    - **payment_mode**: "online" or "cash"
    """
    try:
        # Verify customer exists
        customer = db.query(CustomerUser).filter(
            CustomerUser.customer_id == request.customer_id
        ).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Verify lab exists
        lab = db.query(PathoLabUser).filter(
            PathoLabUser.lab_id == request.lab_id
        ).first()
        if not lab:
            raise HTTPException(status_code=404, detail="Lab not found")
        
        # Generate unique booking ID
        booking_id = generate_booking_id()
        
        # Calculate lab payable amount
        lab_payable_amount = calculate_lab_payable_amount(
            request.sub_total_amount,
            request.total_discount_amount,
            request.platform_fee,
            request.tax_amount
        )
        
        # Prepare gateway response based on payment mode
        gateway_response = {}
        transaction_status = "pending"
        paid_amount = 0.0
        paid_at = None
        transaction_id = None
        
        if request.payment_mode == "online":
            # For online payments, create Razorpay order
            try:
                razorpay_order = razorpay_client.order.create({
                    "amount": int(request.total_amount_to_be_paid * 100),  # Amount in paise
                    "currency": "INR",
                    "receipt": booking_id,
                    "notes": {
                        "booking_id": booking_id,
                        "customer_id": request.customer_id,
                        "lab_id": request.lab_id
                    }
                })
                gateway_response = razorpay_order
                transaction_id = razorpay_order.get("id")
                transaction_status = "initiated"
            except Exception as e:
                print(f"Razorpay error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Payment gateway error: {str(e)}"
                )
        else:
            # For cash payments
            transaction_status = "pending"
            transaction_id = None
        
        # Create booking record
        new_booking = TestPackageBooking(
            booking_id=booking_id,
            customer_id=request.customer_id,
            lab_id=request.lab_id,
            booking_type=request.booking_type,
            booked_items=request.booked_items,
            patient_details=request.patient_details,
            sample_collection_address=request.sample_collection_address,
            booking_status="pending",
            sub_total_amount=request.sub_total_amount,
            total_discount_amount=request.total_discount_amount,
            platform_fee=request.platform_fee,
            tax_amount=request.tax_amount,
            total_amount_to_be_paid=request.total_amount_to_be_paid,
            lab_payable_amount=lab_payable_amount,
            payment_mode=request.payment_mode,
            transaction_id=transaction_id,
            transaction_hash=request.transaction_hash,
            transaction_status=transaction_status,
            gateway_response=gateway_response,
            paid_amount=paid_amount,
            paid_at=paid_at,
            customer_note=request.customer_note,
            report_urls=[]
        )
        
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        
        return BookingResponse(
            booking_id=new_booking.booking_id,
            customer_id=new_booking.customer_id,
            lab_id=new_booking.lab_id,
            booking_status=new_booking.booking_status,
            total_amount_to_be_paid=new_booking.total_amount_to_be_paid,
            payment_mode=new_booking.payment_mode,
            transaction_id=new_booking.transaction_id,
            transaction_status=new_booking.transaction_status
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating booking: {str(e)}")


# =====================================================
# 1b. PUT - UPDATE BOOKING (Status, Cancellation, Reports)
# =====================================================

@router.put("/update/{booking_id}", response_model=BookingDetailResponse)
async def update_booking(
    booking_id: str,
    booking_status: Optional[str] = Form(None),
    cancellation_reason: Optional[str] = Form(None),
    lab_note: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Update booking details including status, cancellation reason, lab notes, and report uploads.
    
    - **booking_id**: Unique booking ID
    - **booking_status**: New booking status (pending, accepted, sample_collected, testing_in_progress, report_ready, completed, cancelled)
    - **cancellation_reason**: Reason for cancellation (if applicable)
    - **lab_note**: Notes from the lab
    - **files**: Report files to upload (replaces old reports)
    """
    try:
        # Fetch booking
        booking = db.query(TestPackageBooking).filter(
            TestPackageBooking.booking_id == booking_id
        ).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Update booking status if provided
        if booking_status:
            booking.booking_status = booking_status
        
        # Update cancellation reason if provided
        if cancellation_reason:
            booking.cancellation_reason = cancellation_reason
        
        # Update lab note if provided
        if lab_note:
            booking.lab_note = lab_note
        
        # Handle file uploads if provided
        if files and len(files) > 0:
            try:
                # Remove None entries (in case no files are actually uploaded)
                valid_files = [f for f in files if f is not None and f.filename]
                
                if valid_files:
                    # Upload reports and replace old ones
                    if len(valid_files) == 1:
                        file_url = await upload_report(booking_id, valid_files[0])
                        booking.report_urls = [file_url]
                    else:
                        file_urls = await upload_multiple_reports(booking_id, valid_files)
                        booking.report_urls = file_urls
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error uploading reports: {str(e)}"
                )
        
        # Update timestamp
        booking.updated_at = datetime.utcnow()
        
        # Commit changes
        db.commit()
        db.refresh(booking)
        
        # Fetch lab details for response
        lab = db.query(PathoLabUser).filter(
            PathoLabUser.lab_id == booking.lab_id
        ).first()
        
        lab_name = lab.lab_name if lab else None
        lab_address = lab.address if lab else None
        lab_phone = lab.mobile_number if lab else None
        lab_email = lab.email_address if lab else None
        
        return BookingDetailResponse(
            booking_id=booking.booking_id,
            customer_id=booking.customer_id,
            lab_id=booking.lab_id,
            booking_type=booking.booking_type,
            booking_status=booking.booking_status,
            booked_items=booking.booked_items,
            patient_details=booking.patient_details,
            sample_collection_address=booking.sample_collection_address,
            report_urls=booking.report_urls,
            sub_total_amount=booking.sub_total_amount,
            total_discount_amount=booking.total_discount_amount,
            platform_fee=booking.platform_fee,
            tax_amount=booking.tax_amount,
            total_amount_to_be_paid=booking.total_amount_to_be_paid,
            lab_payable_amount=booking.lab_payable_amount,
            payment_mode=booking.payment_mode,
            transaction_id=booking.transaction_id,
            transaction_hash=booking.transaction_hash,
            transaction_status=booking.transaction_status,
            paid_amount=booking.paid_amount,
            paid_at=booking.paid_at,
            customer_note=booking.customer_note,
            lab_note=booking.lab_note,
            cancellation_reason=booking.cancellation_reason,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            lab_name=lab_name,
            lab_address=lab_address,
            lab_phone=lab_phone,
            lab_email=lab_email
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating booking: {str(e)}")


# =====================================================
# 2. GET - FETCH ALL BOOKING DETAILS WITH LAB INFO
# =====================================================

@router.get("/details/{booking_id}", response_model=BookingDetailResponse)
async def get_booking_details(
    booking_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all booking details including lab information.
    
    Returns:
    - All booking details
    - Lab name, address, phone, email
    """
    try:
        booking = db.query(TestPackageBooking).filter(
            TestPackageBooking.booking_id == booking_id
        ).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Fetch lab details
        lab = db.query(PathoLabUser).filter(
            PathoLabUser.lab_id == booking.lab_id
        ).first()
        
        lab_name = lab.lab_name if lab else None
        lab_address = lab.address if lab else None
        lab_phone = lab.mobile_number if lab else None
        lab_email = lab.email_address if lab else None
        
        return BookingDetailResponse(
            booking_id=booking.booking_id,
            customer_id=booking.customer_id,
            lab_id=booking.lab_id,
            booking_type=booking.booking_type,
            booking_status=booking.booking_status,
            booked_items=booking.booked_items,
            patient_details=booking.patient_details,
            sample_collection_address=booking.sample_collection_address,
            report_urls=booking.report_urls,
            sub_total_amount=booking.sub_total_amount,
            total_discount_amount=booking.total_discount_amount,
            platform_fee=booking.platform_fee,
            tax_amount=booking.tax_amount,
            total_amount_to_be_paid=booking.total_amount_to_be_paid,
            lab_payable_amount=booking.lab_payable_amount,
            payment_mode=booking.payment_mode,
            transaction_id=booking.transaction_id,
            transaction_hash=booking.transaction_hash,
            transaction_status=booking.transaction_status,
            paid_amount=booking.paid_amount,
            paid_at=booking.paid_at,
            customer_note=booking.customer_note,
            lab_note=booking.lab_note,
            cancellation_reason=booking.cancellation_reason,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            lab_name=lab_name,
            lab_address=lab_address,
            lab_phone=lab_phone,
            lab_email=lab_email
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching booking details: {str(e)}")


# =====================================================
# 3. GET - ALL BOOKINGS BY CUSTOMER ID
# =====================================================

@router.get("/customer/{customer_id}")
async def get_customer_bookings(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all bookings for a specific customer.
    
    Returns:
    - List of all bookings with lab details
    """
    try:
        bookings = db.query(TestPackageBooking).filter(
            TestPackageBooking.customer_id == customer_id
        ).order_by(TestPackageBooking.created_at.desc()).all()
        
        if not bookings:
            raise HTTPException(status_code=404, detail="No bookings found for this customer")
        
        # Build response with lab details
        booking_list = []
        for booking in bookings:
            lab = db.query(PathoLabUser).filter(
                PathoLabUser.lab_id == booking.lab_id
            ).first()
            
            booking_data = {
                "booking_id": booking.booking_id,
                "customer_id": booking.customer_id,
                "lab_id": booking.lab_id,
                "booking_type": booking.booking_type,
                "booking_status": booking.booking_status,
                "booked_items": booking.booked_items,
                "patient_details": booking.patient_details,
                "sample_collection_address": booking.sample_collection_address,
                "report_urls": booking.report_urls,
                "sub_total_amount": booking.sub_total_amount,
                "total_discount_amount": booking.total_discount_amount,
                "platform_fee": booking.platform_fee,
                "tax_amount": booking.tax_amount,
                "total_amount_to_be_paid": booking.total_amount_to_be_paid,
                "lab_payable_amount": booking.lab_payable_amount,
                "payment_mode": booking.payment_mode,
                "transaction_id": booking.transaction_id,
                "transaction_status": booking.transaction_status,
                "paid_amount": booking.paid_amount,
                "customer_note": booking.customer_note,
                "lab_note": booking.lab_note,
                "cancellation_reason": booking.cancellation_reason,
                "created_at": booking.created_at,
                "updated_at": booking.updated_at,
                "lab_name": lab.lab_name if lab else None,
                "lab_address": lab.address if lab else None,
                "lab_phone": lab.mobile_number if lab else None,
                "lab_email": lab.email_address if lab else None
            }
            booking_list.append(booking_data)
        
        return {
            "count": len(booking_list),
            "customer_id": customer_id,
            "bookings": booking_list
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching customer bookings: {str(e)}")


# =====================================================
# 4. GET - ALL BOOKINGS BY LAB ID
# =====================================================

@router.get("/lab/{lab_id}")
async def get_lab_bookings(
    lab_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all bookings for a specific lab.
    
    Returns:
    - List of all bookings with customer and lab details
    """
    try:
        bookings = db.query(TestPackageBooking).filter(
            TestPackageBooking.lab_id == lab_id
        ).order_by(TestPackageBooking.created_at.desc()).all()
        
        if not bookings:
            raise HTTPException(status_code=404, detail="No bookings found for this lab")
        
        # Build response with lab details
        booking_list = []
        for booking in bookings:
            lab = db.query(PathoLabUser).filter(
                PathoLabUser.lab_id == booking.lab_id
            ).first()
            
            booking_data = {
                "booking_id": booking.booking_id,
                "customer_id": booking.customer_id,
                "lab_id": booking.lab_id,
                "booking_type": booking.booking_type,
                "booking_status": booking.booking_status,
                "booked_items": booking.booked_items,
                "patient_details": booking.patient_details,
                "sample_collection_address": booking.sample_collection_address,
                "report_urls": booking.report_urls,
                "sub_total_amount": booking.sub_total_amount,
                "total_discount_amount": booking.total_discount_amount,
                "platform_fee": booking.platform_fee,
                "tax_amount": booking.tax_amount,
                "total_amount_to_be_paid": booking.total_amount_to_be_paid,
                "lab_payable_amount": booking.lab_payable_amount,
                "payment_mode": booking.payment_mode,
                "transaction_id": booking.transaction_id,
                "transaction_status": booking.transaction_status,
                "paid_amount": booking.paid_amount,
                "customer_note": booking.customer_note,
                "lab_note": booking.lab_note,
                "cancellation_reason": booking.cancellation_reason,
                "created_at": booking.created_at,
                "updated_at": booking.updated_at,
                "lab_name": lab.lab_name if lab else None,
                "lab_address": lab.address if lab else None,
                "lab_phone": lab.mobile_number if lab else None,
                "lab_email": lab.email_address if lab else None
            }
            booking_list.append(booking_data)
        
        return {
            "count": len(booking_list),
            "lab_id": lab_id,
            "bookings": booking_list
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching lab bookings: {str(e)}")
