import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Paper,
    Button,
    CircularProgress,
    Alert,
    FormControl,
    InputLabel,
    Select,
    MenuItem
} from '@mui/material';
import { analyzeAttendance } from '../../services/api';

interface DepartmentSelectionProps {
    uploadId: string;
    regulation: string;
    onSelect: (department: string) => void;
}

const DepartmentSelection: React.FC<DepartmentSelectionProps> = ({ uploadId, regulation, onSelect }) => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [departments, setDepartments] = useState<string[]>([]);
    const [selectedDept, setSelectedDept] = useState<string>('');

    useEffect(() => {
        loadDepartments();
    }, [uploadId, regulation]);

    const loadDepartments = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await analyzeAttendance(uploadId, regulation);
            const depts = new Set<string>();
            data.students.forEach((student: any) => {
                if (student.department) {
                    depts.add(student.department);
                }
            });

            const uniqueDepts = Array.from(depts).sort();
            setDepartments(uniqueDepts);

            if (uniqueDepts.length === 1) {
                // Auto-select if only one department
                setSelectedDept(uniqueDepts[0]);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to analyze attendance data');
        } finally {
            setLoading(false);
        }
    };

    const handleProceed = () => {
        onSelect(selectedDept || 'all');
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 8 }}>
                <CircularProgress sx={{ mb: 2 }} />
                <Typography color="text.secondary">Analyzing uploaded data and extracting departments...</Typography>
            </Box>
        );
    }

    if (error) {
        return (
            <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        );
    }

    return (
        <Paper sx={{ p: 4, maxWidth: 600, mx: 'auto', textAlign: 'center' }}>
            <Typography variant="h5" gutterBottom>
                Select Department
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
                We found {departments.length} department(s) in the uploaded file.
            </Typography>

            {departments.length > 0 ? (
                <FormControl fullWidth sx={{ mb: 4 }}>
                    <InputLabel id="department-select-label">Department</InputLabel>
                    <Select
                        labelId="department-select-label"
                        value={selectedDept}
                        label="Department"
                        onChange={(e) => setSelectedDept(e.target.value)}
                    >
                        <MenuItem value="">
                            <em>Select a department</em>
                        </MenuItem>
                        {departments.map(dept => (
                            <MenuItem key={dept} value={dept}>{dept}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
            ) : (
                <Alert severity="warning" sx={{ mb: 4 }}>
                    Could not identify any departments automatically. You will see all students.
                </Alert>
            )}

            <Button
                variant="contained"
                color="primary"
                size="large"
                onClick={handleProceed}
                disabled={departments.length > 0 && !selectedDept}
                fullWidth
            >
                View Dashboard
            </Button>
        </Paper>
    );
};

export default DepartmentSelection;
