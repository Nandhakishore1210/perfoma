
import sys
import os
from datetime import datetime
import pandas as pd
import re

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.report_generator import report_generator
from app.models.schemas import AttendanceAnalysisResponse, StudentAttendance, SubjectAttendance, SubjectComponent

def create_mock_student(id, name, subjects):
    s_list = []
    for s_code, s_name in subjects:
        sub = SubjectAttendance(
            subject_code=s_code, subject_name=s_name, is_combined=False,
            classes_conducted=100, classes_posted=100, classes_attended=80,
            od_count=0, ml_count=0, percentage=80, adjusted_attended=80, final_percentage=80
        )
        s_list.append(sub)
        
    student = StudentAttendance(
        student_id=id, student_name=name,
        subjects=s_list,
        total_conducted=200, total_attended=160, total_adjusted_attended=0,
        total_od=0, total_ml=0,
        overall_original_percentage=80.0, overall_final_percentage=80.0
    )
    return student

# Student 1: CS101, MA102
s1 = create_mock_student("S1", "Student One", [("CS101", "Computer Science"), ("MA102", "Maths")])
# Student 2: CS101 only
s2 = create_mock_student("S2", "Student Two", [("CS101", "Computer Science")])

analysis = AttendanceAnalysisResponse(
    upload_id="test_sheets_reverify", students=[s1, s2], total_students=2, total_subjects=2,
    category_distribution={}, processed_at=datetime.now()
)

print("Generating Multi-sheet Excel report...")
output_path = report_generator.generate_excel_report(analysis, "test_subject_sheets_reverify.xlsx")

print(f"Report generated at: {output_path}")

# Verify with Pandas
xl = pd.ExcelFile(output_path)
sheet_names = xl.sheet_names

print(f"Sheets Found: {sheet_names}")

# Expect: "Attendance Report" (Consolidated) + "CS101 ..." + "MA102 ..."

# 1. Verify Sheet Count
if len(sheet_names) == 3:
    print("✅ PASS: Correct number of sheets (1 Consolidated + 2 Subjects).")
else:
    print(f"❌ FAIL: Expected 3 sheets, found {len(sheet_names)}")

# 2. Verify Subject Sheet Content (CS101)
# Find sheet starting with CS101
cs_sheet = next((s for s in sheet_names if s.startswith("CS101")), None)
if cs_sheet:
    print(f"Found CS Sheet: {cs_sheet}")
    df_cs = pd.read_excel(output_path, sheet_name=cs_sheet, header=None)
    # Row 4+ should have data.
    # CS101 is taken by both S1 and S2. Expect 2 data rows.
    data_rows = df_cs.iloc[4:]
    print(f"CS101 Data Rows: {len(data_rows)}")
    if len(data_rows) == 2:
        print("✅ PASS: CS101 has 2 students.")
    else:
        print(f"❌ FAIL: CS101 Expected 2 students, got {len(data_rows)}")
else:
    print("❌ FAIL: CS101 Sheet not found.")

# 3. Verify Subject Sheet Content (MA102)
ma_sheet = next((s for s in sheet_names if s.startswith("MA102")), None)
if ma_sheet:
    print(f"Found MA Sheet: {ma_sheet}")
    df_ma = pd.read_excel(output_path, sheet_name=ma_sheet, header=None)
    # MA102 is taken by S1 only. Expect 1 data row.
    data_rows = df_ma.iloc[4:]
    print(f"MA102 Data Rows: {len(data_rows)}")
    if len(data_rows) == 1:
        print("✅ PASS: MA102 has 1 student.")
    else:
        print(f"❌ FAIL: MA102 Expected 1 student, got {len(data_rows)}")
else:
    print("❌ FAIL: MA102 Sheet not found.")
