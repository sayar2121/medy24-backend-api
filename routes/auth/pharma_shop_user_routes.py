from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from db import get_db
from models.auth.pharma_shop_user_models import PharmaShopUser
from services.auth.pharma_shop.shop_id_generator import generate_shop_id
from services.auth.pharma_shop.shop_doc_upload import save_and_compress_file, delete_file

router = APIRouter(prefix="/auth/pharma-shop", tags=["Pharma Shop Auth"])

@router.post("/signup")
async def signup(
    shop_name: str = Form(...),
    shop_address: str = Form(...),
    shop_phone_no: str = Form(...),
    shop_email: str = Form(...),
    shop_password: str = Form(...),
    latitude: str = Form(...),
    longitude: str = Form(...),
    drug_license: UploadFile = File(...),
    pan_card: UploadFile = File(...),
    registration_certificate: UploadFile = File(...),
    bank_account_no: str = Form(...),
    bank_ifsc_code: str = Form(...),
    bank_name: str = Form(...),
    bank_account_name: str = Form(...),
    shop_alternative_phone_no: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    gstin_no: Optional[str] = Form(None),
    shop_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Signup endpoint for pharma shop
    """
    # Check if email already exists
    existing_shop = db.query(PharmaShopUser).filter(PharmaShopUser.shop_email == shop_email).first()
    if existing_shop:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate Shop ID
    shop_id = generate_shop_id(shop_name)
    
    # Save required documents
    drug_license_url = save_and_compress_file(drug_license, shop_id, "drug_license")
    pan_card_url = save_and_compress_file(pan_card, shop_id, "pan_card")
    registration_cert_url = save_and_compress_file(registration_certificate, shop_id, "registration_certificate")
    
    # Save optional shop photo
    shop_photo_url = None
    if shop_photo:
        shop_photo_url = save_and_compress_file(shop_photo, shop_id, "shop_photo")
    
    # Create new shop user
    new_shop = PharmaShopUser(
        shop_id=shop_id,
        shop_name=shop_name,
        shop_address=shop_address,
        shop_photo=shop_photo_url,
        shop_phone_no=shop_phone_no,
        shop_alternative_phone_no=shop_alternative_phone_no,
        shop_email=shop_email,
        shop_password=shop_password,
        whatsapp_number=whatsapp_number,
        gstin_no=gstin_no,
        latitude=latitude,
        longitude=longitude,
        drug_license_upload=drug_license_url,
        pan_card_upload=pan_card_url,
        registration_certificate_upload=registration_cert_url,
        bank_account_no=bank_account_no,
        bank_ifsc_code=bank_ifsc_code,
        bank_name=bank_name,
        bank_account_name=bank_account_name,
        status="pending"
    )
    
    db.add(new_shop)
    db.commit()
    db.refresh(new_shop)
    
    return {
        "message": "Shop registered successfully",
        "shop_id": shop_id,
        "status": "pending"
    }

@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Login endpoint for pharma shop using email and password
    """
    shop = db.query(PharmaShopUser).filter(PharmaShopUser.shop_email == email).first()
    if not shop or password != shop.shop_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if shop.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account is {shop.status}. Please contact support."
        )
    
    shop.last_login_at = datetime.now()
    db.commit()
    
    return {
        "message": "Login successful",
        "shop": {
            "shop_id": shop.shop_id,
            "shop_name": shop.shop_name,
            "shop_email": shop.shop_email,
            "status": shop.status
        }
    }

