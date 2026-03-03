import requests
import os
import time
import json

BASE_URL = "http://localhost:8000/api"

def verify_proforma_flow():
    print("1. Uploading test file...")
    file_path = "Sem 6 attendace.xlsx"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Skipping upload test.")
        return

    with open(file_path, "rb") as f:
        files = {"file": f}
        # Use a new upload to ensure clean state
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

    # 3. Get Proforma 1A Students (Subject-wise)
    print("3. Fetching Proforma 1A Rows...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1A")
    if resp.status_code != 200:
        print("Fetch 1A failed:", resp.text)
        return
        
    rows_1a = resp.json()
    print(f"Found {len(rows_1a)} subject entries in 1A (<65%)")
    
    # Check for new fields
    if len(rows_1a) > 0:
        sample = rows_1a[0]
        if "classes_attended" in sample:
            print("SUCCESS: 'classes_attended' field found in API response.")
        else:
            print("FAILURE: 'classes_attended' field MISSING in API response.")

    if not rows_1a:
        print("No entries found in 1A. Cannot test move flow.")
        return

    # Pick a row to move
    row_to_move = rows_1a[0]
    s_id = row_to_move["student_id"]
    sub_code = row_to_move["subject_code"]
    print(f"Selected entry to move: Student {s_id}, Subject {sub_code}")

    # 4. Move to 1B
    print("4. Moving entry to 1B...")
    payload = {
        "upload_id": upload_id,
        "student_id": s_id,
        "subject_code": sub_code,
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
    print("5. Verifying entry appears in 1B list...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1B")
    rows_1b = resp.json()
    found = any(r["student_id"] == s_id and r["subject_code"] == sub_code for r in rows_1b)
    if found:
        print("SUCCESS: Entry found in 1B list.")
    else:
        print("FAILURE: Entry not found in 1B list.")

    # 6. Verify removed from 1A list
    print("6. Verifying entry removed from 1A list...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1A")
    rows_1a_new = resp.json()
    found_in_1a = any(r["student_id"] == s_id and r["subject_code"] == sub_code for r in rows_1a_new)
    if not found_in_1a:
        print("SUCCESS: Entry removed from 1A list.")
    else:
        print("FAILURE: Entry still present in 1A list.")

    # 7. Approve Student
    print("7. Approving entry...")
    resp = requests.post(f"{BASE_URL}/proforma/approve?upload_id={upload_id}&student_id={s_id}&subject_code={sub_code}")
    if resp.status_code == 200:
        print("Approved successfully.")
    else:
        print("Approval failed:", resp.text)

    # 8. Verify Status
    print("8. Verifying status is Approved...")
    resp = requests.get(f"{BASE_URL}/proforma/{upload_id}/1B")
    rows_1b = resp.json()
    entry = next((r for r in rows_1b if r["student_id"] == s_id and r["subject_code"] == sub_code), None)
    entry = next((r for r in rows_1b if r["student_id"] == s_id and r["subject_code"] == sub_code), None)
    if entry and entry["proforma_entry"]["status"] == "Approved":
         print("SUCCESS: Status is Approved.")
    else:
         print(f"FAILURE: Status is {entry['proforma_entry']['status'] if entry else 'Unknown'}")

    # 9. Verify PDF Download
    print("9. Verifying PDF Download...")
    for p_type in ["1A", "1B"]:
        resp = requests.get(f"{BASE_URL}/proforma/download/{upload_id}/{p_type}")
        if resp.status_code == 200 and resp.headers.get("content-type") == "application/pdf":
            print(f"SUCCESS: {p_type} PDF downloaded successfully.")
        else:
            print(f"FAILURE: {p_type} PDF download failed. Status: {resp.status_code}")

if __name__ == "__main__":
    try:
        verify_proforma_flow()
    except Exception as e:
        print(f"Test crashed: {e}")
