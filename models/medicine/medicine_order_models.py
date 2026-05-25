from sqlalchemy import Column, String, DateTime, Float, JSON, ForeignKey, Boolean
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy.sql import func
from db import Base

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customer_users.customer_id"), nullable=False, index=True)
    
    # Nullable initially. Populated when a pharma shop accepts the broadcasted order.
    shop_id = Column(String, ForeignKey("pharma_shop_users.shop_id"), nullable=True, index=True)

    # Order Type: "cart" or "prescription"
    order_type = Column(String, nullable=False, default="cart")
    prescription_url = Column(String, nullable=True) # Uploaded image URL for direct orders
    
    # Delivery Info
    receiver_name = Column(String, nullable=False)
    receiver_phone = Column(String, nullable=False)
    delivery_address = Column(MutableDict.as_mutable(JSON), nullable=False) # e.g., {"address": "...", "lat": ..., "lng": ...}

    # Items: Populated immediately for "cart" orders. 
    # For "prescription" orders, shop updates this field manually during packing.
    items = Column(MutableList.as_mutable(JSON), nullable=False, default=list)

    # Pricing details (Passed from Customer App initially, might be updated by shop for prescription orders)
    item_total = Column(Float, nullable=False, default=0.0)
    platform_fee = Column(Float, nullable=False, default=0.0)
    delivery_fee = Column(Float, nullable=False, default=0.0)
    taxes = Column(Float, nullable=False, default=0.0)
    total_bill_amount = Column(Float, nullable=False, default=0.0)

    # Payment Details
    payment_mode = Column(String, nullable=False) # "cod" or "online"
    payment_status = Column(String, nullable=False, default="pending") # "pending", "success", "failed"
    transaction_id = Column(String, nullable=True) # Razorpay transaction ID

    # Order Status Lifecycle: 
    # broadcast -> accepted -> packing -> out_for_delivery -> delivered (or cancelled)
    order_status = Column(String, nullable=False, default="broadcast", index=True)

    # Rider details (Updated by Pharma Shop)
    rider_name = Column(String, nullable=True)
    rider_phone = Column(String, nullable=True)
    vehicle_number = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "shop_id": self.shop_id,
            "order_type": self.order_type,
            "prescription_url": self.prescription_url,
            "receiver_name": self.receiver_name,
            "receiver_phone": self.receiver_phone,
            "delivery_address": self.delivery_address,
            "items": self.items or [],
            "item_total": self.item_total,
            "platform_fee": self.platform_fee,
            "delivery_fee": self.delivery_fee,
            "taxes": self.taxes,
            "total_bill_amount": self.total_bill_amount,
            "payment_mode": self.payment_mode,
            "payment_status": self.payment_status,
            "transaction_id": self.transaction_id,
            "order_status": self.order_status,
            "rider_name": self.rider_name,
            "rider_phone": self.rider_phone,
            "vehicle_number": self.vehicle_number,
            "vehicle_model": self.vehicle_model,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "accepted_at": self.accepted_at,
            "delivered_at": self.delivered_at
        }