@router.get("/get-all")
async def get_all_shops(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all pharma shops with pagination
    """
    offset = (page - 1) * limit
    shops = db.query(PharmaShopUser).offset(offset).limit(limit).all()
    total = db.query(PharmaShopUser).count()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [shop.to_dict() for shop in shops]
    }

@router.get("/get-by/{shop_id}")
async def get_shop_by_id(shop_id: str, db: Session = Depends(get_db)):
    """
    Get pharma shop by shop ID
    """
    shop = db.query(PharmaShopUser).filter(PharmaShopUser.shop_id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    return shop.to_dict()

@router.put("/update-by/{shop_id}")
async def update_shop_by_id(
    shop_id: str,
    shop_name: Optional[str] = Form(None),
    shop_address: Optional[str] = Form(None),
    shop_phone_no: Optional[str] = Form(None),
    shop_alternative_phone_no: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    gstin_no: Optional[str] = Form(None),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    shop_password: Optional[str] = Form(None),
    bank_account_no: Optional[str] = Form(None),
    bank_ifsc_code: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    bank_account_name: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    shop_photo: Optional[UploadFile] = File(None),
    drug_license: Optional[UploadFile] = File(None),
    pan_card: Optional[UploadFile] = File(None),
    registration_certificate: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Update pharma shop by shop ID. Old files will be replaced with new ones
    """
    shop = db.query(PharmaShopUser).filter(PharmaShopUser.shop_id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Update text fields
    if shop_name is not None:
        shop.shop_name = shop_name
    if shop_address is not None:
        shop.shop_address = shop_address
    if shop_phone_no is not None:
        shop.shop_phone_no = shop_phone_no
    if shop_alternative_phone_no is not None:
        shop.shop_alternative_phone_no = shop_alternative_phone_no
    if whatsapp_number is not None:
        shop.whatsapp_number = whatsapp_number
    if gstin_no is not None:
        shop.gstin_no = gstin_no
    if latitude is not None:
        shop.latitude = latitude
    if longitude is not None:
        shop.longitude = longitude
    if shop_password is not None:
        shop.shop_password = shop_password
    if bank_account_no is not None:
        shop.bank_account_no = bank_account_no
    if bank_ifsc_code is not None:
        shop.bank_ifsc_code = bank_ifsc_code
    if bank_name is not None:
        shop.bank_name = bank_name
    if bank_account_name is not None:
        shop.bank_account_name = bank_account_name
    if status is not None:
        shop.status = status
    
    # Handle shop photo update
    if shop_photo:
        # Delete old photo if exists
        if shop.shop_photo:
            delete_file(shop.shop_photo)
        # Upload new photo
        shop.shop_photo = save_and_compress_file(shop_photo, shop_id, "shop_photo")
    
    # Handle drug license update
    if drug_license:
        # Delete old file if exists
        if shop.drug_license_upload:
            delete_file(shop.drug_license_upload)
        # Upload new file
        shop.drug_license_upload = save_and_compress_file(drug_license, shop_id, "drug_license")
    
    # Handle pan card update
    if pan_card:
        # Delete old file if exists
        if shop.pan_card_upload:
            delete_file(shop.pan_card_upload)
        # Upload new file
        shop.pan_card_upload = save_and_compress_file(pan_card, shop_id, "pan_card")
    
    # Handle registration certificate update
    if registration_certificate:
        # Delete old file if exists
        if shop.registration_certificate_upload:
            delete_file(shop.registration_certificate_upload)
        # Upload new file
        shop.registration_certificate_upload = save_and_compress_file(registration_certificate, shop_id, "registration_certificate")
    
    db.commit()
    db.refresh(shop)
    return shop.to_dict()

@router.delete("/delete-by/{shop_id}")
async def delete_shop_by_id(shop_id: str, db: Session = Depends(get_db)):
    """
    Delete pharma shop by shop ID
    """
    shop = db.query(PharmaShopUser).filter(PharmaShopUser.shop_id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Delete all uploaded files
    delete_file(shop.shop_photo) if shop.shop_photo else None
    delete_file(shop.drug_license_upload) if shop.drug_license_upload else None
    delete_file(shop.pan_card_upload) if shop.pan_card_upload else None
    delete_file(shop.registration_certificate_upload) if shop.registration_certificate_upload else None
    
    # Delete shop record
    db.delete(shop)
    db.commit()
    
    return {"message": "Shop deleted successfully"}

