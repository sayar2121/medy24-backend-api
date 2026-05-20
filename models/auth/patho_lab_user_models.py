from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from db import Base

class PathoLabUser(Base):
    __tablename__ = "patho_lab_users"

    id = Column(Integer, primary_key=True, index=True)
    lab_id = Column(String, unique=True, index=True)
    lab_name = Column(String, nullable=False)
    mobile_number = Column(String, nullable=False)
    email_address = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    gst_number = Column(String, nullable=True)
    pan_number = Column(String, nullable=False)
    nabl_accreditation_number = Column(String, nullable=False)
    address = Column(String, nullable=False)
    lab_logo_url = Column(String, nullable=True)
    registration_certificate_url = Column(String, nullable=False)
    bank_passbook_url = Column(String, nullable=False)
    emergency_contact_number = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    terms_conditions_accepted = Column(Boolean, default=False, nullable=False)
    privacy_policy_accepted = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="pending", nullable=False) # active, suspended, terminated
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
