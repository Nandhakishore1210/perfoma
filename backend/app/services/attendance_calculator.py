"""
Attendance calculation engine with OD/ML adjustment logic
"""
from typing import List
from app.models.schemas import SubjectAttendance, StudentAttendance
from app.core.rules import OD_ML_RULES, get_category_for_percentage, get_category_details
from app.core.config import settings


class AttendanceCalculator:
    """Core attendance calculation service"""
    
    def __init__(self):
        self.od_ml_threshold = settings.OD_ML_THRESHOLD
        self.enable_od_ml = settings.ENABLE_OD_ML_ADJUSTMENT
    
    def calculate_percentage(self, attended: int, conducted: int) -> float:
        """
        Calculate attendance percentage
        
        Args:
            attended: Number of classes attended
            conducted: Total classes conducted
            
        Returns:
            Attendance percentage (0-100)
        """
        if conducted == 0:
            return 0.0
        
        percentage = (attended / conducted) * 100
        return round(percentage, 2)
    
    def apply_od_ml_adjustment(
        self, 
        subject: SubjectAttendance
    ) -> SubjectAttendance:
        """
        Apply OD/ML adjustment if attendance is below threshold
        
        Args:
            subject: Subject attendance data
            
        Returns:
            Updated subject with adjusted attendance
        """
        # Calculate original percentage
        original_percentage = self.calculate_percentage(
            subject.classes_attended,
            subject.classes_conducted
        )
        subject.original_percentage = original_percentage
        
        # Check if adjustment should be applied
        should_adjust = (
            self.enable_od_ml and
            original_percentage < self.od_ml_threshold and
            (subject.od_count > 0 or subject.ml_count > 0)
        )
        
        if should_adjust:
            # Add OD/ML to attended classes
            adjusted_attended = (
                subject.classes_attended + 
                subject.od_count + 
                subject.ml_count
            )
            
            # Ensure adjusted doesn't exceed conducted
            adjusted_attended = min(adjusted_attended, subject.classes_conducted)
            
            # Calculate new percentage
            final_percentage = self.calculate_percentage(
                adjusted_attended,
                subject.classes_conducted
            )
            
            subject.final_percentage = final_percentage
            subject.od_ml_adjusted = True
        else:
            # No adjustment needed
            subject.final_percentage = original_percentage
            subject.od_ml_adjusted = False
        
        # Determine category
        category_key = get_category_for_percentage(subject.final_percentage)
        category_details = get_category_details(category_key)
        
        subject.category = category_key
        subject.category_label = category_details["label"]
        subject.category_color = category_details["color"]
        
        return subject
    
    def calculate_student_attendance(
        self,
        student_id: str,
        student_name: str,
        subjects: List[SubjectAttendance]
    ) -> StudentAttendance:
        """
        Calculate complete attendance for a student
        
        Args:
            student_id: Student identifier
            student_name: Student name
            subjects: List of subject attendance records
            
        Returns:
            Complete StudentAttendance object
        """
        # Process each subject
        processed_subjects = []
        for subject in subjects:
            processed = self.apply_od_ml_adjustment(subject)
            processed_subjects.append(processed)
        
        # Calculate overall attendance
        if processed_subjects:
            total_conducted = sum(s.classes_conducted for s in processed_subjects)
            total_attended = sum(s.classes_attended for s in processed_subjects)
            
            # For overall, use adjusted attendance
            total_adjusted_attended = sum(
                s.classes_attended + (s.od_count + s.ml_count if s.od_ml_adjusted else 0)
                for s in processed_subjects
            )
            
            overall_percentage = self.calculate_percentage(
                total_adjusted_attended,
                total_conducted
            )
            overall_category = get_category_for_percentage(overall_percentage)
        else:
            overall_percentage = 0.0
            overall_category = "critical"
        
        return StudentAttendance(
            student_id=student_id,
            student_name=student_name,
            subjects=processed_subjects,
            overall_percentage=overall_percentage,
            overall_category=overall_category
        )
    
    def calculate_category_distribution(
        self,
        students: List[StudentAttendance]
    ) -> dict:
        """
        Calculate distribution of students across categories
        
        Args:
            students: List of student attendance records
            
        Returns:
            Dict with category counts
        """
        distribution = {
            "critical": 0,
            "danger": 0,
            "border": 0,
            "safe": 0
        }
        
        for student in students:
            if student.overall_category in distribution:
                distribution[student.overall_category] += 1
        
        return distribution


# Singleton instance
attendance_calculator = AttendanceCalculator()
