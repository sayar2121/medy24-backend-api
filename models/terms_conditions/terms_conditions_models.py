from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from db import Base


class TermsConditions(Base):
    __tablename__ = "terms_conditions"

    term_id = Column(String, primary_key=True, index=True)
    term_header = Column(String, nullable=False)
    term_description = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "term_id": self.term_id,
            "term_header": self.term_header,
            "term_description": self.term_description,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
