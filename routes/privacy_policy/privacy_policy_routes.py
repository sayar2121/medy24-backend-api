from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
from db import get_db
from models.privacy_policy.privacy_policy_models import PrivacyPolicy
from services.privacy_policy.privacy_id_generator import generate_privacy_id

router = APIRouter(prefix="/privacy-policies", tags=["Privacy & Policies"])


@router.post("/create")
async def create_privacy_policy(
    privacy_header: str = Body(...),
    privacy_description: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new privacy policy
    """
    # Generate privacy ID
    privacy_id = generate_privacy_id()
    
    # Create new privacy policy record
    new_privacy = PrivacyPolicy(
        privacy_id=privacy_id,
        privacy_header=privacy_header,
        privacy_description=privacy_description
    )
    
    db.add(new_privacy)
    db.commit()
    db.refresh(new_privacy)
    
    return {
        "message": "Privacy policy created successfully",
        "data": new_privacy.to_dict()
    }


@router.get("/get-all")
async def get_all_privacy_policies(
    db: Session = Depends(get_db)
):
    """
    Get all privacy policies
    """
    policies = db.query(PrivacyPolicy).all()
    
    if not policies:
        return {
            "message": "No privacy policies found",
            "data": []
        }
    
    return {
        "message": "Privacy policies retrieved successfully",
        "total": len(policies),
        "data": [policy.to_dict() for policy in policies]
    }


@router.put("/update/{privacy_id}")
async def update_privacy_policy(
    privacy_id: str,
    privacy_header: str = Body(...),
    privacy_description: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update a privacy policy by privacy ID
    """
    # Find the privacy policy
    policy = db.query(PrivacyPolicy).filter(PrivacyPolicy.privacy_id == privacy_id).first()
    
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Privacy policy with ID '{privacy_id}' not found"
        )
    
    # Update fields
    policy.privacy_header = privacy_header
    policy.privacy_description = privacy_description
    
    db.commit()
    db.refresh(policy)
    
    return {
        "message": "Privacy policy updated successfully",
        "data": policy.to_dict()
    }


@router.delete("/delete/{privacy_id}")
async def delete_privacy_policy(
    privacy_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a privacy policy by privacy ID
    """
    # Find the privacy policy
    policy = db.query(PrivacyPolicy).filter(PrivacyPolicy.privacy_id == privacy_id).first()
    
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Privacy policy with ID '{privacy_id}' not found"
        )
    
    # Delete the privacy policy
    db.delete(policy)
    db.commit()
    
    return {
        "message": "Privacy policy deleted successfully",
        "deleted_privacy_id": privacy_id
    }
