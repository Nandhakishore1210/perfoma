"""
Attendance analysis API endpoints
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
from typing import List

from app.models.schemas import (
    AttendanceAnalysisResponse,
    StudentAttendance,
    ReportRequest,
    ReportResponse
)
from app.services.subject_merger import subject_merger
from app.services.attendance_calculator import attendance_calculator
from app.services.report_generator import report_generator
from app.api.routes.upload import upload_storage

router = APIRouter()

# In-memory storage for analysis results
analysis_storage = {}


@router.post("/analyze/{upload_id}", response_model=AttendanceAnalysisResponse)
async def analyze_attendance(upload_id: str):
    """
    Analyze attendance data for an upload
    
    - **upload_id**: Upload identifier
    """
    # Check if upload exists
    if upload_id not in upload_storage:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Get upload data
    upload_data = upload_storage[upload_id]
    records = upload_data["records"]
    
    # Step 1: Merge Theory/Lab subjects
    merged_subjects = subject_merger.process_all_subjects(records)
    
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
    
    # Create analysis response
    analysis = AttendanceAnalysisResponse(
        upload_id=upload_id,
        processed_at=datetime.now(),
        total_students=len(students),
        total_subjects=len(all_subjects),
        students=students,
        category_distribution=category_dist
    )
    
    # Store analysis
    analysis_storage[upload_id] = analysis
    
    return analysis


@router.get("/analysis/{upload_id}", response_model=AttendanceAnalysisResponse)
async def get_analysis(upload_id: str):
    """
    Get stored analysis results
    
    - **upload_id**: Upload identifier
    """
    if upload_id not in analysis_storage:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Please run analysis first."
        )
    
    return analysis_storage[upload_id]


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """
    Generate downloadable report
    
    - **upload_id**: Upload identifier
    - **format**: Report format (excel or pdf)
    """
    # Check if analysis exists
    if request.upload_id not in analysis_storage:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Please run analysis first."
        )
    
    analysis = analysis_storage[request.upload_id]
    
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
    
    filepath = Path("reports") / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/summary/{upload_id}")
async def get_summary(upload_id: str):
    """
    Get quick summary statistics
    
    - **upload_id**: Upload identifier
    """
    if upload_id not in analysis_storage:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Please run analysis first."
        )
    
    analysis = analysis_storage[upload_id]
    
    return {
        "upload_id": upload_id,
        "total_students": analysis.total_students,
        "total_subjects": analysis.total_subjects,
        "category_distribution": analysis.category_distribution,
        "critical_students": [
            {
                "student_id": s.student_id,
                "student_name": s.student_name,
                "percentage": s.overall_percentage
            }
            for s in analysis.students
            if s.overall_category == "critical"
        ]
    }
