"""
Enhanced Attendance Processing Script with Automated Fuzzy Column Matching

This script automatically matches column headers using fuzzy/semantic matching:
- "OD" / "On Duty" / "OnDuty" → recognized as OD
- "Attended Class" / "No. of hours attended" / "Present" → recognized as attended  
- "ML" / "Medical leave" / "Medical" → recognized as ML
- And so on...
"""
import pandas as pd
import re
from difflib import SequenceMatcher

# ========================================
# FUZZY COLUMN MATCHING CONFIGURATION
# ========================================

# Define flexible matching patterns for each field
COLUMN_PATTERNS = {
    'student_id': [
        'student id', 'roll', 'regno', 'reg no', 'regn', 'regn.', 'regn no',
        'registration', 'student number', 'id'
    ],
    'student_name': [
        'student name', 'name', 'student', 'full name'
    ],
    'subject_code': [
        'subject code', 'course code', 'sub code', 'code', 'subject', 'course'
    ],
    'subject_name': [
        'subject name', 'course name', 'sub name', 'coursename', 'subjectname'
    ],
    'conducted': [
        'conducted', 'total class', 'classes conducted', 'total hours',
        'no. of hours conducted', 'no.of hours conducted', 'hours conducted',
        'classes held', 'total', 'no of classes'
    ],
    'attended': [
        'attended', 'present', 'no. of hours attended', 'no.of hours attended',
        'hours attended', 'classes attended', 'attend', 'no of hours attended',
        'attendance', 'no. of present', 'present class'
    ],
    'od': [
        'od', 'on duty', 'onduty', 'on-duty', 'duty'
    ],
    'ml': [
        'ml', 'medical', 'medical leave', 'medicalleave', 'medical-leave'
    ]
}

def fuzzy_match_score(text1, text2):
    """Calculate fuzzy match score between two strings"""
    text1 = str(text1).lower().strip()
    text2 = str(text2).lower().strip()
    
    # Exact match gets highest score
    if text1 == text2:
        return 1.0
    
    # Contains match gets high score
    if text1 in text2 or text2 in text1:
        return 0.9
    
    # Sequence matching for partial matches
    return SequenceMatcher(None, text1, text2).ratio()

def find_best_column_match(columns, patterns):
    """Find the best matching column for given patterns"""
    best_match = None
    best_score = 0.0
    
    for col in columns:
        col_clean = str(col).lower().strip()
        
        for pattern in patterns:
            score = fuzzy_match_score(col_clean, pattern)
            if score > best_score:
                best_score = score
                best_match = col
    
    # Return match only if score is good enough
    if best_score >= 0.6:  # 60% match threshold
        return best_match, best_score
    return None, 0.0

def auto_detect_columns(df):
    """Automatically detect column mappings using fuzzy matching"""
    mapping = {}
    columns = df.columns.tolist()
    
    print("\n" + "=" * 100)
    print("🔍 AUTOMATIC COLUMN DETECTION (Fuzzy Matching)")
    print("=" * 100)
    
    # Find matches for each field
    used_columns = set()
    
    for field, patterns in COLUMN_PATTERNS.items():
        # Only search in unused columns
        available_cols = [c for c in columns if c not in used_columns]
        match, score = find_best_column_match(available_cols, patterns)
        
        if match:
            mapping[field] = match
            used_columns.add(match)
            print(f"  ✅ {field:15} → '{match}' (confidence: {score*100:.0f}%)")
        else:
            print(f"  ❌ {field:15} → Not found")
    
    return mapping

# ========================================
# DATA PROCESSING FUNCTIONS
# ========================================

