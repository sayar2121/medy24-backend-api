from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from db import get_db
from models.lab_test.lab_test_inventory_models import TestInventory
from models.lab_test.core_test_models import CoreLabTest
from services.lab_test.lab_test_id_generator import generate_test_id

router = APIRouter(prefix="/lab-test-inventory", tags=["Lab Test Inventory"])

@router.post("/create")
async def create_test_inventory(
    lab_id: str = Body(...),
    core_test_id: str = Body(...),
    sample_collection_time: str = Body(...),  # e.g., "2 days", "24 hours"
    report_delivery_time: str = Body(...),  # e.g., "3 days", "48 hours"
    price: float = Body(...),
    discount_percent: float = Body(default=0),
    reviews: Optional[List[dict]] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Create a new test inventory entry for a pathology lab
    """
    # Validate core test exists
    lab = db.query(CoreLabTest).filter(CoreLabTest.core_test_id == core_test_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Core test not found")
    
    # Check if test is already in the inventory of this lab
    existing_test = db.query(TestInventory).filter(
        TestInventory.lab_id == lab_id,
        TestInventory.core_test_id == core_test_id
    ).first()
    if existing_test:
        raise HTTPException(status_code=400, detail="This test is already present in your inventory")
    
    # Generate test ID
    test_id = generate_test_id(lab_id)
    
    # Calculate market price after discount
    market_price = price - (price * discount_percent / 100)
    
    new_test = TestInventory(
        test_id=test_id,
        lab_id=lab_id,
        core_test_id=core_test_id,
        sample_collection_time=sample_collection_time,
        report_delivery_time=report_delivery_time,
        price=price,
        discount_percent=discount_percent,
        market_price=market_price,
        reviews=reviews if reviews else []
    )
    
    db.add(new_test)
    db.commit()
    db.refresh(new_test)
    return new_test

@router.get("/get-by/{test_id}")
async def get_test_by_id(test_id: str, db: Session = Depends(get_db)):
    """
    Get a specific test inventory entry by test ID with core test parameters
    """
    test = db.query(TestInventory, CoreLabTest).join(
        CoreLabTest, TestInventory.core_test_id == CoreLabTest.core_test_id
    ).filter(TestInventory.test_id == test_id).first()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test inventory not found")
    
    test_inventory, core_test = test
    test_dict = test_inventory.to_dict()
    test_dict["core_test_details"] = core_test.to_dict()
    
    return test_dict

@router.get("/get-by-lab/{lab_id}")
async def get_tests_by_lab_id(
    lab_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all test inventory entries for a specific lab with core test parameters
    """
    offset = (page - 1) * limit
    
    # Query with join to get core test parameters
    tests = db.query(TestInventory, CoreLabTest).join(
        CoreLabTest, TestInventory.core_test_id == CoreLabTest.core_test_id
    ).filter(TestInventory.lab_id == lab_id).offset(offset).limit(limit).all()
    
    if not tests:
        return {
            "total": 0,
            "page": page,
            "limit": limit,
            "lab_id": lab_id,
            "data": []
        }
    
    # Combine test inventory and core test data
    result_data = []
    for test_inventory, core_test in tests:
        test_dict = test_inventory.to_dict()
        test_dict["core_test_details"] = core_test.to_dict()
        result_data.append(test_dict)
    
    total = db.query(TestInventory).filter(TestInventory.lab_id == lab_id).count()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "lab_id": lab_id,
        "data": result_data
    }

@router.get("/get-all")
async def get_all_tests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all test inventory entries with pagination
    """
    offset = (page - 1) * limit
    
    # Query with join to get core test parameters
    tests = db.query(TestInventory, CoreLabTest).join(
        CoreLabTest, TestInventory.core_test_id == CoreLabTest.core_test_id
    ).offset(offset).limit(limit).all()
    
    if not tests:
        return {
            "total": 0,
            "page": page,
            "limit": limit,
            "data": []
        }
    
    # Combine test inventory and core test data
    result_data = []
    for test_inventory, core_test in tests:
        test_dict = test_inventory.to_dict()
        test_dict["core_test_details"] = core_test.to_dict()
        result_data.append(test_dict)
    
    total = db.query(TestInventory).count()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": result_data
    }

@router.put("/update-by/{test_id}")
async def update_test_inventory_by_id(
    test_id: str,
    sample_collection_time: Optional[str] = Body(None),  # e.g., "2 days", "24 hours"
    report_delivery_time: Optional[str] = Body(None),  # e.g., "3 days", "48 hours"
    price: Optional[float] = Body(None),
    discount_percent: Optional[float] = Body(None),
    reviews: Optional[List[dict]] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Update a test inventory entry by test ID
    """
    test = db.query(TestInventory).filter(TestInventory.test_id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test inventory not found")
    
    if sample_collection_time:
        test.sample_collection_time = sample_collection_time
    if report_delivery_time:
        test.report_delivery_time = report_delivery_time
    if price is not None:
        test.price = price
    if discount_percent is not None:
        test.discount_percent = discount_percent
    if reviews is not None:
        test.reviews = reviews
    
    # Recalculate market price if price or discount changed
    if price is not None or discount_percent is not None:
        final_price = price if price is not None else test.price
        final_discount = discount_percent if discount_percent is not None else test.discount_percent
        test.market_price = final_price - (final_price * final_discount / 100)
    
    db.commit()
    db.refresh(test)
    return test

@router.delete("/delete-by-ids")
async def delete_tests_by_ids(test_ids: List[str] = Body(...), db: Session = Depends(get_db)):
    """
    Delete multiple test inventory entries by their test IDs
    """
    tests = db.query(TestInventory).filter(TestInventory.test_id.in_(test_ids)).all()
    if not tests:
        raise HTTPException(status_code=404, detail="No test inventories found with provided IDs")
    
    for test in tests:
        db.delete(test)
    
    db.commit()
    return {"message": f"Successfully deleted {len(tests)} test inventory entries"}
