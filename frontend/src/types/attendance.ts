// TypeScript interfaces for attendance data

export interface AttendanceRecordInput {
    student_id: string;
    student_name?: string;
    subject_code: string;
    subject_name?: string;
    classes_conducted: number;
    classes_attended: number;
    od_count?: number;
    ml_count?: number;
}

export interface SubjectAttendance {
    subject_code: string;
    subject_name?: string;
    is_combined: boolean;
    combined_from?: string[];
    classes_conducted: number;
    classes_attended: number;
    od_count: number;
    ml_count: number;
    original_percentage: number;
    od_ml_adjusted: boolean;
    final_percentage: number;
    category: string;
    category_label: string;
    category_color: string;
}

export interface StudentAttendance {
    student_id: string;
    student_name?: string;
    subjects: SubjectAttendance[];
    overall_percentage: number;
    overall_category: string;
}

export interface AttendanceAnalysis {
    upload_id: string;
    processed_at: string;
    total_students: number;
    total_subjects: number;
    students: StudentAttendance[];
    category_distribution: Record<string, number>;
}

export interface FileUploadResponse {
    upload_id: string;
    filename: string;
    file_type: string;
    total_records: number;
    preview: AttendanceRecordInput[];
    message: string;
}
