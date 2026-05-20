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

@router.post("/create")
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
    """
    Create a new core lab test
    """
    if not test_name or test_name.strip() == "":
        raise HTTPException(status_code=400, detail="test_name is required")
    
    if not test_category or test_category.strip() == "":
        raise HTTPException(status_code=400, detail="test_category is required")
    
    if not sample_type or sample_type.strip() == "":
        raise HTTPException(status_code=400, detail="sample_type is required")
    
    # Check if test with same name and category already exists
    existing_test = db.query(CoreLabTest).filter(
        CoreLabTest.test_name == test_name,
        CoreLabTest.test_category == test_category
    ).first()
    
    if existing_test:
        raise HTTPException(
            status_code=400,
            detail=f"Test with name '{test_name}' in category '{test_category}' already exists"
        )
    
    # Generate ID
    core_test_id = generate_core_test_id(test_name)
    
    # Process JSON strings
    try:
        params_json = json.loads(parameters) if parameters else []
        precaus_json = json.loads(precautions) if precautions else []
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    
    # Handle Photo
    photo_url = None
    if test_photo:
        try:
            photo_url = upload_test_photo(test_photo, core_test_id, test_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to upload photo: {str(e)}")
    
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
    return {
        "message": "Core test created successfully",
        "test": new_test.to_dict()
    }

@router.get("/get-all")
async def get_all_tests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=20),
    db: Session = Depends(get_db)
):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 20")
    
    offset = (page - 1) * limit
    tests = db.query(CoreLabTest).offset(offset).limit(limit).all()
    total = db.query(CoreLabTest).count()
    return {
        "message": "All core tests retrieved successfully",
        "total": total,
        "page": page,
        "limit": limit,
        "data": tests
    }

@router.get("/search")
async def search_tests(
    name: Optional[str] = Query(None, description="Search by test name (partial match)"),
    category: Optional[str] = Query(None, description="Filter by test category"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=20),
    db: Session = Depends(get_db)
):
    """
    Search core tests by name and/or category with pagination
    
    Query Parameters:
    - name: Partial match on test name (case-insensitive)
    - category: Exact match on test category
    - page: Page number (default: 1)
    - limit: Number of items per page (default: 20, max: 20)
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 20")
    
    if not name and not category:
        raise HTTPException(status_code=400, detail="At least one search parameter (name or category) is required")
    
    offset = (page - 1) * limit
    query = db.query(CoreLabTest)
    
    # Filter by name if provided (case-insensitive partial match)
    if name and name.strip():
        query = query.filter(CoreLabTest.test_name.ilike(f"%{name}%"))
    
    # Filter by category if provided (exact match)
    if category and category.strip():
        query = query.filter(CoreLabTest.test_category == category)
    
    total = query.count()
    tests = query.offset(offset).limit(limit).all()
    
    if not tests:
        return {
            "message": "No tests found matching the search criteria",
            "total": 0,
            "page": page,
            "limit": limit,
            "search_params": {
                "name": name,
                "category": category
            },
            "data": []
        }
    
    return {
        "message": "Tests retrieved successfully",
        "total": total,
        "page": page,
        "limit": limit,
        "search_params": {
            "name": name,
            "category": category
        },
        "data": tests
    }

@router.get("/get-by/{test_id}")
async def get_test_by_id(test_id: str, db: Session = Depends(get_db)):
    """
    Get a core test by ID
    """
    if not test_id or test_id.strip() == "":
        raise HTTPException(status_code=400, detail="test_id is required")
    
    test = db.query(CoreLabTest).filter(CoreLabTest.core_test_id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {
        "message": "Core test retrieved successfully",
        "test": test.to_dict()
    }

@router.put("/update-by/{test_id}")
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
    """
    Update a core test by ID
    """
    if not test_id or test_id.strip() == "":
        raise HTTPException(status_code=400, detail="test_id is required")
    
    test = db.query(CoreLabTest).filter(CoreLabTest.core_test_id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Check if duplicate name and category exists (excluding current test)
    if test_name is not None or test_category is not None:
        updated_name = test_name if test_name is not None else test.test_name
        updated_category = test_category if test_category is not None else test.test_category
        
        duplicate_test = db.query(CoreLabTest).filter(
            CoreLabTest.test_name == updated_name,
            CoreLabTest.test_category == updated_category,
            CoreLabTest.core_test_id != test_id
        ).first()
        
        if duplicate_test:
            raise HTTPException(
                status_code=400,
                detail=f"Test with name '{updated_name}' in category '{updated_category}' already exists"
            )
    
    if test_name and test_name.strip():
        test.test_name = test_name
    if test_category and test_category.strip():
        test.test_category = test_category
    if sample_type and sample_type.strip():
        test.sample_type = sample_type
    if description is not None:
        test.description = description
    if parameters is not None:
        try:
            test.parameters = json.loads(parameters)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format for parameters: {str(e)}")
    if precautions is not None:
        try:
            test.precautions = json.loads(precautions)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format for precautions: {str(e)}")
    
    if test_photo:
        try:
            # Delete old photo
            if test.test_photo_url:
                delete_test_photo(test.test_photo_url)
            # Upload new photo
            test.test_photo_url = upload_test_photo(test_photo, test_id, test.test_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to upload photo: {str(e)}")
    
    db.commit()
    db.refresh(test)
    return {
        "message": "Core test updated successfully",
        "test": test.to_dict()
    }

@router.delete("/delete-by-ids")
async def delete_tests_by_ids(test_ids: List[str] = Body(...), db: Session = Depends(get_db)):
    """
    Delete multiple core tests by their IDs
    """
    if not test_ids or len(test_ids) == 0:
        raise HTTPException(status_code=400, detail="test_ids list cannot be empty")
    
    tests = db.query(CoreLabTest).filter(CoreLabTest.core_test_id.in_(test_ids)).all()
    if not tests:
        raise HTTPException(status_code=404, detail="No tests found with provided IDs")
    
    for test in tests:
        if test.test_photo_url:
            delete_test_photo(test.test_photo_url)
        db.delete(test)
    
    db.commit()
    return {"message": f"Successfully deleted {len(tests)} tests"}