def extract_base_code(subject_code):
    """Extract base code from subject code (removes T/L suffix)"""
    subject_code = str(subject_code).strip().upper()
    
    # Handle R21/R18 suffixes
    clean_code = subject_code.replace("-R21", "").replace("-R18", "")
    
    if clean_code.endswith('T'):
        # Reconstruct base if it had a suffix
        if "-R" in subject_code:
             suffix = subject_code[subject_code.find("-R"):]
             return clean_code[:-1] + suffix, 'T'
        return clean_code[:-1], 'T'
        
    elif clean_code.endswith('L'):
        if "-R" in subject_code:
             suffix = subject_code[subject_code.find("-R"):]
             return clean_code[:-1] + suffix, 'L'
        return clean_code[:-1], 'L'
    else:
        return subject_code, ''

def calculate_percentage(attended, conducted):
    """Calculate attendance percentage"""
    if conducted == 0:
        return 0.0
    return round((attended / conducted) * 100, 2)

def get_category(percentage):
    """Categorize attendance percentage"""
    if percentage < 65:
        return 'critical', '🔴', 'Critical'
    elif percentage < 75:
        return 'danger', '🟠', 'Not Safe'
    elif percentage < 80:
        return 'border', '🟡', 'Border'
    else:
        return 'safe', '🟢', 'Safe'

# ========================================
# MAIN PROCESSING
# ========================================

