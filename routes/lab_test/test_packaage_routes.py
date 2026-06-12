from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from db import get_db
from models.lab_test.test_package_models import TestPackage
from models.lab_test.lab_test_inventory_models import TestInventory
from models.lab_test.core_test_models import CoreLabTest
from services.lab_test.package_id_generator import generate_package_id

router = APIRouter(prefix="/test-packages", tags=["Test Packages"])

@router.post("/create")
async def create_test_package(
    lab_id: str = Body(...),
    package_name: str = Body(...),
    test_ids: List[str] = Body(...),  # List of test IDs to include in the package
    package_description: Optional[str] = Body(None),
    package_sample_collection_time: str = Body(...),  # e.g., "2 days", "24 hours"
    package_report_delivery_time: str = Body(...),  # e.g., "3 days", "48 hours"
    package_market_price: float = Body(...),
    discount_percentage: float = Body(default=0),
    db: Session = Depends(get_db)
):
    """
    Create a new test package with tests from the lab's inventory
    """
    if not test_ids or len(test_ids) == 0:
        raise HTTPException(status_code=400, detail="At least one test must be included in the package")
    
    # Fetch all tests from the inventory
    tests = db.query(TestInventory).filter(
        TestInventory.lab_id == lab_id,
        TestInventory.test_id.in_(test_ids)
    ).all()
    
    if not tests or len(tests) != len(test_ids):
        raise HTTPException(status_code=404, detail="One or more tests not found in lab inventory")
    
    # Generate package ID
    package_id = generate_package_id(lab_id)
    
    # Calculate final price after discount
    package_final_price = package_market_price - (package_market_price * discount_percentage / 100)
    
    new_package = TestPackage(
        package_id=package_id,
        lab_id=lab_id,
        package_name=package_name,
        test_details=test_ids,  # Store only test IDs
        package_description=package_description,
        package_sample_collection_time=package_sample_collection_time,
        package_report_delivery_time=package_report_delivery_time,
        package_market_price=package_market_price,
        discount_percentage=discount_percentage,
        package_final_price=package_final_price
    )
    
    db.add(new_package)
    db.commit()
    db.refresh(new_package)
    return new_package

