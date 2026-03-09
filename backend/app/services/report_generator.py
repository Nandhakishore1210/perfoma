"""
Report generation service for Excel and PDF outputs
"""
import pandas as pd
from typing import List
from pathlib import Path
from datetime import datetime
import xlsxwriter
from io import BytesIO
import re

from app.models.schemas import StudentAttendance, AttendanceAnalysisResponse
from app.core.rules import ATTENDANCE_CATEGORIES


class ReportGenerator:
    """Service to generate attendance reports in various formats"""
    
    def __init__(self, output_dir: str = None):
        import tempfile
        import os
        
        if output_dir is None:
            output_dir = os.path.join(tempfile.gettempdir(), "perfoma_reports")
            
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_excel_report(
        self,
        analysis: AttendanceAnalysisResponse,
        filename: str = None,
        department: str = None
    ) -> str:
        """
        Generate comprehensive Excel report with formatting
        
        Args:
            analysis: Complete attendance analysis
            filename: Output filename (optional)
            department: If provided, only include students from this department
            
        Returns:
            Path to generated file
        """
        # Filter students by department if specified
        if department and department.lower() != 'all':
            dept_norm = department.strip().lower()
            students_to_report = [
                s for s in analysis.students
                if s.department and dept_norm in s.department.strip().lower()
            ]
        else:
            students_to_report = list(analysis.students)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if department and department.lower() != 'all':
                # Build a safe short dept slug for the filename
                dept_slug = re.sub(r'[^A-Za-z0-9]+', '_', department.strip())[:30]
                filename = f"attendance_report_{dept_slug}_{timestamp}.xlsx"
            else:
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
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        # Format for top-level headers (Theory, Lab, Total)
        group_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2E7D32',  # Darker green for grouping
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        pct_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.00'
        })
        
        # Create worksheet
        ws = workbook.add_worksheet('Attendance Report')
        
        # Set up Title Rows
        ws.merge_range('A1:Q1', 'Kumaraguru College of Technology', title_format)
        ws.merge_range('A2:Q2', 'Attendance Report', title_format)
        
        # Headers Row 1 (Group Headers)
        ws.merge_range('F3:G3', 'Theory', group_header_format)   # Shifted +2
        ws.merge_range('H3:I3', 'Lab', group_header_format)      # Shifted +2
        ws.merge_range('J3:K3', 'Total', group_header_format)    # Shifted +2
        ws.write('L3', '%', group_header_format)                 # Shifted +2
        
        ws.merge_range('M3:N3', 'Theory', group_header_format)   # Shifted +2
        ws.merge_range('O3:P3', 'Lab', group_header_format)      # Shifted +2
        ws.merge_range('Q3:Q4', 'Total %', header_format)        # Shifted +2
        
        # Headers Row 2 (Sub-headers)
        headers = [
            'S.No.', 'Regn. No.', 'Student Name', 
            'Subject Code', 'Subject Name',  # NEW COLUMNS
            'No. of hours posted', 'No. of hours attended',  # Theory
            'No. of hours posted', 'No. of hours attended',  # Lab
            'Total number of hours posted', 'Total number of hours attended', 'Total %',
            'OnDuty', 'Medical leave',       # Theory OD
            'OnDuty', 'Medical leave'        # Lab OD
        ]
        
        for col, text in enumerate(headers):
            # Q3 is Total %, handled by merge above
            # Writing sub-headers to Row 4 (Index 3)
            if col < 16: # Up to P
                ws.write(3, col, text, header_format)
        
        # Data Rows
        row = 4
        s_no = 1
        
        for student in students_to_report:
            start_row = row
            
            # Aggregate totals for the STUDENT (Grand Total Row)
            student_theory_posted = 0
            student_theory_attended = 0
            student_lab_posted = 0
            student_lab_attended = 0
            
            student_total_adj_theory = 0
            student_total_adj_lab = 0
            
            student_total_od = 0 # Just for display if needed, though split columns exist
            student_total_ml = 0
            
            # Collect Subject Data first to know count? 
            # Actually we can just write rows and merge later or use write_merge if we know count.
            # Let's iterate and write subject rows first.
            
            # We need to process subjects to calculate row data AND accumulate student totals.
            
            for subject in student.subjects:
                # Initialize Subject Row Data
                subj_theory_posted = 0
                subj_theory_attended = 0
                subj_theory_od = 0
                subj_theory_ml = 0
                
                subj_lab_posted = 0
                subj_lab_attended = 0
                subj_lab_od = 0
                subj_lab_ml = 0
                
                subj_adj_theory = 0
                subj_adj_lab = 0
                
                # Subject Details
                subj_code_display = subject.subject_code
                subj_name_display = subject.subject_name
                
                components = subject.components if (subject.is_combined and subject.components) else [subject]
                
                # 1. Sum Raw Stats across components
                total_att_all = 0
                total_den_all = 0
                total_od_all = 0
                total_ml_all = 0

                for comp in components:
                    # Determine type for display columns
                    sub_code = comp.subject_code.upper()
                    is_lab_proj = bool(re.search(r'\d[LJ](-|$)', sub_code)) or sub_code.endswith('L') or sub_code.endswith('J')
                    
                    denom = comp.classes_posted if (comp.classes_posted and comp.classes_posted > 0) else comp.classes_conducted
                    attended = comp.classes_attended
                    od = comp.od_count or 0
                    ml = comp.ml_count or 0
                    
                    # Add to totals
                    total_att_all += attended
                    total_den_all += denom
                    total_od_all += od
                    total_ml_all += ml
                    
                    if is_lab_proj:
                        subj_lab_posted += denom
                        subj_lab_attended += attended
                        subj_lab_od += od
                        subj_lab_ml += ml
                    else:
                        subj_theory_posted += denom
                        subj_theory_attended += attended
                        subj_theory_od += od
                        subj_theory_ml += ml

                # 2. Calculate OVERALL Adjusted Attendance (Unified Logic)
                combined_pct = (total_att_all / total_den_all * 100) if total_den_all > 0 else 0.0
                min_threshold = 65.0
                is_eligible = combined_pct >= min_threshold and (total_od_all > 0 or total_ml_all > 0)
                
                subj_final_numerator = total_att_all
                if is_eligible:
                    # Sum everything and cap at Total Posted
                    raw_total_adj = total_att_all + total_od_all + total_ml_all
                    subj_final_numerator = min(raw_total_adj, total_den_all)
                
                # 3. Assign to "Theory Adjusted" slot for calculating Student Total (or split it, but total matters)
                # We put the entire adjusted val into 'theory' slot to ensure it gets summed into grand total correctly.
                # The individual 'adjusted' values are not displayed in columns, just used for sums.
                subj_adj_theory = subj_final_numerator 
                subj_adj_lab = 0

                # Add to Student Grand Totals
                student_theory_posted += subj_theory_posted
                student_theory_attended += subj_theory_attended
                student_lab_posted += subj_lab_posted
                student_lab_attended += subj_lab_attended
                
                student_total_adj_theory += subj_adj_theory
                student_total_adj_lab += subj_adj_lab
                
                # Write Subject Row
                # Cols A,B,C are merged later.
                
                ws.write(row, 3, subj_code_display, cell_format)
                ws.write(row, 4, subj_name_display, cell_format)
                
                ws.write(row, 5, subj_theory_posted, cell_format)
                ws.write(row, 6, subj_theory_attended, cell_format)
                
                ws.write(row, 7, subj_lab_posted, cell_format)
                ws.write(row, 8, subj_lab_attended, cell_format)
                
                # Subject Row Total
                subj_total_posted = subj_theory_posted + subj_lab_posted
                subj_total_attended = subj_theory_attended + subj_lab_attended
                subj_total_pct_int = 0
                if subj_total_posted > 0:
                    subj_total_pct_int = int((subj_total_attended / subj_total_posted) * 100)
                
                ws.write(row, 9, subj_total_posted, cell_format)
                ws.write(row, 10, subj_total_attended, cell_format)
                ws.write(row, 11, subj_total_pct_int, cell_format)
                
                ws.write(row, 12, subj_theory_od, cell_format)
                ws.write(row, 13, subj_theory_ml, cell_format)
                ws.write(row, 14, subj_lab_od, cell_format)
                ws.write(row, 15, subj_lab_ml, cell_format)
                
                # Subject Final % (Using Verified Logic per Subject Row)
                subj_final_num = subj_adj_theory + subj_adj_lab
                subj_final_pct = 0.0
                if subj_total_posted > 0:
                    subj_final_pct = (subj_final_num / subj_total_posted) * 100
                    
                ws.write(row, 16, subj_final_pct, pct_format)
                
                row += 1
            
            # Write Total Row
            ws.write(row, 3, "TOTAL", group_header_format)
            ws.write(row, 4, "", group_header_format) # Merged with Total? Or Empty.
            
            ws.write(row, 5, student_theory_posted, group_header_format)
            ws.write(row, 6, student_theory_attended, group_header_format)
            
            ws.write(row, 7, student_lab_posted, group_header_format)
            ws.write(row, 8, student_lab_attended, group_header_format)
            
            # Grand Row Total
            grand_total_posted = student_theory_posted + student_lab_posted
            grand_total_attended = student_theory_attended + student_lab_attended
            grand_total_pct_int = 0
            if grand_total_posted > 0:
                grand_total_pct_int = int((grand_total_attended / grand_total_posted) * 100)
                
            ws.write(row, 9, grand_total_posted, group_header_format)
            ws.write(row, 10, grand_total_attended, group_header_format)
            ws.write(row, 11, grand_total_pct_int, group_header_format)
            
            # OD/ML Columns in Total Row? 
            # Sum of ODs
            # Since we iterate subjects, we didn't sum ODs explicitly above, only adjusted.
            # But the row writing loop had them.
            # Let's sum them up quickly or leave blank? Usually Total row has totals.
            # I'll calculate totals for completeness.
            
            grand_theory_od = sum(
                sum(c.od_count or 0 for c in (s.components if s.is_combined else [s]) 
                    if not (bool(re.search(r'\d[LJ](-|$)', c.subject_code.upper())) or c.subject_code.upper().endswith('L') or c.subject_code.upper().endswith('J')))
                for s in student.subjects
            )
            grand_theory_ml = sum(
                sum(c.ml_count or 0 for c in (s.components if s.is_combined else [s]) 
                    if not (bool(re.search(r'\d[LJ](-|$)', c.subject_code.upper())) or c.subject_code.upper().endswith('L') or c.subject_code.upper().endswith('J')))
                for s in student.subjects
            )
            grand_lab_od = sum(
                sum(c.od_count or 0 for c in (s.components if s.is_combined else [s]) 
                    if (bool(re.search(r'\d[LJ](-|$)', c.subject_code.upper())) or c.subject_code.upper().endswith('L') or c.subject_code.upper().endswith('J')))
                for s in student.subjects
            )
            grand_lab_ml = sum(
                sum(c.ml_count or 0 for c in (s.components if s.is_combined else [s]) 
                    if (bool(re.search(r'\d[LJ](-|$)', c.subject_code.upper())) or c.subject_code.upper().endswith('L') or c.subject_code.upper().endswith('J')))
                for s in student.subjects
            )

            ws.write(row, 12, grand_theory_od, group_header_format)
            ws.write(row, 13, grand_theory_ml, group_header_format)
            ws.write(row, 14, grand_lab_od, group_header_format)
            ws.write(row, 15, grand_lab_ml, group_header_format)
            
            # Student Final Semester Percentage (Sum of Adjusted)
            grand_final_num = student_total_adj_theory + student_total_adj_lab
            grand_final_pct = 0.0
            if grand_total_posted > 0:
                grand_final_pct = (grand_final_num / grand_total_posted) * 100
            
            # Write with different format to highlight? group_header_format is good.
            # Use pct_format but with background?
            grand_pct_fmt = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.00', 'bg_color': '#d9d9d9', 'bold': True
            })
            ws.write(row, 16, grand_final_pct, grand_pct_fmt)
            
            # Merge S.No, Regn, Name
            # Rows to merge: start_row to row (inclusive)
            # If start_row == row (only 1 subject + total row? No, strictly row is incremented)
            # Row is now at Total Row. start_row was first subject.
            # Convert 0-index? write/merge uses 0-index.
            
            if row > start_row:
                # Merge from start_row to row-1 (inclusive of current student's block)
                ws.merge_range(start_row, 0, row - 1, 0, s_no, cell_format)
                ws.merge_range(start_row, 1, row - 1, 1, student.student_id, cell_format)
                ws.merge_range(start_row, 2, row - 1, 2, student.student_name or '', cell_format)
            else:
                # Should not happen as we always add Total Row, so at least 1 subj + 1 total = 2 rows
                ws.write(start_row, 0, s_no, cell_format)
                ws.write(start_row, 1, student.student_id, cell_format)
            ws.write(start_row, 2, student.student_name or '', cell_format)

            row += 1
            s_no += 1
            
        # Auto-fit columns for Consolidated Sheet
        ws.set_column('A:A', 5)   # S.No
        ws.set_column('B:B', 12)  # Regn No
        ws.set_column('C:C', 25)  # Name
        ws.set_column('D:E', 15)  # Subject Code/Name
        ws.set_column('F:Q', 12)  # Data columns
        
        # --- GENERATE SUBJECT-WISE SHEETS ---
        # 1. unique subjects map: Code -> Name
        unique_subjects = {}
        for student in students_to_report:
            for sub in student.subjects:
                if sub.subject_code not in unique_subjects:
                    unique_subjects[sub.subject_code] = sub.subject_name
        
        # 2. Iterate and create sheets
        sorted_codes = sorted(unique_subjects.keys())
        
        for sub_code in sorted_codes:
            sub_name = unique_subjects[sub_code]
            # Excel sheet names max 31 chars.
            sheet_name = sub_code[:31].replace(':', '').replace('?', '').replace('*', '').replace('/', '-').replace('\\', '-')
            
            sub_ws = workbook.add_worksheet(sheet_name)
            
            # Formats are reused
            sub_ws.merge_range('A1:O1', 'Kumaraguru College of Technology', title_format)
            sub_ws.merge_range('A2:O2', f'Attendance Report - {sub_code} {sub_name}', title_format)
            
            # Headers Row 1
            sub_ws.merge_range('D3:E3', 'Theory', group_header_format)
            sub_ws.merge_range('F3:G3', 'Lab', group_header_format)
            sub_ws.merge_range('H3:I3', 'Total', group_header_format)
            sub_ws.write('J3', '%', group_header_format)
            
            sub_ws.merge_range('K3:L3', 'Theory', group_header_format)
            sub_ws.merge_range('M3:N3', 'Lab', group_header_format)
            sub_ws.merge_range('O3:O4', 'Total %', header_format)
            
            # Sub Headers Row 2
            sub_ws.write('D4', 'No. of hours posted', header_format)
            sub_ws.write('E4', 'No. of hours attended', header_format)
            sub_ws.write('F4', 'No. of hours posted', header_format)
            sub_ws.write('G4', 'No. of hours attended', header_format)
            sub_ws.write('H4', 'Total number of hours posted', header_format)
            sub_ws.write('I4', 'Total number of hours attended', header_format)
            sub_ws.write('J4', 'Total %', header_format)
            sub_ws.write('K4', 'OnDuty', header_format)
            sub_ws.write('L4', 'Medical leave', header_format)
            sub_ws.write('M4', 'OnDuty', header_format)
            sub_ws.write('N4', 'Medical leave', header_format)
            
            sub_ws.merge_range('A3:A4', 'S.No.', header_format)
            sub_ws.merge_range('B3:B4', 'Regn. No.', header_format)
            sub_ws.merge_range('C3:C4', 'Student Name', header_format)
            
            # Data Rows
            sub_row = 4
            sub_s_no = 1
            
            for student in students_to_report:
                # Find the subject for this student
                target_subject = next((s for s in student.subjects if s.subject_code == sub_code), None)
                
                if target_subject:
                    # Write Row
                    subj_theory_posted = 0
                    subj_theory_attended = 0
                    subj_theory_od = 0
                    subj_theory_ml = 0
                    
                    subj_lab_posted = 0
                    subj_lab_attended = 0
                    subj_lab_od = 0
                    subj_lab_ml = 0
                    
                    subj_adj_theory = 0
                    subj_adj_lab = 0
                    
                    components = target_subject.components if (target_subject.is_combined and target_subject.components) else [target_subject]
                
                    # 1. Sum Raw Stats
                    total_att_all = 0
                    total_den_all = 0
                    total_od_all = 0
                    total_ml_all = 0
                    
                    for comp in components:
                        c_sub_code = comp.subject_code.upper()
                        is_lab_proj = bool(re.search(r'\d[LJ](-|$)', c_sub_code)) or c_sub_code.endswith('L') or c_sub_code.endswith('J')
                        
                        denom = comp.classes_posted if (comp.classes_posted and comp.classes_posted > 0) else comp.classes_conducted
                        attended = comp.classes_attended
                        od = comp.od_count or 0
                        ml = comp.ml_count or 0
                        
                        total_att_all += attended
                        total_den_all += denom
                        total_od_all += od
                        total_ml_all += ml
                        
                        if is_lab_proj:
                            subj_lab_posted += denom
                            subj_lab_attended += attended
                            subj_lab_od += od
                            subj_lab_ml += ml
                        else:
                            subj_theory_posted += denom
                            subj_theory_attended += attended
                            subj_theory_od += od
                            subj_theory_ml += ml
                        
                    # 2. Calculate OVERALL Adjusted Attendance (Unified Logic)
                    combined_pct = (total_att_all / total_den_all * 100) if total_den_all > 0 else 0.0
                    min_threshold = 65.0
                    is_eligible = combined_pct >= min_threshold and (total_od_all > 0 or total_ml_all > 0)
                    
                    subj_final_numerator = total_att_all
                    if is_eligible:
                        raw_total_adj = total_att_all + total_od_all + total_ml_all
                        subj_final_numerator = min(raw_total_adj, total_den_all)
                    
                    subj_adj_theory = subj_final_numerator
                    subj_adj_lab = 0
                            
                    # Calculate Totals
                    subj_total_posted = subj_theory_posted + subj_lab_posted
                    subj_total_attended = subj_theory_attended + subj_lab_attended
                    subj_total_pct_int = 0
                    if subj_total_posted > 0:
                        subj_total_pct_int = int((subj_total_attended / subj_total_posted) * 100)
                    
                    # Final %
                    subj_final_num = subj_adj_theory + subj_adj_lab
                    subj_final_pct = 0.0
                    if subj_total_posted > 0:
                        subj_final_pct = (subj_final_num / subj_total_posted) * 100
                        
                    # Write to Sheet
                    sub_ws.write(sub_row, 0, sub_s_no, cell_format)
                    sub_ws.write(sub_row, 1, student.student_id, cell_format)
                    sub_ws.write(sub_row, 2, student.student_name or '', cell_format)
                    
                    sub_ws.write(sub_row, 3, subj_theory_posted, cell_format)
                    sub_ws.write(sub_row, 4, subj_theory_attended, cell_format)
                    
                    sub_ws.write(sub_row, 5, subj_lab_posted, cell_format)
                    sub_ws.write(sub_row, 6, subj_lab_attended, cell_format)
                    
                    sub_ws.write(sub_row, 7, subj_total_posted, cell_format)
                    sub_ws.write(sub_row, 8, subj_total_attended, cell_format)
                    sub_ws.write(sub_row, 9, subj_total_pct_int, cell_format)
                    
                    sub_ws.write(sub_row, 10, subj_theory_od, cell_format)
                    sub_ws.write(sub_row, 11, subj_theory_ml, cell_format)
                    sub_ws.write(sub_row, 12, subj_lab_od, cell_format)
                    sub_ws.write(sub_row, 13, subj_lab_ml, cell_format)
                    
                    sub_ws.write(sub_row, 14, subj_final_pct, pct_format)
                    
                    sub_row += 1
                    sub_s_no += 1
            
            # Autofit
            sub_ws.set_column('A:A', 5)
            sub_ws.set_column('B:B', 12)
            sub_ws.set_column('C:C', 25)
            sub_ws.set_column('D:O', 12)
        
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
            # Aggregate data for dataframe
            theory_posted = 0
            theory_attended = 0
            theory_od = 0
            theory_ml = 0
            
            lab_posted = 0
            lab_attended = 0
            lab_od = 0
            lab_ml = 0
            
            # Adjusted totals (Subject-wise logic)
            total_adjusted_theory = 0
            total_adjusted_lab = 0
            
            for subject in student.subjects:
                components = subject.components if (subject.is_combined and subject.components) else [subject]
                
                # 1. Sum Raw Stats
                total_att_all = 0
                total_den_all = 0
                total_od_all = 0
                total_ml_all = 0
                
                for comp in components:
                    sub_code = comp.subject_code.upper()
                    is_lab_proj = bool(re.search(r'\d[LJ](-|$)', sub_code)) or sub_code.endswith('L') or sub_code.endswith('J')
                    denom = comp.classes_posted if (comp.classes_posted and comp.classes_posted > 0) else comp.classes_conducted
                    attended = comp.classes_attended
                    od = comp.od_count or 0
                    ml = comp.ml_count or 0
                    
                    total_att_all += attended
                    total_den_all += denom
                    total_od_all += od
                    total_ml_all += ml
                    
                    if is_lab_proj:
                        lab_posted += denom
                        lab_attended += attended
                        lab_od += od
                        lab_ml += ml
                    else:
                        theory_posted += denom
                        theory_attended += attended
                        theory_od += od
                        theory_ml += ml
                        
                # 2. Calculate OVERALL Adjusted Attendance (Unified Logic)
                combined_pct = (total_att_all / total_den_all * 100) if total_den_all > 0 else 0.0
                min_threshold = 65.0
                is_eligible = combined_pct >= min_threshold and (total_od_all > 0 or total_ml_all > 0)
                
                subj_final_numerator = total_att_all
                if is_eligible:
                    raw_total_adj = total_att_all + total_od_all + total_ml_all
                    subj_final_numerator = min(raw_total_adj, total_den_all)
                
                # Add to student total (Accumulate into theory slot for simplicity)
                total_adjusted_theory += subj_final_numerator

            # Original Percentage (Theory + Lab attended / Total Posted)
            total_posted = theory_posted + lab_posted
            total_attended = theory_attended + lab_attended
            
            total_pct_str = "0.00%"
            if total_posted > 0:
                total_pct_str = f"{(total_attended / total_posted) * 100:.2f}%"
            
            # Final Percentage (Subject-wise Logic)
            final_numerator = total_adjusted_theory + total_adjusted_lab
            
            final_pct_str = "0.00%"
            if total_posted > 0:
                final_pct_str = f"{(final_numerator / total_posted) * 100:.2f}%"

            row = {
                'Student ID': student.student_id,
                'Student Name': student.student_name or '',
                'Theory Posted': theory_posted,
                'Theory Attended': theory_attended,
                'Lab Posted': lab_posted,
                'Lab Attended': lab_attended,
                'Total Posted': theory_posted + lab_posted,
                'Total Attended': theory_attended + lab_attended,
                'Total OD': student.total_od,
                'Total ML': student.total_ml,
                'Original Overall %': total_pct_str,
                'Final Overall %': final_pct_str,
                'Category': student.overall_category.upper(),
                'Status': next(
                    (cat['label'] for key, cat in ATTENDANCE_CATEGORIES.items()
                     if key == student.overall_category),
                    'Unknown'
                )
            }
            data.append(row)
        
        return pd.DataFrame(data)

    def generate_pdf_report(
        self,
        analysis: AttendanceAnalysisResponse,
        filename: str = None,
        department: str = None
    ) -> str:
        """
        Generate PDF report using ReportLab
        
        Args:
            analysis: Complete attendance analysis
            filename: Output filename (optional)
            department: If provided, only include students from this department
            
        Returns:
            Path to generated file
        """
        # Filter students by department if specified
        if department and department.lower() != 'all':
            dept_norm = department.strip().lower()
            students_to_report = [
                s for s in analysis.students
                if s.department and dept_norm in s.department.strip().lower()
            ]
        else:
            students_to_report = list(analysis.students)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if department and department.lower() != 'all':
                dept_slug = re.sub(r'[^A-Za-z0-9]+', '_', department.strip())[:30]
                filename = f"attendance_report_{dept_slug}_{timestamp}.pdf"
            else:
                filename = f"attendance_report_{timestamp}.pdf"
            
        filepath = self.output_dir / filename
        
        # Create Document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1  # Center
        )
        elements.append(Paragraph("Kumaraguru College of Technology", title_style))
        elements.append(Paragraph("Attendance Report", title_style))
        elements.append(Spacer(1, 20))
        
        # Table Data
        # Headers
        data = [[
            "S.No", "ID", "Student Name", 
            "Theory\n(P/A)", "Lab\n(P/A)", "Total\n(P/A)", 
            "OD", "ML", "Final %", "Status"
        ]]
        
        # Rows
        for idx, student in enumerate(students_to_report, 1):
            # Calculate aggregations (reuse logic from dataframe generation or just loop)
            # We need Subject Totals for display? Or Student Grand Totals?
            # Consolidated report shows Student Grand Totals.
            
            # Re-calculate totals matching the logic in generate_student_wise_dataframe
            # or simplify by summing subject components again? 
            # Ideally we should refrain from duplicating logic 3 times.
            # But for now, we copy the "Student Grand Total" logic.
            
            theory_posted = 0
            theory_attended = 0
            lab_posted = 0
            lab_attended = 0
            total_od = 0
            total_ml = 0
            total_adjusted_theory = 0
            total_adjusted_lab = 0
            
            # Logic from generate_student_wise_dataframe
            for subject in student.subjects:
                components = subject.components if (subject.is_combined and subject.components) else [subject]
                
                # 1. Sum Raw Stats
                total_att_all = 0
                total_den_all = 0
                total_od_all = 0
                total_ml_all = 0
                
                for comp in components:
                    sub_code = comp.subject_code.upper()
                    is_lab_proj = bool(re.search(r'\d[LJ](-|$)', sub_code)) or sub_code.endswith('L') or sub_code.endswith('J')
                    denom = comp.classes_posted if (comp.classes_posted and comp.classes_posted > 0) else comp.classes_conducted
                    attended = comp.classes_attended
                    od = comp.od_count or 0
                    ml = comp.ml_count or 0
                    
                    total_att_all += attended
                    total_den_all += denom
                    total_od_all += od
                    total_ml_all += ml
                    
                    if is_lab_proj:
                        lab_posted += denom
                        lab_attended += attended
                    else:
                        theory_posted += denom
                        theory_attended += attended
                
                total_od += total_od_all
                total_ml += total_ml_all

                # 2. Calculate OVERALL Adjusted Attendance (Unified Logic)
                combined_pct = (total_att_all / total_den_all * 100) if total_den_all > 0 else 0.0
                min_threshold = 65.0
                is_eligible = combined_pct >= min_threshold and (total_od_all > 0 or total_ml_all > 0)
                
                subj_final_numerator = total_att_all
                if is_eligible:
                    raw_total_adj = total_att_all + total_od_all + total_ml_all
                    subj_final_numerator = min(raw_total_adj, total_den_all)
                
                total_adjusted_theory += subj_final_numerator

            total_posted = theory_posted + lab_posted
            total_attended = theory_attended + lab_attended
            
            final_numerator = total_adjusted_theory + total_adjusted_lab
            final_pct = 0.0
            if total_posted > 0:
                final_pct = (final_numerator / total_posted) * 100
                
            # Status Label
            category_label = next(
                (cat['label'] for key, cat in ATTENDANCE_CATEGORIES.items() if key == student.overall_category),
                'Unknown'
            )

            row = [
                str(idx),
                student.student_id,
                student.student_name or "",
                f"{theory_posted}/{theory_attended}",
                f"{lab_posted}/{lab_attended}",
                f"{total_posted}/{total_attended}",
                str(total_od),
                str(total_ml),
                f"{final_pct:.2f}%",
                category_label
            ]
            data.append(row)
            
        # Create Table
        # Column Widths
        col_widths = [40, 80, 150, 70, 70, 70, 40, 40, 60, 100]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Table Style
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ])
        
        # Apply conditional formatting for status? 
        # Hard with TableStyle unless we map rows.
        # Just creating basic table for now.
        
        t.setStyle(style)
        elements.append(t)
        
        # Build
        doc.build(elements)
        return str(filepath)


# Singleton instance
report_generator = ReportGenerator()
