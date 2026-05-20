from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from db import get_db
from models.auth.patho_lab_user_models import PathoLabUser
from services.auth.patho_lab.lab_id_generator import generate_lab_id
from services.auth.patho_lab.doc_upload import save_and_compress_file

router = APIRouter(prefix="/auth/patho-lab", tags=["Patho Lab Auth"])

def get_password_hash(password):
    return password

def verify_password(plain_password, stored_password):
    return plain_password == stored_password

@router.post("/signup")
async def signup(
    lab_name: str = Form(...),
    mobile_number: str = Form(...),
    email_address: str = Form(...),
    password: str = Form(...),
    pan_number: str = Form(...),
    nabl_accreditation_number: str = Form(...),
    address: str = Form(...),
    terms_conditions_accepted: bool = Form(...),
    privacy_policy_accepted: bool = Form(...),
    gst_number: Optional[str] = Form(None),
    emergency_contact_number: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    lab_logo: Optional[UploadFile] = File(None),
    registration_certificate: UploadFile = File(...),
    bank_passbook: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Check if user already exists
    existing_user = db.query(PathoLabUser).filter(PathoLabUser.email_address == email_address).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate Lab ID
    lab_id = generate_lab_id(db, PathoLabUser)

    # Save files
    reg_cert_url = save_and_compress_file(registration_certificate, lab_id, "registration_certificate")
    bank_url = save_and_compress_file(bank_passbook, lab_id, "bank_passbook")
    logo_url = None
    if lab_logo:
        logo_url = save_and_compress_file(lab_logo, lab_id, "lab_logo")

    # Create user
    new_user = PathoLabUser(
        lab_id=lab_id,
        lab_name=lab_name,
        mobile_number=mobile_number,
        email_address=email_address,
        password=get_password_hash(password),
        gst_number=gst_number,
        pan_number=pan_number,
        nabl_accreditation_number=nabl_accreditation_number,
        address=address,
        lab_logo_url=logo_url,
        registration_certificate_url=reg_cert_url,
        bank_passbook_url=bank_url,
        emergency_contact_number=emergency_contact_number,
        whatsapp_number=whatsapp_number,
        terms_conditions_accepted=terms_conditions_accepted,
        privacy_policy_accepted=privacy_policy_accepted,
        status="pending"  # New users start with pending status until approved by admin
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully", "lab_id": lab_id}

@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(PathoLabUser).filter(PathoLabUser.email_address == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Your account is {user.status}. Please contact support."
        )
    
    user.last_login_at = datetime.now()
    db.commit()
    
    return {
        "message": "Login successful",
        "user": {
            "lab_id": user.lab_id,
            "lab_name": user.lab_name,
            "email": user.email_address
        }
    }

@router.get("/get-by/{lab_id}")
async def get_by_id(lab_id: str, db: Session = Depends(get_db)):
    user = db.query(PathoLabUser).filter(PathoLabUser.lab_id == lab_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Access denied. Account status: {user.status}"
        )
        
    return user
    
@router.get("/get-all")
async def get_all_labs(
    skip: int = 0, 
    limit: int = 100, 
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    whatsapp: Optional[str] = None,
    address: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(PathoLabUser)
    
    if name:
        query = query.filter(PathoLabUser.lab_name.ilike(f"%{name}%"))
    if email:
        query = query.filter(PathoLabUser.email_address.ilike(f"%{email}%"))
    if phone:
        query = query.filter(PathoLabUser.mobile_number.ilike(f"%{phone}%"))
    if whatsapp:
        query = query.filter(PathoLabUser.whatsapp_number.ilike(f"%{whatsapp}%"))
    if address:
        query = query.filter(PathoLabUser.address.ilike(f"%{address}%"))
    if status and status != "All":
        query = query.filter(PathoLabUser.status == status.lower())
        
    total = query.count()
    labs = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "labs": labs
    }

@router.put("/update-by/{lab_id}")
async def update_by_id(
    lab_id: str,
    lab_name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    email_address: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    gst_number: Optional[str] = Form(None),
    pan_number: Optional[str] = Form(None),
    nabl_accreditation_number: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    emergency_contact_number: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    terms_conditions_accepted: Optional[bool] = Form(None),
    privacy_policy_accepted: Optional[bool] = Form(None),
    lab_logo: Optional[UploadFile] = File(None),
    registration_certificate: Optional[UploadFile] = File(None),
    bank_passbook: Optional[UploadFile] = File(None),
    status: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    user = db.query(PathoLabUser).filter(PathoLabUser.lab_id == lab_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Lab not found")

    if lab_name: user.lab_name = lab_name
    if mobile_number: user.mobile_number = mobile_number
    if email_address: user.email_address = email_address
    if password: user.password = get_password_hash(password)
    if gst_number: user.gst_number = gst_number
    if pan_number: user.pan_number = pan_number
    if nabl_accreditation_number: user.nabl_accreditation_number = nabl_accreditation_number
    if address: user.address = address
    if emergency_contact_number: user.emergency_contact_number = emergency_contact_number
    if whatsapp_number: user.whatsapp_number = whatsapp_number
    if terms_conditions_accepted is not None: user.terms_conditions_accepted = terms_conditions_accepted
    if privacy_policy_accepted is not None: user.privacy_policy_accepted = privacy_policy_accepted
    if status: user.status = status

    if lab_logo:
        user.lab_logo_url = save_and_compress_file(lab_logo, lab_id, "lab_logo")
    if registration_certificate:
        user.registration_certificate_url = save_and_compress_file(registration_certificate, lab_id, "registration_certificate")
    if bank_passbook:
        user.bank_passbook_url = save_and_compress_file(bank_passbook, lab_id, "bank_passbook")

    db.commit()
    db.refresh(user)
    return {"message": "User updated successfully", "lab_id": lab_id}
