import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional

from db import get_db
from models.cart.cart_models import Cart
from models.medicine.core_medicine_models import CoreMedicine
from models.auth.customer_user_models import CustomerUser
from services.cart.cart_id_generator import generate_cart_id

router = APIRouter(prefix="/cart", tags=["Cart"])


def get_customer_id_from_header(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract customer ID from authorization header
    Expected format: "Bearer <customer_id>"
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        return parts[1]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authorization format")


def get_or_create_cart(customer_id: str, db: Session) -> Cart:
    """
    Get existing cart for customer or create a new one
    """
    cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
    
    if not cart:
        # Create new cart
        cart = Cart(
            cart_id=generate_cart_id(),
            customer_id=customer_id,
            items=[],
            total_price=0.0
        )
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    return cart


def calculate_total_price(items: list) -> float:
    """
    Calculate total price from cart items
    """
    total = 0.0
    for item in items:
        total += item.get("subtotal", 0.0)
    return round(total, 2)


@router.post("/add-item")
async def add_item_to_cart(
    medicine_id: str = Body(...),
    quantity: int = Body(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Add item to cart or update quantity if item already exists.
    
    Request body:
    {
        "medicine_id": "MED1234567890",
        "quantity": 2
    }
    
    Authorization: Bearer <customer_id>
    """
    # Validate inputs
    if not medicine_id or quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid medicine_id or quantity")
    
    customer_id = get_customer_id_from_header(authorization)
    
    # Verify customer exists
    customer = db.query(CustomerUser).filter(CustomerUser.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Verify medicine exists
    medicine = db.query(CoreMedicine).filter(CoreMedicine.medicine_id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    # Get or create cart
    cart = get_or_create_cart(customer_id, db)
    
    # Check if item already exists in cart
    existing_item = None
    item_index = None
    for idx, item in enumerate(cart.items):
        if item["medicine_id"] == medicine_id:
            existing_item = item
            item_index = idx
            break
    
    if existing_item:
        # Update quantity - modify item and reassign list
        existing_item["quantity"] = quantity
        existing_item["subtotal"] = round(quantity * existing_item["price_per_unit"], 2)
        cart.items[item_index] = existing_item
    else:
        # Add new item
        new_item = {
            "medicine_id": medicine_id,
            "medicine_name": medicine.medicine_name,
            "quantity": quantity,
            "price_per_unit": medicine.final_selling_price,
            "subtotal": round(quantity * medicine.final_selling_price, 2),
            "medicine_photo": medicine.medicine_photo
        }
        cart.items.append(new_item)
    
    # Explicitly mark items column as modified for SQLAlchemy
    flag_modified(cart, "items")
    
    # Recalculate total price
    cart.total_price = calculate_total_price(cart.items)
    
    db.commit()
    db.refresh(cart)
    
    return {
        "status": "success",
        "message": f"Item added/updated in cart",
        "cart": cart.to_dict()
    }


@router.put("/update-item/{medicine_id}")
async def update_item_quantity(
    medicine_id: str,
    quantity: int = Body(..., embed=True),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Update quantity of an item in cart.
    
    Request body:
    {
        "quantity": 5
    }
    
    Authorization: Bearer <customer_id>
    """
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    
    customer_id = get_customer_id_from_header(authorization)
    
    # Get cart
    cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Find item in cart and update
    item_found = False
    for item in cart.items:
        if item["medicine_id"] == medicine_id:
            item["quantity"] = quantity
            item["subtotal"] = round(quantity * item["price_per_unit"], 2)
            item_found = True
            break
    
    if not item_found:
        raise HTTPException(status_code=404, detail="Medicine not found in cart")
    
    # Explicitly mark items column as modified for SQLAlchemy
    flag_modified(cart, "items")
    
    # Recalculate total price
    cart.total_price = calculate_total_price(cart.items)
    
    db.commit()
    db.refresh(cart)
    
    return {
        "status": "success",
        "message": f"Item quantity updated",
        "cart": cart.to_dict()
    }


@router.delete("/remove-item/{medicine_id}")
async def remove_item_from_cart(
    medicine_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Remove an item from cart.
    
    Authorization: Bearer <customer_id>
    """
    customer_id = get_customer_id_from_header(authorization)
    
    # Get cart
    cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Find and remove item
    original_length = len(cart.items)
    cart.items = [item for item in cart.items if item["medicine_id"] != medicine_id]
    
    if len(cart.items) == original_length:
        raise HTTPException(status_code=404, detail="Medicine not found in cart")
        
    # Explicitly mark items column as modified for SQLAlchemy
    flag_modified(cart, "items")
    
    # Recalculate total price
    cart.total_price = calculate_total_price(cart.items)
    
    db.commit()
    db.refresh(cart)
    
    return {
        "status": "success",
        "message": f"Item removed from cart",
        "cart": cart.to_dict()
    }


@router.get("/")
async def get_cart(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get cart details for the currently logged-in customer.
    
    Authorization: Bearer <customer_id>
    
    Returns complete cart with all items, total price, and item count.
    """
    customer_id = get_customer_id_from_header(authorization)
    
    # Verify customer exists
    customer = db.query(CustomerUser).filter(CustomerUser.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get or create cart
    cart = get_or_create_cart(customer_id, db)
    
    return {
        "status": "success",
        "cart": cart.to_dict()
    }


@router.get("/get-all")
async def get_cart_legacy(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get customer's cart. (Legacy endpoint - use GET / instead)
    
    Authorization: Bearer <customer_id>
    """
    customer_id = get_customer_id_from_header(authorization)
    
    # Get or create cart
    cart = get_or_create_cart(customer_id, db)
    
    return {
        "status": "success",
        "cart": cart.to_dict()
    }


@router.delete("/clear")
async def clear_cart(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Clear all items from customer's cart.
    
    Authorization: Bearer <customer_id>
    """
    customer_id = get_customer_id_from_header(authorization)
    
    # Get cart
    cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Clear items
    cart.items = []
    cart.total_price = 0.0
    
    db.commit()
    db.refresh(cart)
    
    return {
        "status": "success",
        "message": "Cart cleared",
        "cart": cart.to_dict()
    }


@router.get("/summary")
async def get_cart_summary(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get quick summary of customer's cart (item count and total price).
    
    Authorization: Bearer <customer_id>
    """
    customer_id = get_customer_id_from_header(authorization)
    
    # Get cart
    cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
    if not cart:
        return {
            "total_items": 0,
            "total_price": 0.0,
            "is_empty": True
        }
    
    return {
        "total_items": len(cart.items),
        "total_price": cart.total_price,
        "is_empty": len(cart.items) == 0
    }
