"""
File parsing service for Excel and PDF attendance files with intelligent fuzzy column matching
"""
import pandas as pd
import pdfplumber
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
from difflib import SequenceMatcher
from app.models.schemas import AttendanceRecordInput


class FileParserService:
    """Universal file parser for attendance data with fuzzy column matching"""
    
    def __init__(self):
        self.supported_excel = ['.xlsx', '.xls']
        self.supported_pdf = ['.pdf']
        
        # Enhanced column patterns with more variations
        self.column_patterns = {
            'student_id': [
                'student id', 'roll', 'roll no', 'roll number', 'rollno', 'regno', 
                'reg no', 'regn', 'regn.', 'regn no', 'registration', 
                'student number', 'id', 'student_id', 'roll_no'
            ],
            'student_name': [
                'student name', 'name', 'student', 'full name', 
                'student_name', 'studentname'
            ],
            'subject_code': [
                'subject code', 'course code', 'sub code', 'code', 'subject', 
                'course', 'subject_code', 'subjectcode', 'coursecode'
            ],
            'subject_name': [
                'subject name', 'course name', 'sub name', 'coursename', 
                'subjectname', 'subject_name', 'course_name'
            ],
            'classes_conducted': [
                'conducted', 'total class', 'classes conducted', 'total hours',
                'no. of hours conducted', 'no.of hours conducted', 'hours conducted',
                'classes held', 'total', 'no of classes', 'classes_conducted',
                'total_classes', 'no of hours', 'hours held'
            ],
            'classes_attended': [
                'attended', 'present', 'no. of hours attended', 'no.of hours attended',
                'hours attended', 'classes attended', 'attend', 'no of hours attended',
                'attendance', 'no. of present', 'present class', 'classes_attended',
                'no of attended'
            ],
            'od_count': [
                'od', 'on duty', 'onduty', 'on-duty', 'duty', 'od count', 
                'od_count', 'on_duty'
            ],
'ml_count': [
                'ml', 'medical', 'medical leave', 'medicalleave', 'medical-leave',
                'ml count', 'ml_count', 'medical_leave'
            ]
        }
    
    def detect_file_type(self, filename: str) -> str:
        """
        Detect file type from filename
        
        Args:
            filename: Name of the file
            
        Returns:
            File type: 'excel', 'pdf', or 'unknown'
        """
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        if extension in self.supported_excel:
            return 'excel'
        elif extension in self.supported_pdf:
            return 'pdf'
        else:
            return 'unknown'
    
    def _fuzzy_match_score(self, text1: str, text2: str) -> float:
        """
        Calculate fuzzy match score between two strings
        
        Args:
            text1: First string
            text2: Second string
            
        Returns:
            Match score between 0.0 and 1.0
        """
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
    
    def _find_best_column_match(self, columns: List[str], patterns: List[str], 
                                 used_columns: set) -> Tuple[Optional[str], float]:
        """
        Find the best matching column for given patterns
        
        Args:
            columns: List of all column names
            patterns: List of patterns to match
            used_columns: Set of columns already mapped
            
        Returns:
            Tuple of (best_match_column, confidence_score)
        """
        best_match = None
        best_score = 0.0
        
        # Only search in unused columns
        available_cols = [c for c in columns if c not in used_columns]
        
        for col in available_cols:
            col_clean = str(col).lower().strip()
            
            for pattern in patterns:
                score = self._fuzzy_match_score(col_clean, pattern)
                if score > best_score:
                    best_score = score
                    best_match = col
        
        # Return match only if score is good enough (60% threshold)
        if best_score >= 0.6:
            return best_match, best_score
        return None, 0.0
    
    def _auto_detect_header_row(self, file_path: str) -> Tuple[pd.DataFrame, int]:
        """
        Automatically detect the row containing column headers
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Tuple of (DataFrame, skiprows count)
        """
        # Try different skip rows to find the header
        for skiprows in range(0, 25):
            try:
                temp_df = pd.read_excel(file_path, skiprows=skiprows, nrows=10)
                # Look for column headers that match our patterns
                cols_str = ' '.join([str(c).lower() for c in temp_df.columns])
                
                # Check if we found meaningful columns
                if any(keyword in cols_str for keyword in 
                       ['student', 'roll', 'regno', 'subject', 'course', 'attend', 'class']):
                    # Verify it has some data
                    if len(temp_df) > 0 and not temp_df.iloc[0].isna().all():
                        df = pd.read_excel(file_path, skiprows=skiprows)
                        return df, skiprows
            except:
                continue
        
        # Fallback: read without skipping
        return pd.read_excel(file_path), 0
    
    def parse_excel(self, file_path: str) -> List[AttendanceRecordInput]:
        """
        Parse Excel file and extract attendance records with automatic header detection
        
        Uses fuzzy matching to automatically detect column names regardless of variations:
        - "Student ID" / "Regn. No." / "Roll No" → student_id
        - "OnDuty" / "On Duty" / "OD" → od
        - "No. of hours attended" / "Attended" → attended
        - And many more variations...
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of AttendanceRecordInput objects
        """
        # Auto-detect header row
        df, skiprows = self._auto_detect_header_row(file_path)
        
        print(f"✅ Auto-detected data starting at row {skiprows + 1}")
        
        # Map flexible column names to standard names using fuzzy matching
        original_columns = df.columns.tolist()
        column_mapping = self._detect_column_mapping_fuzzy(original_columns)
        
        # Rename columns to standard names
        df = df.rename(columns=column_mapping)
        
        # Convert to list of records
        records = []
        for idx, row in df.iterrows():
            try:
                # Skip rows with missing critical data
                student_id = str(row.get('student_id', '')).strip()
                subject_code = str(row.get('subject_code', '')).strip()
                
                if not student_id or student_id == 'nan' or len(student_id) < 2:
                    continue
                if not subject_code or subject_code == 'nan':
                    continue
                
                record = AttendanceRecordInput(
                    student_id=student_id,
                    student_name=str(row.get('student_name', '')).strip() if pd.notna(row.get('student_name')) else None,
                    subject_code=subject_code,
                    subject_name=str(row.get('subject_name', '')).strip() if pd.notna(row.get('subject_name')) else None,
                    classes_conducted=int(float(row.get('classes_conducted', 0))) if pd.notna(row.get('classes_conducted')) else 0,
                    classes_attended=int(float(row.get('classes_attended', 0))) if pd.notna(row.get('classes_attended')) else 0,
                    od_count=int(float(row.get('od_count', 0))) if pd.notna(row.get('od_count')) else 0,
                    ml_count=int(float(row.get('ml_count', 0))) if pd.notna(row.get('ml_count')) else 0
                )
                records.append(record)
            except Exception as e:
                # Skip invalid rows
                continue
        
        print(f"✅ Successfully parsed {len(records)} attendance records")
        return records
    
    def _detect_column_mapping_fuzzy(self, columns: List[str]) -> Dict[str, str]:
        """
        Detect and map column names to standard names using fuzzy matching
        
        Args:
            columns: List of column names from file
            
        Returns:
            Mapping dict {original_name: standard_name}
        """
        mapping = {}
        used_columns = set()
        
        print("\n🔍 Fuzzy Column Matching:")
        
        # Find matches for each field in priority order
        priority_order = [
            'student_id', 'subject_code', 'classes_conducted', 'classes_attended',
            'student_name', 'subject_name', 'od_count', 'ml_count'
        ]
        
        for field in priority_order:
            patterns = self.column_patterns.get(field, [])
            match, score = self._find_best_column_match(columns, patterns, used_columns)
            
            if match:
                mapping[match] = field
                used_columns.add(match)
                print(f"  ✅ {field:20} ← '{match}' (confidence: {score*100:.0f}%)")
            else:
                print(f"  ⚠️  {field:20} ← Not found")
        
        return mapping
    
    def parse_pdf(self, file_path: str) -> List[AttendanceRecordInput]:
        """
        Parse PDF file and extract attendance records with fuzzy column matching
        
        Uses the same intelligent fuzzy matching system as Excel parser
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of AttendanceRecordInput objects
        """
        records = []
        
        print(f"📄 Parsing PDF file...")
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Extract tables from page
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # First row is usually headers
                    headers = [str(h) if h else '' for h in table[0]]
                    
                    # Detect column mapping using fuzzy matching
                    column_mapping = self._detect_column_mapping_fuzzy(headers)
                    
                    # Process data rows
                    for row in table[1:]:
                        if not row or len(row) != len(headers):
                            continue
                        
                        # Create dict from row
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if header in column_mapping and i < len(row):
                                standard_name = column_mapping[header]
                                row_dict[standard_name] = row[i]
                        
                        # Skip rows with missing critical data
                        student_id = str(row_dict.get('student_id', '')).strip()
                        subject_code = str(row_dict.get('subject_code', '')).strip()
                        
                        if not student_id or student_id == 'nan' or len(student_id) < 2:
                            continue
                        if not subject_code or subject_code == 'nan':
                            continue
                        
                        # Try to create record
                        try:
                            record = AttendanceRecordInput(
                                student_id=student_id,
                                student_name=str(row_dict.get('student_name', '')).strip() if row_dict.get('student_name') else None,
                                subject_code=subject_code,
                                subject_name=str(row_dict.get('subject_name', '')).strip() if row_dict.get('subject_name') else None,
                                classes_conducted=int(float(row_dict.get('classes_conducted', 0))) if row_dict.get('classes_conducted') else 0,
                                classes_attended=int(float(row_dict.get('classes_attended', 0))) if row_dict.get('classes_attended') else 0,
                                od_count=int(float(row_dict.get('od_count', 0))) if row_dict.get('od_count') else 0,
                                ml_count=int(float(row_dict.get('ml_count', 0))) if row_dict.get('ml_count') else 0
                            )
                            records.append(record)
                        except Exception as e:
                            # Skip invalid rows
                            continue
        
        print(f"✅ Successfully parsed {len(records)} attendance records from PDF")
        return records
    
    def parse_file(self, file_path: str) -> List[AttendanceRecordInput]:
        """
        Universal file parser - detects type and parses accordingly
        
        Args:
            file_path: Path to file
            
        Returns:
            List of AttendanceRecordInput objects
            
        Raises:
            ValueError: If file type is unsupported
        """
        file_type = self.detect_file_type(file_path)
        
        if file_type == 'excel':
            return self.parse_excel(file_path)
        elif file_type == 'pdf':
            return self.parse_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")


# Singleton instance
file_parser = FileParserService()
