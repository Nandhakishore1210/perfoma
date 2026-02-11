"""
File upload API endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import shutil
import json
from typing import List

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import FileUploadResponse, ErrorResponse, AttendanceRecordInput
from app.models.sql_models import Upload
from app.services.parser_service import file_parser

router = APIRouter()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload attendance file (Excel or PDF)
    
    - **file**: Attendance file to upload
    """
    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / 1024 / 1024} MB"
        )
    
    # Generate unique upload ID
    upload_id = str(uuid.uuid4())
    
    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(exist_ok=True)
    
    file_path = upload_dir / f"{upload_id}_{file.filename}"
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Parse file
    try:
        records = file_parser.parse_file(str(file_path))
    except Exception as e:
        # Clean up file on parse error
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    if not records:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="No valid attendance records found in file"
        )
    
    # Store upload data in DB
    try:
        # Convert Pydantic models to dict for JSON storage
        records_json = [record.dict() for record in records]
        
        db_upload = Upload(
            upload_id=upload_id,
            filename=file.filename,
            file_type=file_parser.detect_file_type(file.filename),
            file_path=str(file_path),
            total_records=len(records),
            records=records_json
        )
        db.add(db_upload)
        db.commit()
        db.refresh(db_upload)
    except Exception as e:
        # Clean up on DB error
        file_path.unlink(missing_ok=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Return response with preview
    preview_count = min(5, len(records))
    
    return FileUploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        file_type=file_parser.detect_file_type(file.filename),
        total_records=len(records),
        preview=records[:preview_count],
        message=f"Successfully uploaded and parsed {len(records)} records"
    )


@router.get("/uploads/{upload_id}")
async def get_upload(upload_id: str, db: Session = Depends(get_db)):
    """
    Get upload metadata
    
    - **upload_id**: Upload identifier
    """
    db_upload = db.query(Upload).filter(Upload.upload_id == upload_id).first()
    if not db_upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return {
        "upload_id": db_upload.upload_id,
        "filename": db_upload.filename,
        "file_type": db_upload.file_type,
        "total_records": db_upload.total_records
    }


@router.delete("/uploads/{upload_id}")
async def delete_upload(upload_id: str, db: Session = Depends(get_db)):
    """
    Delete uploaded file and its data
    
    - **upload_id**: Upload identifier
    """
    db_upload = db.query(Upload).filter(Upload.upload_id == upload_id).first()
    if not db_upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Delete file
    file_path = Path(db_upload.file_path)
    file_path.unlink(missing_ok=True)
    
    # Remove from DB
    db.delete(db_upload)
    db.commit()
    
    return {"message": "Upload deleted successfully"}

