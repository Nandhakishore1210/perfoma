"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime


# ============= Input Models =============

class AttendanceRecordInput(BaseModel):
    """Single attendance record from uploaded file"""
    student_id: str = Field(..., description="Student roll number or ID")
    student_name: Optional[str] = None
    subject_code: str = Field(..., description="Subject code (e.g., CS301T, CS301L)")
    subject_name: Optional[str] = None
    classes_conducted: int = Field(..., ge=0, description="Total classes conducted")
    classes_attended: int = Field(..., ge=0, description="Classes attended by student")
    od_count: Optional[int] = Field(0, ge=0, description="On Duty count")
    ml_count: Optional[int] = Field(0, ge=0, description="Medical Leave count")
    
    @validator('classes_attended')
    def attended_not_greater_than_conducted(cls, v, values):
        if 'classes_conducted' in values and v > values['classes_conducted']:
            raise ValueError('Classes attended cannot be greater than classes conducted')
        return v


class FileUploadResponse(BaseModel):
    """Response after file upload"""
    upload_id: str
    filename: str
    file_type: str
    total_records: int
    preview: List[AttendanceRecordInput]
    message: str


# ============= Processing Models =============

class SubjectComponent(BaseModel):
    """Component of a merged subject (e.g., Theory or Lab part)"""
    subject_code: str
    subject_name: Optional[str]
    classes_conducted: int
    classes_attended: int
    od_count: int = 0
    ml_count: int = 0
    percentage: float = 0.0

class SubjectAttendance(BaseModel):
    """Combined subject attendance (Theory + Lab merged)"""
    subject_code: str
    subject_name: Optional[str]
    is_combined: bool = Field(
        default=False,
        description="True if theory and lab were combined"
    )
    combined_from: Optional[List[str]] = Field(
        default=None,
        description="Original subject codes if combined (e.g., ['CS301T', 'CS301L'])"
    )
    components: Optional[List['SubjectComponent']] = Field(
        default=None,
        description="Detailed breakdown of combined components"
    )
    classes_conducted: int
    classes_attended: int
    od_count: int = 0
    ml_count: int = 0
    
    # Calculated fields
    original_percentage: float = Field(
        default=0.0,
        description="Attendance % before OD/ML adjustment"
    )
    od_ml_adjusted: bool = Field(
        default=False,
        description="Whether OD/ML adjustment was applied"
    )
    final_percentage: float = Field(
        default=0.0,
        description="Final attendance % after adjustments"
    )
    category: str = Field(
        default="safe",
        description="Risk category: critical, danger, border, safe"
    )
    category_label: str = ""
    category_color: str = ""


class StudentAttendance(BaseModel):
    """Complete attendance record for a student"""
    student_id: str
    student_name: Optional[str]
    subjects: List[SubjectAttendance]
    overall_percentage: float = 0.0
    overall_category: str = "safe"


class AttendanceAnalysisResponse(BaseModel):
    """Complete analysis response"""
    upload_id: str
    processed_at: datetime
    total_students: int
    total_subjects: int
    students: List[StudentAttendance]
    
    # Summary statistics
    category_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of students in each category"
    )


# ============= Report Models =============

class ReportRequest(BaseModel):
    """Request for report generation"""
    upload_id: str
    format: str = Field(
        default="excel",
        description="Report format: excel or pdf"
    )
    include_charts: bool = True
    include_summary: bool = True


class ReportResponse(BaseModel):
    """Report generation response"""
    filename: str
    file_path: str
    format: str


# ============= Error Models =============

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
