// Re-export all types for cleaner imports
export type {
    StudentAttendance,
    AttendanceAnalysis,
    FileUploadResponse
} from './attendance';

export interface SubjectComponent {
    subject_code: string;
    subject_name?: string;
    classes_conducted: number;
    classes_attended: number;
    od_count: number;
    ml_count: number;
    percentage: number;
}

export interface SubjectAttendance {
    subject_code: string;
    subject_name?: string;
    is_combined: boolean;
    combined_from?: string[];
    components?: SubjectComponent[];
    classes_conducted: number;
    classes_attended: number;
    od_count: number;
    ml_count: number;
    original_percentage: number;
    final_percentage: number;
    od_ml_adjusted: boolean;
    category: 'critical' | 'danger' | 'border' | 'safe';
    category_label: string;
    category_color: string;
}