@router.get("/get-by/{package_id}")
async def get_package_by_id(package_id: str, db: Session = Depends(get_db)):
    """
    Get a specific test package by package ID with enriched test details
    """
    package = db.query(TestPackage).filter(TestPackage.package_id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Test package not found")
    
    # Enrich test details with TestInventory and CoreLabTest information
    enriched_test_details = []
    for test_id in package.test_details:
        test_inv = db.query(TestInventory).filter(TestInventory.test_id == test_id).first()
        if test_inv:
            core_test = db.query(CoreLabTest).filter(
                CoreLabTest.core_test_id == test_inv.core_test_id
            ).first()
            
            enriched_detail = {
                "test_id": test_inv.test_id,
                "core_test_id": test_inv.core_test_id,
                "test_description": test_inv.description if hasattr(test_inv, 'description') else None,
                "test_parameters": test_inv.parameters if hasattr(test_inv, 'parameters') else [],
                "test_precautions": test_inv.precautions if hasattr(test_inv, 'precautions') else [],
                "test_photo_url": test_inv.test_photo_url if hasattr(test_inv, 'test_photo_url') else None,
                "price": test_inv.price,
                "sample_collection_time": test_inv.sample_collection_time,
                "report_delivery_time": test_inv.report_delivery_time
            }
            
            if core_test:
                enriched_detail["core_test_details"] = core_test.to_dict()
            
            enriched_test_details.append(enriched_detail)
    
    package_dict = package.to_dict()
    package_dict["test_details"] = enriched_test_details
    
    return package_dict

@router.get("/get-all")
async def get_all_test_packages(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all test packages with pagination and enriched test details
    """
    offset = (page - 1) * limit
    
    packages = db.query(TestPackage).offset(offset).limit(limit).all()
    
    # Enrich test details with TestInventory and CoreLabTest information
    enriched_packages = []
    for package in packages:
        enriched_test_details = []
        for test_id in package.test_details:
            test_inv = db.query(TestInventory).filter(TestInventory.test_id == test_id).first()
            if test_inv:
                core_test = db.query(CoreLabTest).filter(
                    CoreLabTest.core_test_id == test_inv.core_test_id
                ).first()
                
                enriched_detail = {
                    "test_id": test_inv.test_id,
                    "core_test_id": test_inv.core_test_id,
                    "test_description": test_inv.description if hasattr(test_inv, 'description') else None,
                    "test_parameters": test_inv.parameters if hasattr(test_inv, 'parameters') else [],
                    "test_precautions": test_inv.precautions if hasattr(test_inv, 'precautions') else [],
                    "test_photo_url": test_inv.test_photo_url if hasattr(test_inv, 'test_photo_url') else None,
                    "price": test_inv.price,
                    "sample_collection_time": test_inv.sample_collection_time,
                    "report_delivery_time": test_inv.report_delivery_time
                }
                
                if core_test:
                    enriched_detail["core_test_details"] = core_test.to_dict()
                
                enriched_test_details.append(enriched_detail)
        
        package_dict = package.to_dict()
        package_dict["test_details"] = enriched_test_details
        enriched_packages.append(package_dict)
    
    total = db.query(TestPackage).count()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": enriched_packages
    }

@router.get("/get-by-lab/{lab_id}")
async def get_packages_by_lab_id(
    lab_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all test packages for a specific lab with pagination and enriched test details
    """
    offset = (page - 1) * limit
    
    packages = db.query(TestPackage).filter(
        TestPackage.lab_id == lab_id
    ).offset(offset).limit(limit).all()
    
    # Enrich test details with TestInventory and CoreLabTest information
    enriched_packages = []
    for package in packages:
        enriched_test_details = []
        for test_id in package.test_details:
            test_inv = db.query(TestInventory).filter(TestInventory.test_id == test_id).first()
            if test_inv:
                core_test = db.query(CoreLabTest).filter(
                    CoreLabTest.core_test_id == test_inv.core_test_id
                ).first()
                
                enriched_detail = {
                    "test_id": test_inv.test_id,
                    "core_test_id": test_inv.core_test_id,
                    "test_description": test_inv.description if hasattr(test_inv, 'description') else None,
                    "test_parameters": test_inv.parameters if hasattr(test_inv, 'parameters') else [],
                    "test_precautions": test_inv.precautions if hasattr(test_inv, 'precautions') else [],
                    "test_photo_url": test_inv.test_photo_url if hasattr(test_inv, 'test_photo_url') else None,
                    "price": test_inv.price,
                    "sample_collection_time": test_inv.sample_collection_time,
                    "report_delivery_time": test_inv.report_delivery_time
                }
                
                if core_test:
                    enriched_detail["core_test_details"] = core_test.to_dict()
                
                enriched_test_details.append(enriched_detail)
        
        package_dict = package.to_dict()
        package_dict["test_details"] = enriched_test_details
        enriched_packages.append(package_dict)
    
    total = db.query(TestPackage).filter(TestPackage.lab_id == lab_id).count()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "lab_id": lab_id,
        "data": enriched_packages
    }

@router.put("/update-by/{package_id}")
async def update_package_by_id(
    package_id: str,
    package_name: Optional[str] = Body(None),
    test_ids: Optional[List[str]] = Body(None),  # Update tests in package
    package_description: Optional[str] = Body(None),
    package_sample_collection_time: Optional[str] = Body(None),
    package_report_delivery_time: Optional[str] = Body(None),
    package_market_price: Optional[float] = Body(None),
    discount_percentage: Optional[float] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Update a test package by package ID
    """
    package = db.query(TestPackage).filter(TestPackage.package_id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Test package not found")
    
    # Update package name if provided
    if package_name is not None:
        package.package_name = package_name
    
    # Update test details if new test IDs provided
    if test_ids is not None and len(test_ids) > 0:
        tests = db.query(TestInventory).filter(
            TestInventory.lab_id == package.lab_id,
            TestInventory.test_id.in_(test_ids)
        ).all()
        
        if not tests or len(tests) != len(test_ids):
            raise HTTPException(status_code=404, detail="One or more tests not found in lab inventory")
        
        # Store only test IDs
        package.test_details = test_ids
    
    if package_description is not None:
        package.package_description = package_description
    if package_sample_collection_time is not None:
        package.package_sample_collection_time = package_sample_collection_time
    if package_report_delivery_time is not None:
        package.package_report_delivery_time = package_report_delivery_time
    if package_market_price is not None:
        package.package_market_price = package_market_price
    if discount_percentage is not None:
        package.discount_percentage = discount_percentage
    
    # Recalculate final price if price or discount changed
    if package_market_price is not None or discount_percentage is not None:
        final_price = package_market_price if package_market_price is not None else package.package_market_price
        final_discount = discount_percentage if discount_percentage is not None else package.discount_percentage
        package.package_final_price = final_price - (final_price * final_discount / 100)
    
    db.commit()
    db.refresh(package)
    return package

@router.delete("/delete-by/{package_id}")
async def delete_package_by_id(package_id: str, db: Session = Depends(get_db)):
    """
    Delete a test package by package ID
    """
    package = db.query(TestPackage).filter(TestPackage.package_id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Test package not found")
    
    db.delete(package)
    db.commit()
    return {"message": f"Successfully deleted test package {package_id}"}
