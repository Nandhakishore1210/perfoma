import sys
import os
# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.attendance_calculator import attendance_calculator
from app.models.schemas import SubjectAttendance, SubjectComponent

def verify_logic():
    print("Verifying OD/ML Combined Logic...")
    
    # Create a mock combined subject
    # Scenario:
    # Theory: 10/20 (50%) - Not eligible individually (if <65%)
    # Lab:    18/20 (90%) - Eligible individually
    # Combined: 28/40 (70%) - Eligible (>65%)
    # OD: 5 hours total (3 in theory, 2 in lab)
    
    comp_theory = SubjectComponent(
        subject_code="TEST101T",
        subject_name="Test Theory",
        classes_conducted=20,
        classes_posted=20,
        classes_attended=10, # 50%
        od_count=3,
        ml_count=0
    )
    
    comp_lab = SubjectComponent(
        subject_code="TEST101L",
        subject_name="Test Lab",
        classes_conducted=20,
        classes_posted=20,
        classes_attended=18, # 90%
        od_count=2,
        ml_count=0
    )
    
    subject = SubjectAttendance(
        subject_code="TEST101",
        subject_name="Test Subject Combined",
        is_combined=True,
        components=[comp_theory, comp_lab],
        classes_conducted=40,
        classes_posted=40,
        classes_attended=28
    )
    
    # Run Calculator
    processed = attendance_calculator.apply_od_ml_adjustment(subject)
    
    # Check Results
    print(f"\nSubject: {processed.subject_name}")
    print(f"Original Attended: {subject.classes_attended}")
    print(f"Adjusted Attended: {processed.adjusted_attended}")
    print(f"Original %: {processed.original_percentage}%")
    print(f"Final %: {processed.final_percentage}%")
    
    # Expected Logic:
    # Combined % = 70% >= 65% (Eligible)
    # Total Attended = 28
    # Total OD = 5
    # Adjusted = min(28 + 5, 40) = 33
    
    expected_adj = 33
    if processed.adjusted_attended == expected_adj:
        print("[SUCCESS] Adjusted Attendance matches expected Overall Logic (33).")
    else:
        print(f"[FAILURE] Expected {expected_adj}, got {processed.adjusted_attended}.")
        
    # Check if per-component logic would have given less
    # Theory: 10 (Ineligible) -> 10
    # Lab: 18+2=20 (Capped) -> 20
    # Sum = 30
    if processed.adjusted_attended > 30:
        print("[INFO] New logic yields higher attendance than component-sum logic (33 > 30).")

if __name__ == "__main__":
    try:
        verify_logic()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
