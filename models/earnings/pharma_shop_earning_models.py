from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from db import Base

class Earning(Base):
    __tablename__ = "earnings"

    earning_id = Column(String, primary_key=True, index=True)
    shop_id = Column(String, ForeignKey("pharma_shop_users.shop_id"), nullable=True, index=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False, unique=True, index=True)

    # Financial Breakdown
    total_bill_amount = Column(Float, nullable=False) # Total collected from customer
    platform_fee_deduction = Column(Float, nullable=False, default=0.0)
    delivery_fee_deduction = Column(Float, nullable=False, default=0.0)
    taxes_deduction = Column(Float, nullable=False, default=0.0)
    
    # What the shop actually makes: total_bill_amount - (platform_fee + delivery_fee + taxes)
    net_earning = Column(Float, nullable=False)

    # Accounting tracking based on payment mode
    # If "cod", the shop collected the cash, so they OWE the platform the deductions.
    # If "online", the platform collected the cash, so the platform OWES the shop the net_earning.
    payment_mode = Column(String, nullable=False) 
    
    # Settlement status between your platform and the shop: "pending", "settled"
    settlement_status = Column(String, nullable=False, default="pending", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    settled_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "earning_id": self.earning_id,
            "shop_id": self.shop_id,
            "order_id": self.order_id,
            "total_bill_amount": self.total_bill_amount,
            "platform_fee_deduction": self.platform_fee_deduction,
            "delivery_fee_deduction": self.delivery_fee_deduction,
            "taxes_deduction": self.taxes_deduction,
            "net_earning": self.net_earning,
            "payment_mode": self.payment_mode,
            "settlement_status": self.settlement_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settled_at": self.settled_at
        }