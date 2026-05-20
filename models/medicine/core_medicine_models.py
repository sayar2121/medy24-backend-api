from sqlalchemy import Column, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from db import Base

class CoreMedicine(Base):
    __tablename__ = "core_medicines"

    medicine_id = Column(String, primary_key=True, index=True)
    medicine_name = Column(String, nullable=False)
    medicine_category = Column(String, nullable=False)
    medicine_photo = Column(String, nullable=True)
    medicine_quantity = Column(String, nullable=False)
    medicine_description = Column(Text, nullable=True)
    medicine_composition = Column(String, nullable=True)
    precautions = Column(JSON, nullable=True)
    mrp = Column(Float, nullable=False)  # MRP in rupees
    discount_percent = Column(Float, nullable=True)  # Discount percentage
    final_selling_price = Column(Float, nullable=False)  # Auto-calculated: MRP - (MRP * discount_percent / 100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "medicine_id": self.medicine_id,
            "medicine_name": self.medicine_name,
            "medicine_category": self.medicine_category,
            "medicine_photo": self.medicine_photo,
            "medicine_quantity": self.medicine_quantity,
            "medicine_description": self.medicine_description,
            "medicine_composition": self.medicine_composition,
            "precautions": self.precautions,
            "mrp": self.mrp,
            "discount_percent": self.discount_percent,
            "final_selling_price": self.final_selling_price,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
