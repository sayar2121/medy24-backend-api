from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from db import get_db
from models.medicine.core_medicine_models import CoreMedicine
from services.medicine.medicine_id_generator import generate_medicine_id
from services.medicine.medicine_photo_upload import upload_medicine_photo, delete_medicine_photo

router = APIRouter(prefix="/medicines", tags=["Core Medicines"])

def calculate_final_selling_price(mrp: float, discount_percent: Optional[float] = None) -> float:
    """
    Calculate final selling price based on MRP and discount percent
    If discount_percent is None, final_selling_price = mrp
    Otherwise, final_selling_price = mrp - (mrp * discount_percent / 100)
    """
    if discount_percent is None:
        return mrp
    return mrp - (mrp * discount_percent / 100)

@router.post("/create")
async def create_medicine(
    medicine_name: str = Form(...),
    medicine_category: str = Form(...),
    medicine_quantity: str = Form(...),
    mrp: float = Form(...),
    discount_percent: Optional[float] = Form(None),
    medicine_description: Optional[str] = Form(None),
    medicine_composition: Optional[str] = Form(None),
    precautions: Optional[str] = Form(None),
    medicine_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create a new medicine with all details
    """
    # Validate: Check if medicine with same name and category already exists
    existing_medicine = db.query(CoreMedicine).filter(
        CoreMedicine.medicine_name == medicine_name,
        CoreMedicine.medicine_category == medicine_category
    ).first()
    
    if existing_medicine:
        raise HTTPException(
            status_code=400, 
            detail=f"Medicine with name '{medicine_name}' in category '{medicine_category}' already exists"
        )
    
    # Generate medicine ID
    medicine_id = generate_medicine_id(medicine_name)
    
    # Handle photo upload
    photo_url = None
    if medicine_photo:
        photo_url = upload_medicine_photo(medicine_photo, medicine_id, medicine_name)
    
    # Parse precautions as JSON
    precautions_json = json.loads(precautions) if precautions else []
    
    # Calculate final selling price
    final_selling_price = calculate_final_selling_price(mrp, discount_percent)
    
    # Create new medicine record
    new_medicine = CoreMedicine(
        medicine_id=medicine_id,
        medicine_name=medicine_name,
        medicine_category=medicine_category,
        medicine_quantity=medicine_quantity,
        mrp=mrp,
        discount_percent=discount_percent,
        final_selling_price=final_selling_price,
        medicine_description=medicine_description,
        medicine_composition=medicine_composition,
        precautions=precautions_json,
        medicine_photo=photo_url
    )
    
    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)
    return new_medicine.to_dict()

@router.get("/get-all")
async def get_all_medicines(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all medicines with pagination
    """
    offset = (page - 1) * limit
    medicines = db.query(CoreMedicine).offset(offset).limit(limit).all()
    total = db.query(CoreMedicine).count()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": medicines
    }

@router.get("/get-by/{medicine_id}")
async def get_medicine_by_id(medicine_id: str, db: Session = Depends(get_db)):
    """
    Get medicine by ID
    """
    medicine = db.query(CoreMedicine).filter(CoreMedicine.medicine_id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    return medicine

@router.put("/update-by/{medicine_id}")
async def update_medicine_by_id(
    medicine_id: str,
    medicine_name: Optional[str] = Form(None),
    medicine_category: Optional[str] = Form(None),
    medicine_quantity: Optional[str] = Form(None),
    mrp: Optional[float] = Form(None),
    discount_percent: Optional[float] = Form(None),
    medicine_description: Optional[str] = Form(None),
    medicine_composition: Optional[str] = Form(None),
    precautions: Optional[str] = Form(None),
    medicine_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Update medicine by ID. If new photo is provided, old photo will be replaced.
    Final selling price is auto-calculated based on MRP and discount percent.
    """
    medicine = db.query(CoreMedicine).filter(CoreMedicine.medicine_id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    # Validate: Check if duplicate name and category exists (excluding current medicine)
    if medicine_name is not None or medicine_category is not None:
        updated_name = medicine_name if medicine_name is not None else medicine.medicine_name
        updated_category = medicine_category if medicine_category is not None else medicine.medicine_category
        
        duplicate_medicine = db.query(CoreMedicine).filter(
            CoreMedicine.medicine_name == updated_name,
            CoreMedicine.medicine_category == updated_category,
            CoreMedicine.medicine_id != medicine_id
        ).first()
        
        if duplicate_medicine:
            raise HTTPException(
                status_code=400,
                detail=f"Medicine with name '{updated_name}' in category '{updated_category}' already exists"
            )
    
    # Update text fields
    if medicine_name is not None:
        medicine.medicine_name = medicine_name
    if medicine_category is not None:
        medicine.medicine_category = medicine_category
    if medicine_quantity is not None:
        medicine.medicine_quantity = medicine_quantity
    if mrp is not None:
        medicine.mrp = mrp
    if discount_percent is not None:
        medicine.discount_percent = discount_percent
    if medicine_description is not None:
        medicine.medicine_description = medicine_description
    if medicine_composition is not None:
        medicine.medicine_composition = medicine_composition
    if precautions is not None:
        medicine.precautions = json.loads(precautions)
    
    # Recalculate final_selling_price if mrp or discount_percent changed
    if mrp is not None or discount_percent is not None:
        updated_mrp = mrp if mrp is not None else medicine.mrp
        updated_discount = discount_percent if discount_percent is not None else medicine.discount_percent
        medicine.final_selling_price = calculate_final_selling_price(updated_mrp, updated_discount)
    
    # Handle photo update - delete old and upload new
    if medicine_photo:
        # Delete old photo if exists
        if medicine.medicine_photo:
            delete_medicine_photo(medicine.medicine_photo)
        
        # Upload new photo
        new_photo_url = upload_medicine_photo(medicine_photo, medicine_id, medicine.medicine_name)
        medicine.medicine_photo = new_photo_url
    
    db.commit()
    db.refresh(medicine)
    return medicine.to_dict()

@router.delete("/delete-by-ids")
async def delete_medicines_by_ids(medicine_ids: List[str] = Body(...), db: Session = Depends(get_db)):
    """
    Delete multiple medicines by their IDs
    """
    medicines = db.query(CoreMedicine).filter(CoreMedicine.medicine_id.in_(medicine_ids)).all()
    if not medicines:
        raise HTTPException(status_code=404, detail="No medicines found with provided IDs")
    
    # Delete photos and database records
    for medicine in medicines:
        if medicine.medicine_photo:
            delete_medicine_photo(medicine.medicine_photo)
        db.delete(medicine)
    
    db.commit()
    return {"message": f"Successfully deleted {len(medicines)} medicines"}
