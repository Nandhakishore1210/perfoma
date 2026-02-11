"""
SQLAlchemy models for database persistence
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base

class Upload(Base):
    __tablename__ = "uploads"

    upload_id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    file_type = Column(String)
    file_path = Column(String)  # Path to local file (ephemeral on Render)
    total_records = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Store parsed records as JSON to avoid complex relational mapping for now
    # This allows us to reconstruct the exact data needed for analysis
    records = Column(JSON) 

class Analysis(Base):
    __tablename__ = "analyses"

    upload_id = Column(String, primary_key=True, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    total_students = Column(Integer)
    total_subjects = Column(Integer)
    
    # Store complete analysis result as JSON
    result_data = Column(JSON)
