"""
Application configuration and settings
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Info
    APP_NAME: str = "Automated Proforma System"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".xlsx", ".xls", ".pdf"]
    UPLOAD_DIR: str = "uploads"
    
    # Attendance Rules
    OD_ML_THRESHOLD: float = 75.0
    ENABLE_OD_ML_ADJUSTMENT: bool = True
    
    # Database (Optional)
    DATABASE_URL: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
