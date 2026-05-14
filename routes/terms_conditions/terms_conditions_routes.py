from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
from db import get_db
from models.terms_conditions.terms_conditions_models import TermsConditions
from services.terms_conditions.term_id_generator import generate_term_id

router = APIRouter(prefix="/terms-conditions", tags=["Terms & Conditions"])


@router.post("/create")
async def create_term(
    term_header: str = Body(...),
    term_description: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new term and condition
    """
    # Generate term ID
    term_id = generate_term_id()
    
    # Create new term record
    new_term = TermsConditions(
        term_id=term_id,
        term_header=term_header,
        term_description=term_description
    )
    
    db.add(new_term)
    db.commit()
    db.refresh(new_term)
    
    return {
        "message": "Term and condition created successfully",
        "data": new_term.to_dict()
    }


@router.get("/get-all")
async def get_all_terms(
    db: Session = Depends(get_db)
):
    """
    Get all terms and conditions
    """
    terms = db.query(TermsConditions).all()
    
    if not terms:
        return {
            "message": "No terms and conditions found",
            "data": []
        }
    
    return {
        "message": "Terms and conditions retrieved successfully",
        "total": len(terms),
        "data": [term.to_dict() for term in terms]
    }


@router.put("/update/{term_id}")
async def update_term(
    term_id: str,
    term_header: str = Body(...),
    term_description: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update a term and condition by term ID
    """
    # Find the term
    term = db.query(TermsConditions).filter(TermsConditions.term_id == term_id).first()
    
    if not term:
        raise HTTPException(
            status_code=404,
            detail=f"Term with ID '{term_id}' not found"
        )
    
    # Update fields
    term.term_header = term_header
    term.term_description = term_description
    
    db.commit()
    db.refresh(term)
    
    return {
        "message": "Term and condition updated successfully",
        "data": term.to_dict()
    }


@router.delete("/delete/{term_id}")
async def delete_term(
    term_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a term and condition by term ID
    """
    # Find the term
    term = db.query(TermsConditions).filter(TermsConditions.term_id == term_id).first()
    
    if not term:
        raise HTTPException(
            status_code=404,
            detail=f"Term with ID '{term_id}' not found"
        )
    
    # Delete the term
    db.delete(term)
    db.commit()
    
    return {
        "message": "Term and condition deleted successfully",
        "deleted_term_id": term_id
    }
