"""
Direct processing script for Sem 6 attendance Excel file
Works without backend dependencies
"""
import pandas as pd
import re

def extract_base_code(subject_code):
    """Extract base code and type from subject code"""
    subject_code = str(subject_code).strip().upper()
    if subject_code.endswith('T'):
        return subject_code[:-1], 'T'
    elif subject_code.endswith('L'):
        return subject_code[:-1], 'L'
    else:
        return subject_code, ''

def calculate_percentage(attended, conducted):
    """Calculate attendance percentage"""
    if conducted == 0:
        return 0.0
    return round((attended / conducted) * 100, 2)

def get_category(percentage):
    """Get category for percentage"""
    if percentage < 65:
        return 'critical', '🔴', 'Critical'
    elif percentage < 75:
        return 'danger', '🟠', 'Not Safe'
    elif percentage < 80:
        return 'border', '🟡', 'Border'
    else:
        return 'safe', '🟢', 'Safe'

def process_excel_file(file_path):
    """Process the Excel file"""
    
    print("=" * 100)
    print("AUTOMATED FACULTY PROFORMA SYSTEM - PROCESSING ATTENDANCE")
    print("=" * 100)
    print(f"\nFile: {file_path}\n")
    
    # Try to read the Excel file with different configurations
    df = None
    for skiprows in range(0, 20):
        try:
            temp_df = pd.read_excel(file_path, skiprows=skiprows)
            # Look for columns that might contain student/subject data
            cols_str = ' '.join([str(c).lower() for c in temp_df.columns])
            if any(keyword in cols_str for keyword in ['student', 'roll', 'subject', 'class', 'attend']):
                df = temp_df
                print(f"✅ Found data starting at row {skiprows + 1}")
                break
        except:
            continue
    
    if df is None:
        print("❌ Could not find proper data structure in Excel file")
        return
    
    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]
    
    print(f"\nColumns found: {list(df.columns[:15])}")
    print(f"\nTotal rows: {len(df)}")
    
    # Display sample data
    print("\n" + "=" * 100)
    print("SAMPLE DATA (First 5 rows)")
    print("=" * 100)
    print(df.head(5).to_string())
    
    # Try to identify columns
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if any(x in col_lower for x in ['student id', 'roll', 'regno', 'reg no']):
            column_mapping['student_id'] = col
        elif 'student name' in col_lower or (col_lower == 'name' and 'student_id' in column_mapping):
            column_mapping['student_name'] = col
        elif 'subject code' in col_lower or 'course code' in col_lower:
            column_mapping['subject_code'] = col
        elif 'subject name' in col_lower or 'course name' in col_lower:
            column_mapping['subject_name'] = col
        elif any(x in col_lower for x in ['total class', 'classes conducted', 'total']):
            if 'subject_code' in column_mapping:  # Only after subject is found
                column_mapping['conducted'] = col
        elif any(x in col_lower for x in ['attend', 'present']):
            if 'conducted' in column_mapping:  # After conducted
                column_mapping['attended'] = col
        elif col_lower in ['od', 'on duty']:
            column_mapping['od'] = col
        elif col_lower in ['ml', 'medical']:
            column_mapping['ml'] = col
    
    print("\n" + "=" * 100)
    print("COLUMN MAPPING DETECTED")
    print("=" * 100)
    for key, val in column_mapping.items():
        print(f"  {key:15} → {val}")
    
    if not all(k in column_mapping for k in ['student_id', 'subject_code', 'conducted', 'attended']):
        print("\n⚠️  Warning: Could not detect all required columns")
        print("    Required: student_id, subject_code, conducted, attended")
        print("\n📋 Please share the column structure of your Excel file so I can adjust the parser.")
        return
    
    # Parse records
    records = []
    for _, row in df.iterrows():
        try:
            student_id = str(row[column_mapping['student_id']]).strip()
            if not student_id or student_id == 'nan':
                continue
                
            record = {
                'student_id': student_id,
                'student_name': str(row.get(column_mapping.get('student_name'), '')).strip() if column_mapping.get('student_name') else '',
                'subject_code': str(row[column_mapping['subject_code']]).strip(),
                'subject_name': str(row.get(column_mapping.get('subject_name'), '')).strip() if column_mapping.get('subject_name') else '',
                'conducted': int(float(row[column_mapping['conducted']])) if pd.notna(row[column_mapping['conducted']]) else 0,
                'attended': int(float(row[column_mapping['attended']])) if pd.notna(row[column_mapping['attended']]) else 0,
                'od': int(float(row.get(column_mapping.get('od'), 0))) if column_mapping.get('od') and pd.notna(row.get(column_mapping.get('od'))) else 0,
                'ml': int(float(row.get(column_mapping.get('ml'), 0))) if column_mapping.get('ml') and pd.notna(row.get(column_mapping.get('ml'))) else 0,
            }
            records.append(record)
        except Exception as e:
            continue
    
    print(f"\n✅ Parsed {len(records)} attendance records")
    
    # Group by student and base subject
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
    
    # Process and calculate
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
            
            # Combine records
            total_conducted = sum(r['conducted'] for r in records_list)
            total_attended = sum(r['attended'] for r in records_list)
            total_od = sum(r['od'] for r in records_list)
            total_ml = sum(r['ml'] for r in records_list)
            
            # Calculate attendance
            original_pct = calculate_percentage(total_attended, total_conducted)
            
            # Apply OD/ML if < 75%
            od_ml_adjusted = False
            final_pct = original_pct
            if original_pct < 75 and (total_od + total_ml > 0):
                adjusted_attended = min(total_attended + total_od + total_ml, total_conducted)
                final_pct = calculate_percentage(adjusted_attended, total_conducted)
                od_ml_adjusted = True
            
            category_key, emoji, category_label = get_category(final_pct)
            
            subject_result = {
                'code': base_code,
                'name': subject_data['subject_name'],
                'is_combined': len(records_list) > 1,
                'components': [r['subject_code'] for r in records_list],
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
    
    # Sort by overall percentage
    results.sort(key=lambda x: x['overall_percentage'])
    
    # Display results
    print("\n" + "=" * 100)
    print("📊 SUMMARY STATISTICS")
    print("=" * 100)
    print(f"\nTotal Students Analyzed: {len(results)}")
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
            print(f"\n{i}. {student['student_id']:15} {student['student_name'][:30]:30} Overall: {student['overall_percentage']:5.1f}%")
            for subj in student['subjects']:
                adj_marker = " ✅OD/ML" if subj['od_ml_adjusted'] else ""
                combined_marker = " (T+L)" if subj['is_combined'] else ""
                print(f"   {subj['emoji']} {subj['code']:10} {subj['final_pct']:5.1f}%{combined_marker}{adj_marker}")
    
    # Show top performers
    safe = [r for r in results if r['category'] == 'safe']
    if safe:
        print("\n" + "=" * 100)
        print(f"✨ TOP PERFORMERS - {len(safe)} students with ≥80% attendance")
        print("=" * 100)
        for i, student in enumerate(list(reversed(safe))[:10], 1):
            print(f"{i}. {student['student_id']:15} {student['student_name'][:30]:30} Overall: {student['overall_percentage']:5.1f}%")
    
    print("\n" + "=" * 100)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 100)
    print(f"\n💡 This data can now be uploaded to the web interface for detailed reports and visualizations!")

if __name__ == "__main__":
    file_path = "C:/Users/Lenovo/Desktop/perfoma/Sem 6 attendace.xlsx"
    process_excel_file(file_path)
