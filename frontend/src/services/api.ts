/**
 * API client for backend communication
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

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
