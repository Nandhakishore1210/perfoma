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

        # Helper to process a single component/subject
        def process_component(attended, conducted, posted, od, ml):
            denominator = posted if (posted and posted > 0) else conducted
            pct = self.calculate_percentage(attended, denominator)
            
            # Check eligibility (must be >= 65% in this specific component)
            min_threshold = OD_ML_RULES.get("min_percentage_for_adjustment", 65.0)
            is_eligible = (
                self.enable_od_ml and 
                pct >= min_threshold and 
                (od > 0 or ml > 0)
            )
            
            final_adj_attended = attended
            if is_eligible:
                # Add OD/ML
                raw_adj = attended + od + ml
                # Cap at denominator
                final_adj_attended = min(raw_adj, denominator)
            
            return final_adj_attended, pct

        # Case 1: Combined Subject with Components (Theory + Lab)
        if subject.components and len(subject.components) > 0:
            # 1. Calculate TOTALS across all components
            total_attended_all = 0
            total_posted_all = 0
            total_od_all = 0
            total_ml_all = 0
            
            for comp in subject.components:
                # Get denominator for this component
                comp_denom = comp.classes_posted if (comp.classes_posted and comp.classes_posted > 0) else comp.classes_conducted
                
                # Update totals
                total_attended_all += comp.classes_attended
                total_posted_all += comp_denom
                total_od_all += (comp.od_count or 0)
                total_ml_all += (comp.ml_count or 0)
                
                # Calculate component-level percentage (for display/record only)
                comp.percentage = self.calculate_percentage(comp.classes_attended, comp_denom)
                
                # Base adjustment for component (Per-component logic kept for breakdown display)
                # This ensures the individual rows in reports don't look broken, even if they don't sum strictly to the enhanced total
                comp.adjusted_attended = comp.classes_attended # Default
            
            # 2. Check COMBINED Eligibility
            combined_pct = self.calculate_percentage(total_attended_all, total_posted_all)
            min_threshold = OD_ML_RULES.get("min_percentage_for_adjustment", 65.0)
            
            is_eligible = (
                self.enable_od_ml and
                combined_pct >= min_threshold and
                (total_od_all > 0 or total_ml_all > 0)
            )
            
            # 3. Calculate Overall Adjusted Attendance (The "Enhanced" Total)
            final_adjusted_total = total_attended_all
            
            if is_eligible:
                # Sum everything and cap at Total Posted
                raw_total_adj = total_attended_all + total_od_all + total_ml_all
                final_adjusted_total = min(raw_total_adj, total_posted_all)
            
            # 4. Update Subject Level Fields
            subject.adjusted_attended = final_adjusted_total
            
            # Original %
            subject.original_percentage = combined_pct
            
            # Final % (Based on the Enhanced Total)
            subject.final_percentage = self.calculate_percentage(
                subject.adjusted_attended, 
                total_posted_all
            )
            
            subject.od_ml_adjusted = (subject.final_percentage > subject.original_percentage)

            # 5. Review Component Level Adjustments
            # If we have an "enhanced" total that is greater than the sum of simple component adjustments,
            # we technically have "floating" hours. 
            # For now, we update components to show their 'local' adjusted values (simple cap),
            # but the Subject Total will show the higher value.
            
            for comp in subject.components:
                comp_denom = comp.classes_posted if (comp.classes_posted and comp.classes_posted > 0) else comp.classes_conducted
                
                # Apply simple local adjustment if eligible (just for display consistency)
                if is_eligible:
                    local_adj = comp.classes_attended + (comp.od_count or 0) + (comp.ml_count or 0)
                    comp.adjusted_attended = min(local_adj, comp_denom)
                    comp.final_percentage = self.calculate_percentage(comp.adjusted_attended, comp_denom)
                else:
                    comp.adjusted_attended = comp.classes_attended
                    comp.final_percentage = comp.percentage

        # Case 2: Single Subject (No components)
        else:
            adj_attended, original_pct = process_component(
                subject.classes_attended,
                subject.classes_conducted,
                subject.classes_posted,
                subject.od_count,
                subject.ml_count
            )
            
            subject.original_percentage = original_pct
            subject.adjusted_attended = adj_attended
            
            # Recalculate final percentage
            denom = subject.classes_posted if (subject.classes_posted > 0) else subject.classes_conducted
            subject.final_percentage = self.calculate_percentage(adj_attended, denom)
            
            subject.od_ml_adjusted = (subject.final_percentage > subject.original_percentage)
        
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
            # Use posted if available, else conducted for each subject in the total
            total_conducted = sum(
                s.classes_posted if (s.classes_posted and s.classes_posted > 0) else s.classes_conducted 
                for s in processed_subjects
            )
            total_attended = sum(s.classes_attended for s in processed_subjects)
            
            # For overall, use adjusted attendance based on subject-level rules
            # We must use the effective attended classes from each processed subject
            total_adjusted_attended = sum(
                s.classes_attended + (s.od_count + s.ml_count if s.od_ml_adjusted else 0)
                for s in processed_subjects
            )
            
            overall_original_percentage = self.calculate_percentage(
                total_attended,
                total_conducted
            )
            
            # Recalculate based on the SUM of adjusted values
            overall_final_percentage = self.calculate_percentage(
                total_adjusted_attended,
                total_conducted
            )
            
            # The user wants "overall before applying od" for the main display, 
            # but categorization should be "after applying to each subject".
            overall_percentage = overall_original_percentage
            overall_category = get_category_for_percentage(overall_final_percentage)
            overall_od_ml_adjusted = overall_final_percentage > overall_original_percentage
            
            # Calculate total OD/ML across all subjects
            all_od = sum(s.od_count for s in processed_subjects)
            all_ml = sum(s.ml_count for s in processed_subjects)
        else:
            total_conducted = 0
            total_attended = 0
            overall_percentage = 0.0
            overall_original_percentage = 0.0
            overall_final_percentage = 0.0
            overall_category = "critical"
            overall_od_ml_adjusted = False
            all_od = 0
            all_ml = 0
        
        return StudentAttendance(
            student_id=student_id,
            student_name=student_name,
            subjects=processed_subjects,
            overall_percentage=overall_percentage,
            overall_original_percentage=overall_original_percentage,
            overall_final_percentage=overall_final_percentage,
            overall_category=overall_category,
            overall_od_ml_adjusted=overall_od_ml_adjusted,
            total_od=all_od,
            total_ml=all_ml,
            total_conducted=total_conducted,
            total_attended=total_attended,
            total_adjusted_attended=total_adjusted_attended
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
