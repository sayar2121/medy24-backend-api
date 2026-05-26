from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from db import Base

class PharmaShopUser(Base):
    __tablename__ = "pharma_shop_users"

    shop_id = Column(String, primary_key=True, index=True)
    shop_name = Column(String, nullable=False)
    shop_address = Column(String, nullable=False)
    shop_photo = Column(String, nullable=True)
    shop_phone_no = Column(String, nullable=False)
    shop_alternative_phone_no = Column(String, nullable=True)
    shop_email = Column(String, unique=True, index=True, nullable=False)
    shop_password = Column(String, nullable=False)
    whatsapp_number = Column(String, nullable=True)
    gstin_no = Column(String, nullable=True)
    drug_license_upload = Column(String, nullable=False)
    pan_card_upload = Column(String, nullable=False)
    registration_certificate_upload = Column(String, nullable=False)
    bank_account_no = Column(String, nullable=True)
    bank_ifsc_code = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    bank_account_name = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # active, terminated, pending, suspended
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "shop_id": self.shop_id,
            "shop_name": self.shop_name,
            "shop_address": self.shop_address,
            "shop_photo": self.shop_photo,
            "shop_phone_no": self.shop_phone_no,
            "shop_alternative_phone_no": self.shop_alternative_phone_no,
            "shop_email": self.shop_email,
            "whatsapp_number": self.whatsapp_number,
            "gstin_no": self.gstin_no,
            "drug_license_upload": self.drug_license_upload,
            "pan_card_upload": self.pan_card_upload,
            "registration_certificate_upload": self.registration_certificate_upload,
            "bank_account_no": self.bank_account_no,
            "bank_ifsc_code": self.bank_ifsc_code,
            "bank_name": self.bank_name,
            "bank_account_name": self.bank_account_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login_at": self.last_login_at
        }
