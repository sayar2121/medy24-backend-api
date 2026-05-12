from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from db import Base

class AboutUs(Base):
    __tablename__ = "about_us"

    id = Column(Integer, primary_key=True, index=True)
    
    company_name = Column(String, nullable=False)
    company_photo = Column(String, nullable=True)
    company_tagline = Column(String, nullable=True)
    company_description_text = Column(String, nullable=True)
    
    mission = Column(String, nullable=True)
    vision = Column(String, nullable=True)
    
    director_name = Column(String, nullable=True)
    director_message = Column(String, nullable=True)
    director_photo = Column(String, nullable=True)
    
    # Partners JSON structure: [{"partner_name", "partner_photo", "partner_website"}, ...]
    partners = Column(JSON, nullable=True)
    
    office_address = Column(String, nullable=True)
    registered_address = Column(String, nullable=True)
    
    email1 = Column(String, nullable=True)
    email2 = Column(String, nullable=True)
    
    phone1 = Column(String, nullable=True)
    phone2 = Column(String, nullable=True)
    
    website = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "company_photo": self.company_photo,
            "company_tagline": self.company_tagline,
            "company_description_text": self.company_description_text,
            "mission": self.mission,
            "vision": self.vision,
            "director_name": self.director_name,
            "director_message": self.director_message,
            "director_photo": self.director_photo,
            "partners": self.partners,
            "office_address": self.office_address,
            "registered_address": self.registered_address,
            "email1": self.email1,
            "email2": self.email2,
            "phone1": self.phone1,
            "phone2": self.phone2,
            "website": self.website,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
