"""
Subject code analyzer and merger service
Handles Theory/Lab subject combination logic
"""
from typing import List, Dict, Tuple
from app.models.schemas import AttendanceRecordInput, SubjectAttendance
from app.core.rules import SUBJECT_CODE_PATTERNS
import re


class SubjectMergerService:
    """Service to analyze and merge Theory/Lab subjects"""
    
    def __init__(self):
        self.theory_suffix = SUBJECT_CODE_PATTERNS["theory_suffix"]
        self.lab_suffix = SUBJECT_CODE_PATTERNS["lab_suffix"]
    
    def extract_base_code(self, subject_code: str) -> Tuple[str, str]:
        """
        Extract base code and type from subject code
        
        Args:
            subject_code: Subject code (e.g., CS301T, CS301L, MATH101)
            
        Returns:
            Tuple of (base_code, subject_type)
            e.g., ("CS301", "T"), ("CS301", "L"), ("MATH101", "")
        """
        subject_code = subject_code.strip().upper()
        
        # Check if ends with T or L
        if subject_code.endswith(self.theory_suffix):
            base_code = subject_code[:-1]
            return base_code, "T"
        elif subject_code.endswith(self.lab_suffix):
            base_code = subject_code[:-1]
            return base_code, "L"
        else:
            # No suffix, standalone subject
            return subject_code, ""
    
    def group_by_student_and_base(
        self, 
        records: List[AttendanceRecordInput]
    ) -> Dict[str, Dict[str, List[AttendanceRecordInput]]]:
        """
        Group attendance records by student and base subject code
        
        Args:
            records: List of attendance records
            
        Returns:
            Nested dict: {student_id: {base_code: [records]}}
        """
        grouped = {}
        
        for record in records:
            student_id = record.student_id
            base_code, _ = self.extract_base_code(record.subject_code)
            
            if student_id not in grouped:
                grouped[student_id] = {}
            
            if base_code not in grouped[student_id]:
                grouped[student_id][base_code] = []
            
            grouped[student_id][base_code].append(record)
        
        return grouped
    
    def merge_theory_lab(
        self, 
        records: List[AttendanceRecordInput]
    ) -> SubjectAttendance:
        """
        Merge theory and lab records for the same subject
        
        Args:
            records: List of records with same base code (may include T and L)
            
        Returns:
            Merged SubjectAttendance object
        """
        if not records:
            raise ValueError("Cannot merge empty records list")
        
        # If only one record, no merging needed
        if len(records) == 1:
            rec = records[0]
            return SubjectAttendance(
                subject_code=rec.subject_code,
                subject_name=rec.subject_name,
                is_combined=False,
                combined_from=None,
                classes_conducted=rec.classes_conducted,
                classes_attended=rec.classes_attended,
                od_count=rec.od_count or 0,
                ml_count=rec.ml_count or 0
            )
        
        # Multiple records - merge them
        base_code, _ = self.extract_base_code(records[0].subject_code)
        combined_from = [rec.subject_code for rec in records]
        
        # Sum up all attendance data
        total_conducted = sum(rec.classes_conducted for rec in records)
        total_attended = sum(rec.classes_attended for rec in records)
        total_od = sum(rec.od_count or 0 for rec in records)
        total_ml = sum(rec.ml_count or 0 for rec in records)
        
        # Use first record's subject name if available
        subject_name = next(
            (rec.subject_name for rec in records if rec.subject_name), 
            None
        )
        
        return SubjectAttendance(
            subject_code=base_code,
            subject_name=subject_name,
            is_combined=True,
            combined_from=combined_from,
            classes_conducted=total_conducted,
            classes_attended=total_attended,
            od_count=total_od,
            ml_count=total_ml
        )
    
    def process_all_subjects(
        self, 
        records: List[AttendanceRecordInput]
    ) -> Dict[str, List[SubjectAttendance]]:
        """
        Process all records and return merged subjects per student
        
        Args:
            records: All attendance records
            
        Returns:
            Dict mapping student_id to list of merged SubjectAttendance
        """
        # Group by student and base subject
        grouped = self.group_by_student_and_base(records)
        
        # Process each student's subjects
        result = {}
        for student_id, subjects in grouped.items():
            student_subjects = []
            
            for base_code, subject_records in subjects.items():
                merged = self.merge_theory_lab(subject_records)
                student_subjects.append(merged)
            
            result[student_id] = student_subjects
        
        return result


# Singleton instance
subject_merger = SubjectMergerService()
