/**
 * API client for backend communication
 */
import axios from 'axios';

let API_BASE_URL = import.meta.env.VITE_API_URL || 'https://perfoma-qe6d.onrender.com/api';

// Ensure URL ends with /api
if (API_BASE_URL.endsWith('/')) {
    API_BASE_URL = API_BASE_URL.slice(0, -1);
}
if (!API_BASE_URL.endsWith('/api')) {
    API_BASE_URL += '/api';
}

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Upload file
export const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });

    return response.data;
};

// Analyze attendance
export const analyzeAttendance = async (uploadId: string, regulation: string = "U18") => {
    const response = await api.post(`/analyze/${uploadId}?regulation=${regulation}`);
    return response.data;
};

// Get analysis
export const getAnalysis = async (uploadId: string) => {
    const response = await api.get(`/analysis/${uploadId}`);
    return response.data;
};

// Generate report
export const generateReport = async (uploadId: string, format: string = 'excel') => {
    const response = await api.post('/reports/generate', {
        upload_id: uploadId,
        format,
    });
    return response.data;
};

// Download report
export const downloadReport = (filename: string) => {
    return `${API_BASE_URL}/reports/download/${filename}`;
};

// Get summary
export const getSummary = async (uploadId: string) => {
    const response = await api.get(`/summary/${uploadId}`);
    return response.data;
};

// Proforma APIs
export const getProformaStudents = async (uploadId: string, type: '1A' | '1B', department?: string) => {
    const params: Record<string, string> = {};
    if (department && department !== 'all') {
        params.department = department;
    }
    const response = await api.get(`/proforma/${uploadId}/${type}`, { params });
    return response.data;
};

export const updateProformaEntry = async (entry: {
    upload_id: string;
    student_id: string;
    subject_code: string;
    proforma_type: '1A' | '1B';
    reason?: string;
    status?: string;
}) => {
    const response = await api.post('/proforma/entry', entry);
    return response.data;
};

export const uploadProof = async (uploadId: string, studentId: string, subjectCode: string, file: File) => {
    const formData = new FormData();
    formData.append('upload_id', uploadId);
    formData.append('student_id', studentId);
    formData.append('subject_code', subjectCode);
    formData.append('file', file);

    const response = await api.post('/proforma/upload_proof', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const approveStudent = async (uploadId: string, studentId: string, subjectCode: string) => {
    const response = await api.post(`/proforma/approve?upload_id=${uploadId}&student_id=${studentId}&subject_code=${subjectCode}`);
    return response.data;
};

export const generateProformaReport = async (uploadId: string, type: '1A' | '1B', format: 'pdf' | 'excel' = 'pdf') => {
    const response = await api.get(`/proforma/download/${uploadId}/${type}`, {
        params: { format }
    });
    return response.data;
};
