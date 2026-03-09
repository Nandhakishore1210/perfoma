from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import shutil
import pandas as pd
from datetime import datetime
import uuid
import traceback
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models import sql_models, schemas
from app.core.config import settings
from app.utils.pdf_generator import ProformaPDFGenerator

router = APIRouter()

@router.get("/proforma/{upload_id}/{proforma_type}", response_model=List[schemas.ProformaReportRow])
def get_proforma_students(
    upload_id: str, 
    proforma_type: str,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get subject-wise entries eligible for Proforma 1A or 1B.
    Merges analysis data with saved proforma state.
    Optionally filter by department (case-insensitive partial match).
    """
    # 1. Get Analysis
    analysis = db.query(sql_models.Analysis).filter(sql_models.Analysis.upload_id == upload_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # 2. Get Saved Proforma Entries
    saved_entries = db.query(sql_models.ProformaEntry).filter(
        sql_models.ProformaEntry.upload_id == upload_id
    ).all()
    
    # Map (student_id, subject_code) -> entry
    entries_map = {(entry.student_id, entry.subject_code): entry for entry in saved_entries}
    
    students_data = analysis.result_data.get("students", [])
    report_rows = []
    
    # Normalise department filter for comparison
    dept_filter = department.strip().lower() if department else None
    
    for s_data in students_data:
        student_id = s_data.get("student_id")
        student_name = s_data.get("student_name")
        student_dept = s_data.get("department") or ""
        subjects = s_data.get("subjects", [])
        
        # Apply department filter — use case-insensitive partial match so
        # "B.TECH-INFORMATION TECHNOLOGY" matches "Department of Information Technology" etc.
        if dept_filter:
            dept_norm = student_dept.lower()
            # Try both directions of substring matching
            if dept_filter not in dept_norm and dept_norm not in dept_filter:
                # Also try keyword overlap (split and check if any word matches)
                filter_words = set(dept_filter.replace('-', ' ').split())
                dept_words = set(dept_norm.replace('-', ' ').split())
                common = filter_words & dept_words
                # Exclude very short common words (like "of", "and", etc.)
                meaningful_common = {w for w in common if len(w) > 2}
                if not meaningful_common:
                    continue  # Skip this student — doesn't match department filter
        
        for subject in subjects:
            final_pct = subject.get("final_percentage", 0.0)
            subject_code = subject.get("subject_code")
            subject_name = subject.get("subject_name")
            
            # Lookup entry
            entry_key = (student_id, subject_code)
            entry = entries_map.get(entry_key)
            current_type = entry.proforma_type if entry else None
            
            # Logic for inclusion
            include = False
            
            if proforma_type == "1A":
                # Include if < 65% AND NOT moved to 1B
                if final_pct < 65.0:
                    if current_type != "1B":
                        include = True
            
            elif proforma_type == "1B":
                # Include if 65% <= pct < 75%
                # OR if (< 65% AND moved to 1B)
                if 65.0 <= final_pct < 75.0:
                    include = True
                elif final_pct < 65.0 and current_type == "1B":
                    include = True
            
            if include:
                row = {
                    "student_id": student_id,
                    "student_name": student_name,
                    "department": student_dept,
                    "subject_code": subject_code,
                    "subject_name": subject_name,
                    "attendance_percentage": final_pct,
                    "classes_attended": subject.get("classes_attended", 0),
                    "classes_conducted": subject.get("classes_conducted", 0),
                    "classes_posted": subject.get("classes_posted", 0),
                    "proforma_entry": entry if entry else None
                }
                report_rows.append(row)
            
    return report_rows


@router.post("/proforma/entry", response_model=schemas.ProformaEntryResponse)
def create_or_update_entry(
    entry_in: schemas.ProformaEntryCreate,
    db: Session = Depends(get_db)
):
    entry = db.query(sql_models.ProformaEntry).filter(
        sql_models.ProformaEntry.upload_id == entry_in.upload_id,
        sql_models.ProformaEntry.student_id == entry_in.student_id,
        sql_models.ProformaEntry.subject_code == entry_in.subject_code
    ).first()
    
    if entry:
        # Update existing
        entry.proforma_type = entry_in.proforma_type
        if entry_in.reason is not None:
            entry.reason = entry_in.reason
        if entry_in.status is not None:
            entry.status = entry_in.status
        entry.updated_at = datetime.utcnow()
    else:
        # Create new
        entry = sql_models.ProformaEntry(
            upload_id=entry_in.upload_id,
            student_id=entry_in.student_id,
            subject_code=entry_in.subject_code,
            proforma_type=entry_in.proforma_type,
            reason=entry_in.reason,
            status=entry_in.status
        )
        db.add(entry)
    
    db.commit()
    db.refresh(entry)
    return entry

@router.post("/proforma/upload_proof")
async def upload_proof(
    upload_id: str = Form(...),
    student_id: str = Form(...),
    subject_code: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Ensure directory exists
    upload_dir = os.path.join("uploads", "proofs", upload_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{student_id}_{subject_code}_proof_{uuid.uuid4().hex[:8]}{file_ext}"
    safe_filename = safe_filename.replace("/", "_").replace("\\", "_") # Sanitize
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update DB entry
    entry = db.query(sql_models.ProformaEntry).filter(
        sql_models.ProformaEntry.upload_id == upload_id,
        sql_models.ProformaEntry.student_id == student_id,
        sql_models.ProformaEntry.subject_code == subject_code
    ).first()
    
    if not entry:
        # Create if not exists (should theoretically exist if in 1B list, but safe to create)
        entry = sql_models.ProformaEntry(
            upload_id=upload_id,
            student_id=student_id,
            subject_code=subject_code,
            proforma_type="1B", # Implied
            proof_path=file_path
        )
        db.add(entry)
    else:
        entry.proof_path = file_path
        
    db.commit()
    return {"filename": safe_filename, "path": file_path}

@router.post("/proforma/approve")
def approve_student(
    upload_id: str,
    student_id: str,
    subject_code: str,
    db: Session = Depends(get_db)
):
    entry = db.query(sql_models.ProformaEntry).filter(
        sql_models.ProformaEntry.upload_id == upload_id,
        sql_models.ProformaEntry.student_id == student_id,
        sql_models.ProformaEntry.subject_code == subject_code
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    entry.status = "Approved"
    entry.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success"}

@router.get("/proforma/download/{upload_id}/{proforma_type}", response_model=schemas.ReportResponse)
async def download_proforma_report(
    upload_id: str, 
    proforma_type: str,
    format: str = "pdf",
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 1. Get Analysis
    analysis = db.query(sql_models.Analysis).filter(sql_models.Analysis.upload_id == upload_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # 2. Get Saved Proforma Entries
    saved_entries = db.query(sql_models.ProformaEntry).filter(
        sql_models.ProformaEntry.upload_id == upload_id
    ).all()
    entries_map = {(entry.student_id, entry.subject_code): entry for entry in saved_entries}
    
    students_data = analysis.result_data.get("students", [])
    report_data = []

    # Normalise department filter (same logic as get_proforma_students)
    dept_filter = department.strip().lower() if department else None
    
    for s_data in students_data:
        student_id = s_data.get("student_id")
        student_name = s_data.get("student_name")
        subjects = s_data.get("subjects", [])
        student_dept = s_data.get("department") or ""

        # Apply department filter
        if dept_filter:
            dept_norm = student_dept.lower()
            if dept_filter not in dept_norm and dept_norm not in dept_filter:
                filter_words = set(dept_filter.replace('-', ' ').split())
                dept_words = set(dept_norm.replace('-', ' ').split())
                meaningful_common = {w for w in (filter_words & dept_words) if len(w) > 2}
                if not meaningful_common:
                    continue
        
        for subject in subjects:
            final_pct = subject.get("final_percentage", 0.0)
            subject_code = subject.get("subject_code")
            subject_name = subject.get("subject_name")
            
            entry_key = (student_id, subject_code)
            entry = entries_map.get(entry_key)
            current_type = entry.proforma_type if entry else None
            
            include = False
            if proforma_type == "1A":
                if final_pct < 65.0:
                    if current_type != "1B":
                        include = True
            elif proforma_type == "1B":
                if 65.0 <= final_pct < 75.0:
                    include = True
                elif final_pct < 65.0 and current_type == "1B":
                    include = True
            
            if include:
                entry_dict = {
                    "reason": entry.reason if entry else "",
                    "status": entry.status if entry else "Pending"
                }
                
                row = {
                    "student_id": student_id,
                    "student_name": student_name,
                    "department": s_data.get("department"),
                    "subject_code": subject_code,
                    "subject_name": subject_name,
                    "attendance_percentage": final_pct,
                    "classes_attended": subject.get("classes_attended", 0),
                    "classes_conducted": subject.get("classes_conducted", 0),
                    "classes_posted": subject.get("classes_posted", 0),
                    "proforma_entry": entry_dict
                }
                report_data.append(row)

    import tempfile
    temp_dir = os.path.join(tempfile.gettempdir(), "perfoma_reports")
    os.makedirs(temp_dir, exist_ok=True)

    # Build dept slug for filename
    dept_slug = ""
    if department and department.lower() != 'all':
        import re as _re
        dept_slug = "_" + _re.sub(r'[^A-Za-z0-9]+', '_', department.strip())[:20]
    
    if format.lower() == "excel":
        try:
            # Flatten data for Excel
            excel_data = []
            for idx, item in enumerate(report_data, 1):
                excel_data.append({
                    "S.No": idx,
                    "Register No.": item["student_id"],
                    "Student Name": item["student_name"],
                    "Subject Code": item["subject_code"],
                    "Subject Name": item["subject_name"],
                    "Classes Posted": item["classes_posted"],
                    "Classes Attended": item["classes_attended"],
                    "Attendance %": f"{item['attendance_percentage']:.2f}",
                    "Reason": item["proforma_entry"]["reason"],
                    "Status": item["proforma_entry"]["status"]
                })
                
            df = pd.DataFrame(excel_data)
            
            filename = f"Proforma_{proforma_type}{dept_slug}_{upload_id[:8]}.xlsx"
            filepath = os.path.join(temp_dir, filename)
            
            # Write to Excel
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name=f'Proforma_{proforma_type}', index=False)
                
                # Auto-adjust columns
                worksheet = writer.sheets[f'Proforma_{proforma_type}']
                for idx, col in enumerate(df.columns):
                    series = df[col]
                    max_val_len = series.astype(str).map(len).max() if not series.empty else 0
                    max_len = max(max_val_len, len(str(col))) + 2
                    worksheet.set_column(idx, idx, max_len)
            
            return schemas.ReportResponse(
                filename=filename,
                file_path=filepath,
                format="excel"
            )
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"Excel generation failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Excel generation failed: {str(e)}")
    else:
        try:
            # Generate PDF
            generator = ProformaPDFGenerator()
            if proforma_type == "1A":
                pdf_buffer = generator.generate_proforma_1a(report_data)
                filename = f"Proforma_1A{dept_slug}_{upload_id[:8]}.pdf"
            else:
                pdf_buffer = generator.generate_proforma_1b(report_data)
                filename = f"Proforma_1B{dept_slug}_{upload_id[:8]}.pdf"
            
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "wb") as f:
                f.write(pdf_buffer.getvalue())
                
            return schemas.ReportResponse(
                filename=filename,
                file_path=filepath,
                format="pdf"
            )
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"PDF generation failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
