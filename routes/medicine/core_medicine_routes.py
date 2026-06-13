from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import json
from db import get_db
from models.medicine.core_medicine_models import CoreMedicine
from services.medicine.medicine_id_generator import generate_medicine_id
from services.medicine.medicine_photo_upload import upload_medicine_photo, delete_medicine_photo
from services.medicine.medicine_csv_upload import upload_medicine_csv
from services.medicine.medicine_data_extractor import extract_medicines_from_csv

router = APIRouter(prefix="/medicines", tags=["Core Medicines"])

# Global dictionary to track CSV import job status
import uuid
from datetime import datetime

csv_import_jobs = {}


def process_csv_in_background(file_path: str, job_id: str, db: Session):
    """Process CSV file in background and store results"""
    try:
        csv_import_jobs[job_id]["status"] = "processing"
        csv_import_jobs[job_id]["started_at"] = datetime.now().isoformat()
        
        results = extract_medicines_from_csv(file_path, db)
        
        csv_import_jobs[job_id]["status"] = "completed"
        csv_import_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        csv_import_jobs[job_id]["results"] = results
    except Exception as e:
        csv_import_jobs[job_id]["status"] = "failed"
        csv_import_jobs[job_id]["error"] = str(e)
        csv_import_jobs[job_id]["completed_at"] = datetime.now().isoformat()

def calculate_final_selling_price(mrp: float, discount_percent: Optional[float] = None) -> float:
    """
    Calculate final selling price based on MRP.
    Individual discounts have been removed globally. final_selling_price = mrp.
    """
    return mrp

@router.post("/create")
async def upload_medicines_from_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload medicines in bulk from a CSV file (asynchronous).
    
    This endpoint accepts a CSV file, returns immediately with a job ID,
    and processes the file in the background.
    
    Expected CSV columns:
    - medicine_name (required)
    - medicine_category (required)
    - medicine_quantity (required)
    - mrp (required)
    - discount_percent (optional)
    - medicine_description (optional)
    - medicine_composition (optional)
    - precautions (optional - JSON array or comma-separated values)
    - prescription_required (optional - "true" or "false")
    
    Returns:
    - job_id: Unique ID to track the import progress
    - status: "queued" (processing will start shortly)
    - message: Instructions to check status
    """
    try:
        # Validate file is CSV
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job tracking
        csv_import_jobs[job_id] = {
            "status": "queued",
            "job_id": job_id,
            "filename": file.filename,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "results": None,
            "error": None
        }
        
        # Upload CSV file
        file_path = await upload_medicine_csv(file)
        
        # Add background task to process CSV
        background_tasks.add_task(process_csv_in_background, file_path, job_id, db)
        
        return {
            "status": "queued",
            "job_id": job_id,
            "message": f"CSV file '{file.filename}' uploaded successfully. Processing started in background.",
            "check_status_url": f"/medicines/import-status/{job_id}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading medicines from CSV: {str(e)}")


@router.get("/import-status/{job_id}")
async def get_import_status(job_id: str):
    """
    Get the status of a CSV import job.
    
    Returns:
    - job_id: The job ID
    - status: "queued", "processing", "completed", or "failed"
    - results: (if completed) Import results with counts and created medicines
    - error: (if failed) Error message
    """
    if job_id not in csv_import_jobs:
        raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found")
    
    job = csv_import_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "filename": job["filename"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"]
    }
    
    if job["status"] == "completed" and job["results"]:
        response["results"] = {
            "total_rows": job["results"]["total_rows"],
            "successful": job["results"]["successful"],
            "failed": job["results"]["failed"],
            "errors": job["results"]["errors"],
            "created_medicines_count": len(job["results"]["created_medicines"]),
            "sample_created_medicines": job["results"]["created_medicines"][:10]  # First 10
        }
    
    if job["status"] == "failed":
        response["error"] = job["error"]
    
    return response


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
        "data": [medicine.to_dict() for medicine in medicines]
    }

@router.get("/search")
async def search_medicines(
    search_term: Optional[str] = Query(None),
    price_range: Optional[List[str]] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Search medicines by name, price range, and category with pagination
    
    Query Parameters:
    - search_term: Search by medicine name (case-insensitive substring match)
    - price_range: Filter by price ranges (can be multiple)
      - "0-100": 0 to 100
      - "100-500": 100 to 500
      - "500-1000": 500 to 1000
      - "1000-5000": 1000 to 5000
      - "5000+": Above 5000
    - category: Filter by medicine category
    - page: Page number (default: 1)
    - limit: Results per page (default: 20, max: 100)
    
    Example: /search?search_term=aspirin&price_range=0-100&price_range=100-500&category=Pain%20Relief
    """
    query = db.query(CoreMedicine)
    
    # Filter by search term (medicine name - case insensitive)
    if search_term:
        query = query.filter(CoreMedicine.medicine_name.ilike(f"%{search_term}%"))
    
    # Filter by category
    if category:
        query = query.filter(CoreMedicine.medicine_category == category)
    
    # Filter by price range(s)
    if price_range:
        price_filters = []
        
        for range_str in price_range:
            if range_str == "0-100":
                price_filters.append(
                    (CoreMedicine.final_selling_price >= 0) & 
                    (CoreMedicine.final_selling_price <= 100)
                )
            elif range_str == "100-500":
                price_filters.append(
                    (CoreMedicine.final_selling_price > 100) & 
                    (CoreMedicine.final_selling_price <= 500)
                )
            elif range_str == "500-1000":
                price_filters.append(
                    (CoreMedicine.final_selling_price > 500) & 
                    (CoreMedicine.final_selling_price <= 1000)
                )
            elif range_str == "1000-5000":
                price_filters.append(
                    (CoreMedicine.final_selling_price > 1000) & 
                    (CoreMedicine.final_selling_price <= 5000)
                )
            elif range_str == "5000+":
                price_filters.append(CoreMedicine.final_selling_price > 5000)
        
        # Combine all price filters with OR logic
        if price_filters:
            query = query.filter(or_(*price_filters))
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    medicines = query.offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "count": len(medicines),
        "data": [medicine.to_dict() for medicine in medicines]
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
    prescription_required: Optional[str] = Form(None),
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
    if prescription_required is not None:
        medicine.prescription_required = prescription_required
    
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
