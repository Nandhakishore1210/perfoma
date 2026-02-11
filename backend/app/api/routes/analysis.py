"""
Attendance analysis API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import json

from app.core.database import get_db
from app.models.sql_models import Upload, Analysis
from app.models.schemas import (
    AttendanceAnalysisResponse,
    StudentAttendance,
    ReportRequest,
    ReportResponse,
    AttendanceRecordInput
)
from app.services.subject_merger import subject_merger
from app.services.attendance_calculator import attendance_calculator
from app.services.report_generator import report_generator

router = APIRouter()

@router.post("/analyze/{upload_id}", response_model=AttendanceAnalysisResponse)
async def analyze_attendance(upload_id: str, regulation: str = "U18", db: Session = Depends(get_db)):
    """
    Analyze attendance data for an upload
    
    - **upload_id**: Upload identifier
    - **regulation**: Regulation type (U18 or R24)
    """
    # Check if upload exists in DB
    db_upload = db.query(Upload).filter(Upload.upload_id == upload_id).first()
    if not db_upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Get upload data and convert back to Pydantic models
    records_data = db_upload.records
    records = [AttendanceRecordInput(**rec) for rec in records_data]
    
    # Step 1: Merge Theory/Lab subjects
    merged_subjects = subject_merger.process_all_subjects(records, regulation=regulation)
    
    # Step 2: Calculate attendance for each student
    students: List[StudentAttendance] = []
    
    for student_id, subjects in merged_subjects.items():
        # Get student name from first record
        student_name = next(
            (rec.student_name for rec in records if rec.student_id == student_id),
            None
        )
        
        # Calculate attendance
        student_attendance = attendance_calculator.calculate_student_attendance(
            student_id=student_id,
            student_name=student_name,
            subjects=subjects
        )
        
        students.append(student_attendance)
    
    # Sort students by ID
    students.sort(key=lambda s: s.student_id)
    
    # Calculate category distribution
    category_dist = attendance_calculator.calculate_category_distribution(students)
    
    # Count unique subjects
    all_subjects = set()
    for student in students:
        for subject in student.subjects:
            all_subjects.add(subject.subject_code)
    
    # Create analysis response object (not DB model yet w.r.t structure)
    analysis_response = AttendanceAnalysisResponse(
        upload_id=upload_id,
        processed_at=datetime.utcnow(),
        total_students=len(students),
        total_subjects=len(all_subjects),
        students=students,
        category_distribution=category_dist
    )
    
    # Store analysis in DB
    try:
        # Convert response to dict for storage
        analysis_json = analysis_response.dict()
        # Handle datetime serialization if needed, though Pydantic .dict() usually works with custom encoders or we store as string if JSON field requires 
        # But SQLAlchney JSON type handles dicts. Datetime in the dict might be an issue for standard JSON.
        # Let's ensure datetime is stringified for JSON storage if DB requires it.
        # Pydantic's .json() gives a string, json.loads() gives a dict with strings.
        analysis_dict = json.loads(analysis_response.json())
        
        # Check if analysis already exists
        db_analysis = db.query(Analysis).filter(Analysis.upload_id == upload_id).first()
        if db_analysis:
            db_analysis.processed_at = analysis_response.processed_at
            db_analysis.total_students = analysis_response.total_students
            db_analysis.total_subjects = analysis_response.total_subjects
            db_analysis.result_data = analysis_dict
        else:
            db_analysis = Analysis(
                upload_id=upload_id,
                processed_at=analysis_response.processed_at,
                total_students=analysis_response.total_students,
                total_subjects=analysis_response.total_subjects,
                result_data=analysis_dict
            )
            db.add(db_analysis)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return analysis_response


@router.get("/analysis/{upload_id}", response_model=AttendanceAnalysisResponse)
async def get_analysis(upload_id: str, db: Session = Depends(get_db)):
    """
    Get stored analysis results
    
    - **upload_id**: Upload identifier
    """
    db_analysis = db.query(Analysis).filter(Analysis.upload_id == upload_id).first()
    if not db_analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Please run analysis first."
        )
    
    return db_analysis.result_data


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest, db: Session = Depends(get_db)):
    """
    Generate downloadable report
    
    - **upload_id**: Upload identifier
    - **format**: Report format (excel or pdf)
    """
    # Check if analysis exists
    db_analysis = db.query(Analysis).filter(Analysis.upload_id == request.upload_id).first()
    if not db_analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Please run analysis first."
        )
    
    # Reconstruct analysis object from stored JSON
    try:
        analysis_data = db_analysis.result_data
        analysis = AttendanceAnalysisResponse(**analysis_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data corruption error: {str(e)}")
    
    # Generate report based on format
    if request.format.lower() == "excel":
        try:
            filepath = report_generator.generate_excel_report(analysis)
            
            return ReportResponse(
                filename=filepath.split('/')[-1],
                file_path=filepath,
                format="excel"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate report: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported report format: {request.format}"
        )


@router.get("/reports/download/{filename}")
async def download_report(filename: str):
    """
    Download generated report
    
    - **filename**: Report filename
    """
    from pathlib import Path
    
    filepath = Path("/tmp/reports") / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/summary/{upload_id}")
async def get_summary(upload_id: str, db: Session = Depends(get_db)):
    """
    Get quick summary statistics
    
    - **upload_id**: Upload identifier
    """
    db_analysis = db.query(Analysis).filter(Analysis.upload_id == upload_id).first()
    if not db_analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Please run analysis first."
        )
    
    analysis_data = db_analysis.result_data
    
    # Extract critical students from JSON data
    students = analysis_data.get("students", [])
    critical_students = [
        {
            "student_id": s["student_id"],
            "student_name": s.get("student_name"),
            "percentage": s["overall_percentage"]
        }
        for s in students
        if s.get("overall_category") == "critical"
    ]
    
    return {
        "upload_id": upload_id,
        "total_students": db_analysis.total_students,
        "total_subjects": db_analysis.total_subjects,
        "category_distribution": analysis_data.get("category_distribution", {}),
        "critical_students": critical_students
    }

