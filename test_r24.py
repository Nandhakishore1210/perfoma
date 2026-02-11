import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.subject_merger import SubjectMergerService
from app.models.schemas import AttendanceRecordInput

def test_r24_merging():
    merger = SubjectMergerService()
    
    # Test Data: R24 Style (Code + CodeL)
    # Expected: Merge into "CS101"
    records = [
        # Theory (No T suffix in R24, just the code)
        AttendanceRecordInput(
            student_id="ST001", student_name="Test Student",
            subject_code="CS101", subject_name="Computer Science",
            classes_conducted=10, classes_attended=8
        ),
        # Lab (Has L suffix)
        AttendanceRecordInput(
            student_id="ST001", student_name="Test Student",
            subject_code="CS101L", subject_name="Computer Science Lab",
            classes_conducted=10, classes_attended=9
        ),
        # Unrelated Subject
        AttendanceRecordInput(
            student_id="ST001", student_name="Test Student",
            subject_code="MATH101", subject_name="Math",
            classes_conducted=20, classes_attended=20
        )
    ]
    
    print("\n--- Testing R24 Logic ---")
    merged_r24 = merger.process_all_subjects(records, regulation="R24")
    
    for subj in merged_r24["ST001"]:
        print(f"Subject: {subj.subject_code} | Combined: {subj.is_combined}")
        if subj.is_combined:
            print(f"  Components: {[c.subject_code for c in subj.components]}")
            
    # Verification
    cs101 = next((s for s in merged_r24["ST001"] if s.subject_code == "CS101"), None)
    if cs101 and cs101.is_combined and len(cs101.components) == 2:
        print("\n✅ R24 Logic SUCCESS: CS101 and CS101L merged into CS101")
    else:
        print("\n❌ R24 Logic FAILED")

    print("\n--- Testing U18 Logic (Control) ---")
    # In U18, CS101 (no T) and CS101L might NOT merge if CS101 doesn't end in T?
    # Let's check. My U18 logic expects T or L. If "CS101", extract_base returns "CS101", ""
    # "CS101L", extract_base returns "CS101", "L"
    # So they WOULD merge in U18 too if the base matches!
    # But let's check output.
    merged_u18 = merger.process_all_subjects(records, regulation="U18")
    for subj in merged_u18["ST001"]:
         print(f"Subject: {subj.subject_code} | Combined: {subj.is_combined}")

if __name__ == "__main__":
    test_r24_merging()
