"""
Report generation service for Excel and PDF outputs
"""
import pandas as pd
from typing import List
from pathlib import Path
from datetime import datetime
import xlsxwriter
from io import BytesIO

from app.models.schemas import StudentAttendance, AttendanceAnalysisResponse
from app.core.rules import ATTENDANCE_CATEGORIES


class ReportGenerator:
    """Service to generate attendance reports in various formats"""
    
    def __init__(self, output_dir: str = "/tmp/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_excel_report(
        self,
        analysis: AttendanceAnalysisResponse,
        filename: str = None
    ) -> str:
        """
        Generate comprehensive Excel report with formatting
        
        Args:
            analysis: Complete attendance analysis
            filename: Output filename (optional)
            
        Returns:
            Path to generated file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"attendance_report_{timestamp}.xlsx"
        
        filepath = self.output_dir / filename
        
        # Create workbook and worksheets
        workbook = xlsxwriter.Workbook(str(filepath))
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        category_formats = {
            'critical': workbook.add_format({'bg_color': '#FFCDD2', 'border': 1}),
            'danger': workbook.add_format({'bg_color': '#FFE0B2', 'border': 1}),
            'border': workbook.add_format({'bg_color': '#FFF9C4', 'border': 1}),
            'safe': workbook.add_format({'bg_color': '#C8E6C9', 'border': 1})
        }
        
        default_format = workbook.add_format({'border': 1})
        
        # Create detailed worksheet
        ws_detail = workbook.add_worksheet('Detailed Report')
        
        # Headers
        headers = [
            'Student ID', 'Student Name', 'Subject Code', 'Subject Name',
            'Combined', 'Classes Conducted', 'Classes Attended',
            'OD', 'ML', 'Original %', 'Final %', 'OD/ML Applied',
            'Category', 'Status'
        ]
        
        for col, header in enumerate(headers):
            ws_detail.write(0, col, header, header_format)
        
        # Data rows
        row = 1
        for student in analysis.students:
            for subject in student.subjects:
                col = 0
                ws_detail.write(row, col, student.student_id, default_format)
                col += 1
                ws_detail.write(row, col, student.student_name or '', default_format)
                col += 1
                ws_detail.write(row, col, subject.subject_code, default_format)
                col += 1
                ws_detail.write(row, col, subject.subject_name or '', default_format)
                col += 1
                ws_detail.write(row, col, 'Yes' if subject.is_combined else 'No', default_format)
                col += 1
                ws_detail.write(row, col, subject.classes_conducted, default_format)
                col += 1
                ws_detail.write(row, col, subject.classes_attended, default_format)
                col += 1
                ws_detail.write(row, col, subject.od_count, default_format)
                col += 1
                ws_detail.write(row, col, subject.ml_count, default_format)
                col += 1
                ws_detail.write(row, col, f"{subject.original_percentage:.2f}%", default_format)
                col += 1
                
                # Final percentage with category coloring
                cell_format = category_formats.get(subject.category, default_format)
                ws_detail.write(row, col, f"{subject.final_percentage:.2f}%", cell_format)
                col += 1
                
                ws_detail.write(row, col, 'Yes' if subject.od_ml_adjusted else 'No', default_format)
                col += 1
                ws_detail.write(row, col, subject.category_label, cell_format)
                col += 1
                ws_detail.write(row, col, subject.category.upper(), cell_format)
                
                row += 1
        
        # Auto-fit columns
        ws_detail.set_column('A:A', 12)
        ws_detail.set_column('B:B', 20)
        ws_detail.set_column('C:D', 15)
        ws_detail.set_column('E:N', 12)
        
        # Create summary worksheet
        ws_summary = workbook.add_worksheet('Summary')
        
        # Summary headers
        ws_summary.write(0, 0, 'Category', header_format)
        ws_summary.write(0, 1, 'Student Count', header_format)
        ws_summary.write(0, 2, 'Percentage', header_format)
        
        # Summary data
        total_students = analysis.total_students
        row = 1
        for category_key, category_info in ATTENDANCE_CATEGORIES.items():
            count = analysis.category_distribution.get(category_key, 0)
            percentage = (count / total_students * 100) if total_students > 0 else 0
            
            cell_format = category_formats.get(category_key, default_format)
            ws_summary.write(row, 0, category_info['label'], cell_format)
            ws_summary.write(row, 1, count, cell_format)
            ws_summary.write(row, 2, f"{percentage:.1f}%", cell_format)
            row += 1
        
        # Add total
        ws_summary.write(row, 0, 'TOTAL', header_format)
        ws_summary.write(row, 1, total_students, header_format)
        ws_summary.write(row, 2, '100%', header_format)
        
        ws_summary.set_column('A:C', 15)
        
        workbook.close()
        
        return str(filepath)
    
    def generate_student_wise_dataframe(
        self,
        students: List[StudentAttendance]
    ) -> pd.DataFrame:
        """
        Generate student-wise summary DataFrame
        
        Args:
            students: List of student attendance records
            
        Returns:
            Pandas DataFrame
        """
        data = []
        
        for student in students:
            # Calculate totals
            total_conducted = sum(s.classes_conducted for s in student.subjects)
            total_attended = sum(s.classes_attended for s in student.subjects)
            
            row = {
                'Student ID': student.student_id,
                'Student Name': student.student_name or '',
                'Total Classes': total_conducted,
                'Classes Attended': total_attended,
                'Overall %': f"{student.overall_percentage:.2f}%",
                'Category': student.overall_category.upper(),
                'Status': next(
                    (cat['label'] for key, cat in ATTENDANCE_CATEGORIES.items()
                     if key == student.overall_category),
                    'Unknown'
                )
            }
            data.append(row)
        
        return pd.DataFrame(data)


# Singleton instance
report_generator = ReportGenerator()
