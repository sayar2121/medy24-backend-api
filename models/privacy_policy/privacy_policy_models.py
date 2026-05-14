from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from db import Base


class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    privacy_id = Column(String, primary_key=True, index=True)
    privacy_header = Column(String, nullable=False)
    privacy_description = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "privacy_id": self.privacy_id,
            "privacy_header": self.privacy_header,
            "privacy_description": self.privacy_description,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
