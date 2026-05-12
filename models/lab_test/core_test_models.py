from sqlalchemy import Column, String, JSON, DateTime, Integer
from sqlalchemy.sql import func
from db import Base

class CoreLabTest(Base):
    __tablename__ = "core_lab_tests"

    core_test_id = Column(String, primary_key=True, index=True)
    test_name = Column(String, nullable=False)
    test_category = Column(String, nullable=False)
    sample_type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    parameters = Column(JSON, nullable=True)  # List of parameters
    precautions = Column(JSON, nullable=True)  # List of precautions
    test_photo_url = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "core_test_id": self.core_test_id,
            "test_name": self.test_name,
            "test_category": self.test_category,
            "sample_type": self.sample_type,
            "description": self.description,
            "parameters": self.parameters,
            "precautions": self.precautions,
            "test_photo_url": self.test_photo_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
