from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from db import get_db
from models.about_us.about_us_models import AboutUs
from services.about_us.about_us_photo_upload import upload_about_us_photo, delete_about_us_photo

router = APIRouter(prefix="/about-us", tags=["About Us"])

@router.post("/create")
async def create_about_us(
    company_name: str = Form(...),
    company_tagline: Optional[str] = Form(None),
    company_description_text: Optional[str] = Form(None),
    mission: Optional[str] = Form(None),
    vision: Optional[str] = Form(None),
    director_name: Optional[str] = Form(None),
    director_message: Optional[str] = Form(None),
    office_address: Optional[str] = Form(None),
    registered_address: Optional[str] = Form(None),
    email1: Optional[str] = Form(None),
    email2: Optional[str] = Form(None),
    phone1: Optional[str] = Form(None),
    phone2: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    partners: Optional[str] = Form(None),  # Expecting JSON string
    company_photo: Optional[UploadFile] = File(None),
    director_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create about us information
    """
    # Parse partners JSON if provided
    partners_json = json.loads(partners) if partners else []
    
    # Upload photos if provided
    company_photo_url = None
    if company_photo:
        company_photo_url = upload_about_us_photo(company_photo, "company_photo")
    
    director_photo_url = None
    if director_photo:
        director_photo_url = upload_about_us_photo(director_photo, "director_photo")
    
    # Handle partners photos
    processed_partners = []
    if partners_json:
        for i, partner in enumerate(partners_json):
            processed_partners.append(partner)
    
    new_about_us = AboutUs(
        company_name=company_name,
        company_photo=company_photo_url,
        company_tagline=company_tagline,
        company_description_text=company_description_text,
        mission=mission,
        vision=vision,
        director_name=director_name,
        director_message=director_message,
        director_photo=director_photo_url,
        partners=processed_partners if processed_partners else None,
        office_address=office_address,
        registered_address=registered_address,
        email1=email1,
        email2=email2,
        phone1=phone1,
        phone2=phone2,
        website=website
    )
    
    db.add(new_about_us)
    db.commit()
    db.refresh(new_about_us)
    return new_about_us

@router.get("/get-all")
async def get_all_about_us(db: Session = Depends(get_db)):
    """
    Get all about us entries
    """
    entries = db.query(AboutUs).all()
    if not entries:
        return {"total": 0, "data": []}
    
    return {
        "total": len(entries),
        "data": entries
    }

@router.get("/get-by/{about_us_id}")
async def get_about_us_by_id(about_us_id: int, db: Session = Depends(get_db)):
    """
    Get about us information by ID
    """
    entry = db.query(AboutUs).filter(AboutUs.id == about_us_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="About us information not found")
    
    return entry

@router.put("/update-by/{about_us_id}")
async def update_about_us_by_id(
    about_us_id: int,
    company_name: Optional[str] = Form(None),
    company_tagline: Optional[str] = Form(None),
    company_description_text: Optional[str] = Form(None),
    mission: Optional[str] = Form(None),
    vision: Optional[str] = Form(None),
    director_name: Optional[str] = Form(None),
    director_message: Optional[str] = Form(None),
    office_address: Optional[str] = Form(None),
    registered_address: Optional[str] = Form(None),
    email1: Optional[str] = Form(None),
    email2: Optional[str] = Form(None),
    phone1: Optional[str] = Form(None),
    phone2: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    partners: Optional[str] = Form(None),  # Expecting JSON string
    company_photo: Optional[UploadFile] = File(None),
    director_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Update about us information by ID with photo replacement
    """
    entry = db.query(AboutUs).filter(AboutUs.id == about_us_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="About us information not found")
    
    # Update text fields
    if company_name is not None:
        entry.company_name = company_name
    if company_tagline is not None:
        entry.company_tagline = company_tagline
    if company_description_text is not None:
        entry.company_description_text = company_description_text
    if mission is not None:
        entry.mission = mission
    if vision is not None:
        entry.vision = vision
    if director_name is not None:
        entry.director_name = director_name
    if director_message is not None:
        entry.director_message = director_message
    if office_address is not None:
        entry.office_address = office_address
    if registered_address is not None:
        entry.registered_address = registered_address
    if email1 is not None:
        entry.email1 = email1
    if email2 is not None:
        entry.email2 = email2
    if phone1 is not None:
        entry.phone1 = phone1
    if phone2 is not None:
        entry.phone2 = phone2
    if website is not None:
        entry.website = website
    
    # Update partners if provided
    if partners is not None:
        partners_json = json.loads(partners)
        entry.partners = partners_json if partners_json else None
    
    # Handle company photo replacement
    if company_photo:
        # Delete old photo if exists
        if entry.company_photo:
            delete_about_us_photo(entry.company_photo)
        # Upload new photo
        entry.company_photo = upload_about_us_photo(company_photo, "company_photo")
    
    # Handle director photo replacement
    if director_photo:
        # Delete old photo if exists
        if entry.director_photo:
            delete_about_us_photo(entry.director_photo)
        # Upload new photo
        entry.director_photo = upload_about_us_photo(director_photo, "director_photo")
    
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/delete-by/{about_us_id}")
async def delete_about_us_by_id(about_us_id: int, db: Session = Depends(get_db)):
    """
    Delete about us information by ID
    """
    entry = db.query(AboutUs).filter(AboutUs.id == about_us_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="About us information not found")
    
    # Delete photos if they exist
    if entry.company_photo:
        delete_about_us_photo(entry.company_photo)
    if entry.director_photo:
        delete_about_us_photo(entry.director_photo)
    
    db.delete(entry)
    db.commit()
    return {"message": f"Successfully deleted about us information with ID {about_us_id}"}
