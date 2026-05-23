from sqlalchemy import Column, String, DateTime, Float, JSON, ForeignKey
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.sql import func
from db import Base


class Cart(Base):
    __tablename__ = "carts"

    cart_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customer_users.customer_id"), nullable=False, index=True, unique=True)
    
    # Store cart items as JSON array
    # Each item: {
    #   "medicine_id": str,
    #   "medicine_name": str,
    #   "quantity": int,
    #   "price_per_unit": float (price at time of adding),
    #   "subtotal": float (quantity * price_per_unit),
    #   "medicine_photo": str (optional)
    # }
    items = Column(MutableList.as_mutable(JSON), nullable=False, default=list)
    
    total_price = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "cart_id": self.cart_id,
            "customer_id": self.customer_id,
            "items": self.items or [],
            "total_price": self.total_price,
            "total_items": len(self.items) if self.items else 0,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