def process_excel_file(file_path):
    """Process the attendance Excel file with automatic column detection"""
    
    print("=" * 100)
    print("🚀 AUTOMATED FACULTY PROFORMA SYSTEM - WITH SMART COLUMN MATCHING")
    print("=" * 100)
    print(f"\nFile: {file_path}\n")
    
    # Smart detection: Try different skip rows to find the header
    df = None
    for skiprows in range(0, 25):
        try:
            temp_df = pd.read_excel(file_path, skiprows=skiprows, nrows=10)
            # Look for column headers that match our patterns
            cols_str = ' '.join([str(c).lower() for c in temp_df.columns])
            
            # Check if we found meaningful columns
            if any(keyword in cols_str for keyword in ['student', 'roll', 'regno', 'subject', 'course', 'attend']):
                # Verify it has some data
                if len(temp_df) > 0 and not temp_df.iloc[0].isna().all():
                    df = pd.read_excel(file_path, skiprows=skiprows)
                    print(f"✅ Found data starting at row {skiprows + 1}")
                    break
        except:
            continue
    
    if df is None:
        print("❌ Could not find proper data structure in Excel file")
        return
    
    # Auto-detect columns using fuzzy matching
    column_mapping = auto_detect_columns(df)
    
    # Verify required columns
    required = ['student_id', 'subject_code', 'conducted', 'attended']
    missing = [r for r in required if r not in column_mapping]
    
    if missing:
        print(f"\n⚠️  Missing required columns: {missing}")
        print("\n📋 Available columns in file:")
        for i, col in enumerate(df.columns[:15], 1):
            print(f"  {i:2d}. '{col}'")
        return
    
    print(f"\n✅ All required columns detected!")
    print(f"📊 Total rows in file: {len(df)}")
    
    # Parse records
    print("\n" + "=" * 100)
    print("📖 PARSING ATTENDANCE RECORDS")
    print("=" * 100)
    
    records = []
    for idx, row in df.iterrows():
        try:
            student_id = str(row[column_mapping['student_id']]).strip()
            if not student_id or student_id == 'nan' or len(student_id) < 3:
                continue
            
            subject_code = str(row[column_mapping['subject_code']]).strip()
            if not subject_code or subject_code == 'nan':
                continue
            
            record = {
                'student_id': student_id,
                'student_name': str(row.get(column_mapping.get('student_name'), '')).strip() if column_mapping.get('student_name') else '',
                'subject_code': subject_code,
                'subject_name': str(row.get(column_mapping.get('subject_name'), '')).strip() if column_mapping.get('student_name') else '',
                'conducted': int(float(row[column_mapping['conducted']])) if pd.notna(row[column_mapping['conducted']]) else 0,
                'attended': int(float(row[column_mapping['attended']])) if pd.notna(row[column_mapping['attended']]) else 0,
                'od': int(float(row.get(column_mapping.get('od'), 0))) if column_mapping.get('od') and pd.notna(row.get(column_mapping.get('od'))) else 0,
                'ml': int(float(row.get(column_mapping.get('ml'), 0))) if column_mapping.get('ml') and pd.notna(row.get(column_mapping.get('ml'))) else 0,
            }
            records.append(record)
        except Exception as e:
            continue
    
    print(f"\n✅ Successfully parsed {len(records)} attendance records")
    
    # Group by student and merge T+L subjects
    print("\n" + "=" * 100)
    print("🔀 MERGING THEORY & LAB SUBJECTS")
    print("=" * 100)
    
    student_subjects = {}
    for rec in records:
        student_id = rec['student_id']
        base_code, subject_type = extract_base_code(rec['subject_code'])
        
        if student_id not in student_subjects:
            student_subjects[student_id] = {'name': rec['student_name'], 'subjects': {}}
        
        if base_code not in student_subjects[student_id]['subjects']:
            student_subjects[student_id]['subjects'][base_code] = {
                'records': [],
                'base_code': base_code,
                'subject_name': rec['subject_name']
            }
        
        student_subjects[student_id]['subjects'][base_code]['records'].append(rec)
    
    # Show merging example
    first_student = list(student_subjects.keys())[0]
    print(f"\nExample: Student {first_student}")
    for base_code, subj_data in list(student_subjects[first_student]['subjects'].items())[:3]:
        components = [r['subject_code'] for r in subj_data['records']]
        if len(components) > 1:
            print(f"  🔗 {base_code}: Merged {' + '.join(components)}")
        else:
            print(f"     {base_code}: {components[0]}")
    
    # Calculate attendance with OD/ML adjustments
    print("\n" + "=" * 100)
    print("📊 CALCULATING ATTENDANCE WITH OD/ML ADJUSTMENTS")
    print("=" * 100)
    
    results = []
    category_counts = {'critical': 0, 'danger': 0, 'border': 0, 'safe': 0}
    
    for student_id, student_data in student_subjects.items():
        student_result = {
            'student_id': student_id,
            'student_name': student_data['name'],
            'subjects': [],
            'total_conducted': 0,
            'total_attended': 0,
            'overall_percentage': 0,
            'category': ''
        }
        
        for base_code, subject_data in student_data['subjects'].items():
            records_list = subject_data['records']
            
            # Combine T+L
            total_conducted = sum(r['conducted'] for r in records_list)
            total_attended = sum(r['attended'] for r in records_list)
            total_od = sum(r['od'] for r in records_list)
            total_ml = sum(r['ml'] for r in records_list)
            
            # Calculate original percentage
            original_pct = calculate_percentage(total_attended, total_conducted)
            
            # Apply OD/ML boost if < 75% AND >= 65%
            # Rule: Only apply if original % < 75 AND original % >= 65
            od_ml_adjusted = False
            final_pct = original_pct
            
            if original_pct < 75 and original_pct >= 65 and (total_od + total_ml > 0):
                adjusted_attended = min(total_attended + total_od + total_ml, total_conducted)
                final_pct = calculate_percentage(adjusted_attended, total_conducted)
                od_ml_adjusted = True
            
            category_key, emoji, category_label = get_category(final_pct)
            
            subject_result = {
                'code': base_code,
                'name': subject_data['subject_name'],
                'is_combined': len(records_list) > 1,
                'combined_from': [r['subject_code'] for r in records_list],
                'components': [
                    {
                        'subject_code': r['subject_code'], 
                        'classes_conducted': r['conducted'],
                        'classes_attended': r['attended'],
                        'od_count': r['od'],
                        'ml_count': r['ml'],
                        'percentage': calculate_percentage(r['attended'], r['conducted'])
                    } for r in records_list
                ],
                'conducted': total_conducted,
                'attended': total_attended,
                'od': total_od,
                'ml': total_ml,
                'original_pct': original_pct,
                'final_pct': final_pct,
                'od_ml_adjusted': od_ml_adjusted,
                'category': category_key,
                'emoji': emoji,
                'label': category_label
            }
            
            student_result['subjects'].append(subject_result)
            student_result['total_conducted'] += total_conducted
            student_result['total_attended'] += total_attended
        
        # Calculate overall
        if student_result['total_conducted'] > 0:
            student_result['overall_percentage'] = calculate_percentage(
                student_result['total_attended'],
                student_result['total_conducted']
            )
            cat_key, _, _ = get_category(student_result['overall_percentage'])
            student_result['category'] = cat_key
            category_counts[cat_key] += 1
        
        results.append(student_result)
    
    # Sort by overall percentage (lowest first)
    results.sort(key=lambda x: x['overall_percentage'])
    
    # Display results
    print("\n" + "=" * 100)
    print("📊 SUMMARY STATISTICS")
    print("=" * 100)
    print(f"\n✨ Total Students Analyzed: {len(results)}")
    print(f"\n🔴 Critical (<65%):     {category_counts['critical']:3d} students")
    print(f"🟠 Danger (65-75%):     {category_counts['danger']:3d} students")
    print(f"🟡 Border (75-80%):     {category_counts['border']:3d} students")
    print(f"🟢 Safe (≥80%):         {category_counts['safe']:3d} students")
    
    # Show critical students
    critical = [r for r in results if r['category'] == 'critical']
    if critical:
        print("\n" + "=" * 100)
        print(f"⚠️  CRITICAL STUDENTS - {len(critical)} students below 65% attendance")
        print("=" * 100)
        for i, student in enumerate(critical[:15], 1):
            print(f"\n{i:2d}. {student['student_id']:15} {student['student_name'][:35]:35} Overall: {student['overall_percentage']:5.1f}%")
            for subj in student['subjects']:
                adj_indicator = " ✅OD/ML" if subj['od_ml_adjusted'] else ""
                combined_indicator = " (T+L)" if subj['is_combined'] else ""
                print(f"     {subj['emoji']} {subj['code']:15} {subj['final_pct']:5.1f}%{combined_indicator}{adj_indicator}")
                
                # Show breakdown if combined
                if subj['is_combined']:
                    for comp in subj['components']:
                        od_ml_str = ""
                        if comp['od_count'] > 0 or comp['ml_count'] > 0:
                            od_ml_str = f" [OD:{comp['od_count']} ML:{comp['ml_count']}]"
                        print(f"        └─ {comp['subject_code']:15}: {comp['percentage']}% ({comp['classes_attended']}/{comp['classes_conducted']}){od_ml_str}")
    
    # Show danger students
    danger = [r for r in results if r['category'] == 'danger']
    if danger:
        print("\n" + "=" * 100)
        print(f"🟠 DANGER ZONE - {len(danger)} students between 65-75% attendance")
        print("=" * 100)
        for i, student in enumerate(danger[:10], 1):
             print(f"{i:2d}. {student['student_id']:15} {student['student_name'][:35]:35} Overall: {student['overall_percentage']:5.1f}%")
    
    # Show top performers
    safe = [r for r in results if r['category'] == 'safe']
    if safe:
        print("\n" + "=" * 100)
        print(f"✨ TOP PERFORMERS - {len(safe)} students with ≥80% attendance")
        print("=" * 100)
        for i, student in enumerate(list(reversed(safe))[:5], 1):
            print(f"{i}. {student['student_id']:15} {student['student_name'][:35]:35} Overall: {student['overall_percentage']:5.1f}%")
    
    print("\n" + "=" * 100)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 100)
    print(f"\n💡 The system automatically detected all columns using fuzzy matching!")
    print(f"📤 This data is ready to be uploaded to the web interface for detailed reports.")

if __name__ == "__main__":
    file_path = "C:/Users/Lenovo/Desktop/perfoma/Sem 6 attendace.xlsx"
    process_excel_file(file_path)
