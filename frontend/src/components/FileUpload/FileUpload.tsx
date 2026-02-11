import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Box, Typography, Paper, Button, LinearProgress, Alert } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { uploadFile } from '../../services/api';

interface FileUploadProps {
    onUploadSuccess: (uploadId: string, filename: string) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        if (acceptedFiles.length === 0) return;

        const file = acceptedFiles[0];
        setUploadedFile(file);
        setError(null);
        setUploading(true);

        try {
            const response = await uploadFile(file);
            setUploading(false);
            onUploadSuccess(response.upload_id, response.filename);
        } catch (err: any) {
            setUploading(false);
            setError(err.response?.data?.detail || 'Failed to upload file');
        }
    }, [onUploadSuccess]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            'application/vnd.ms-excel': ['.xls'],
            'application/pdf': ['.pdf'],
        },
        maxFiles: 1,
    });

    return (
        <Box>
            <Paper
                {...getRootProps()}
                sx={{
                    p: 6,
                    textAlign: 'center',
                    border: '2px dashed',
                    borderColor: isDragActive ? 'primary.main' : 'grey.300',
                    bgcolor: isDragActive ? 'action.hover' : 'background.paper',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                        borderColor: 'primary.main',
                        bgcolor: 'action.hover',
                    },
                }}
            >
                <input {...getInputProps()} />
                <CloudUploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
                <Typography variant="h5" gutterBottom>
                    {isDragActive ? 'Drop the file here' : 'Upload Attendance File'}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Drag and drop your Excel (.xlsx, .xls) or PDF file here, or click to browse
                </Typography>
                <Button variant="outlined" component="span">
                    Select File
                </Button>
            </Paper>

            {uploadedFile && (
                <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <InsertDriveFileIcon color="primary" />
                    <Typography variant="body2">{uploadedFile.name}</Typography>
                </Box>
            )}

            {uploading && (
                <Box sx={{ mt: 2 }}>
                    <LinearProgress />
                    <Typography variant="body2" sx={{ mt: 1 }} color="text.secondary">
                        Uploading and processing file...
                    </Typography>
                </Box>
            )}

            {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                </Alert>
            )}
        </Box>
    );
};

export default FileUpload;
