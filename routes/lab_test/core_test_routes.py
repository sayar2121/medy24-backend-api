from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from db import get_db
from models.lab_test.core_test_models import CoreLabTest
from services.lab_test.core_test_id_generator import generate_core_test_id
from services.lab_test.test_photo_upload import upload_test_photo, delete_test_photo
import os

router = APIRouter(prefix="/core-tests", tags=["Core Lab Tests"])

@router.post("/")
async def create_core_test(
    test_name: str = Form(...),
    test_category: str = Form(...),
    sample_type: str = Form(...),
    description: Optional[str] = Form(None),
    parameters: Optional[str] = Form(None), # Expecting JSON string
    precautions: Optional[str] = Form(None), # Expecting JSON string
    test_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # Generate ID
    core_test_id = generate_core_test_id(test_name)
    
    # Process JSON strings
    params_json = json.loads(parameters) if parameters else []
    precaus_json = json.loads(precautions) if precautions else []
    
    # Handle Photo
    photo_url = None
    if test_photo:
        photo_url = upload_test_photo(test_photo, core_test_id, test_name)
    
    new_test = CoreLabTest(
        core_test_id=core_test_id,
        test_name=test_name,
        test_category=test_category,
        sample_type=sample_type,
        description=description,
        parameters=params_json,
        precautions=precaus_json,
        test_photo_url=photo_url
    )
    
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    return new_test

@router.get("/")
async def get_all_tests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=20),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * limit
    tests = db.query(CoreLabTest).offset(offset).limit(limit).all()
    total = db.query(CoreLabTest).count()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": tests
    }

@router.get("/{test_id}")
async def get_test_by_id(test_id: str, db: Session = Depends(get_db)):
    test = db.query(CoreLabTest).filter(CoreLabTest.core_test_id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@router.put("/{test_id}")
async def update_test_by_id(
    test_id: str,
    test_name: Optional[str] = Form(None),
    test_category: Optional[str] = Form(None),
    sample_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    parameters: Optional[str] = Form(None),
    precautions: Optional[str] = Form(None),
    test_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    test = db.query(CoreLabTest).filter(CoreLabTest.core_test_id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if test_name: test.test_name = test_name
    if test_category: test.test_category = test_category
    if sample_type: test.sample_type = sample_type
    if description: test.description = description
    if parameters: test.parameters = json.loads(parameters)
    if precautions: test.precautions = json.loads(precautions)
    
    if test_photo:
        # Delete old photo
        if test.test_photo_url:
            delete_test_photo(test.test_photo_url)
        # Upload new photo
        test.test_photo_url = upload_test_photo(test_photo, test_id, test.test_name)
    
    db.commit()
    db.refresh(test)
    return test

@router.delete("/")
async def delete_tests_by_ids(test_ids: List[str] = Body(...), db: Session = Depends(get_db)):
    tests = db.query(CoreLabTest).filter(CoreLabTest.core_test_id.in_(test_ids)).all()
    if not tests:
        raise HTTPException(status_code=404, detail="No tests found with provided IDs")
    
    for test in tests:
        if test.test_photo_url:
            delete_test_photo(test.test_photo_url)
        db.delete(test)
    
    db.commit()
    return {"message": f"Successfully deleted {len(tests)} tests"}
