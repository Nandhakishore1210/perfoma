import requests
import os
import time

BASE_URL = "http://localhost:8000/api"

# We need an existing upload_id. 
# You should check the uploads folder or DB, or upload a file first.
# For this script to be standalone, we'd need to upload a file. 
# Let's assume the user has run the app and we can find a recent upload or we just upload one now.

def verify_proforma_flow():
    print("1. Uploading test file...")
    # Create a dummy excel file if needed or use existing one
    file_path = "Sem 6 attendace.xlsx" # Assuming this exists from context
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. functionality. Skipping upload test.")
        return

    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(f"{BASE_URL}/upload", files=files)
        if resp.status_code != 200:
            print("Upload failed:", resp.text)
            return
        upload_data = resp.json()
        upload_id = upload_data["upload_id"]
        print(f"Uploaded successfully. ID: {upload_id}")

    # Trigger Analysis
    print("2. Triggering Analysis...")
    resp = requests.post(f"{BASE_URL}/analyze/{upload_id}?regulation=U18")
    if resp.status_code != 200:
        print("Analysis failed:", resp.text)
        return
    print("Analysis complete.")

    # 3. Get Proforma 1A Students
    print("3. Fetching Proforma 1A Students...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1A")
    students_1a = resp.json()
    print(f"Found {len(students_1a)} students in 1A (<65%)")
    
    if not students_1a:
        print("No students found in 1A. Cannot test move flow.")
        return

    student_to_move = students_1a[0]
    s_id = student_to_move["student_id"]
    print(f"Selected student to move: {s_id}")

    # 4. Move to 1B
    print("4. Moving student to 1B...")
    payload = {
        "upload_id": upload_id,
        "student_id": s_id,
        "proforma_type": "1B",
        "reason": "Medical Reason",
        "status": "Pending"
    }
    resp = requests.post(f"{BASE_URL}/proforma/entry", json=payload)
    if resp.status_code != 200:
        print("Move failed:", resp.text)
        return
    print("Moved successfully.")

    # 5. Verify in 1B list
    print("5. Verifying student appears in 1B list...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1B")
    students_1b = resp.json()
    found = any(s["student_id"] == s_id for s in students_1b)
    if found:
        print("SUCCESS: Student found in 1B list.")
    else:
        print("FAILURE: Student not found in 1B list.")

    # 6. Verify removed from 1A list
    print("6. Verifying student removed from 1A list...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1A")
    students_1a_new = resp.json()
    found_in_1a = any(s["student_id"] == s_id for s in students_1a_new)
    if not found_in_1a:
        print("SUCCESS: Student removed from 1A list.")
    else:
        print("FAILURE: Student still present in 1A list.")

    # 7. Approve Student
    print("7. Approving student...")
    resp = requests.post(f"{BASE_URL}/proforma/approve?upload_id={upload_id}&student_id={s_id}")
    if resp.status_code == 200:
        print("Approved successfully.")
    else:
        print("Approval failed:", resp.text)

    # 8. Verify Status
    print("8. Verifying status is Approved...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1B")
    students_1b = resp.json()
    student = next((s for s in students_1b if s["student_id"] == s_id), None)
    if student and student["proforma_entry"]["status"] == "Approved":
         print("SUCCESS: Status is Approved.")
    else:
         print(f"FAILURE: Status is {student['proforma_entry']['status'] if student else 'Unknown'}")

if __name__ == "__main__":
    try:
        verify_proforma_flow()
    except Exception as e:
        print(f"Test crashed: {e}")
        print("Make sure the backend is running on port 8000")
