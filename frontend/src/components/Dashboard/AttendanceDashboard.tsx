import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    Button,
    Card,
    CardContent,
    TextField,
    MenuItem,
    CircularProgress,
    Alert,
    IconButton,
    Collapse,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import type { AttendanceAnalysis, StudentAttendance } from '../../types/index';
import { analyzeAttendance, generateReport, downloadReport } from '../../services/api';

interface AttendanceDashboardProps {
    uploadId: string;
    filename: string;
}

const CATEGORY_COLORS: Record<string, string> = {
    critical: '#f44336',
    danger: '#ff9800',
    border: '#ffc107',
    safe: '#4caf50',
};

const CATEGORY_LABELS: Record<string, string> = {
    critical: 'Critical',
    danger: 'Not Safe',
    border: 'Border',
    safe: 'Safe',
};

const AttendanceDashboard: React.FC<AttendanceDashboardProps> = ({ uploadId, filename }) => {
    const [analysis, setAnalysis] = useState<AttendanceAnalysis | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterCategory, setFilterCategory] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedSubjects, setExpandedSubjects] = useState<Record<string, boolean>>({});
    const [downloading, setDownloading] = useState(false);

    useEffect(() => {
        loadAnalysis();
    }, [uploadId]);

    const loadAnalysis = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await analyzeAttendance(uploadId);
            setAnalysis(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to analyze attendance');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadReport = async () => {
        setDownloading(true);
        try {
            const reportData = await generateReport(uploadId, 'excel');
            window.open(downloadReport(reportData.filename), '_blank');
        } catch (err: any) {
            setError('Failed to generate report');
        } finally {
            setDownloading(false);
        }
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return <Alert severity="error">{error}</Alert>;
    }

    if (!analysis) {
        return <Alert severity="info">No analysis data available</Alert>;
    }

    // Prepare chart data
    const chartData = Object.entries(analysis.category_distribution).map(([key, value]) => ({
        category: CATEGORY_LABELS[key] || key,
        count: value,
        color: CATEGORY_COLORS[key],
    }));

    // Filter students
    const filteredStudents = analysis.students.filter((student) => {
        const matchesCategory = filterCategory === 'all' || student.overall_category === filterCategory;
        const matchesSearch =
            !searchQuery ||
            student.student_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (student.student_name && student.student_name.toLowerCase().includes(searchQuery.toLowerCase()));
        return matchesCategory && matchesSearch;
    });

    return (
        <Box>
            {/* Header */}
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" gutterBottom>
                        Attendance Analysis
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        File: {filename}
                    </Typography>
                </Box>
                <Button
                    variant="contained"
                    startIcon={downloading ? <CircularProgress size={20} /> : <DownloadIcon />}
                    onClick={handleDownloadReport}
                    disabled={downloading}
                >
                    Download Report
                </Button>
            </Box>

            {/* Summary Cards */}
            <Box sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: 'repeat(4, 1fr)' },
                gap: 3,
                mb: 4
            }}>
                <Card>
                    <CardContent>
                        <Typography color="text.secondary" gutterBottom>
                            Total Students
                        </Typography>
                        <Typography variant="h3">{analysis.total_students}</Typography>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent>
                        <Typography color="text.secondary" gutterBottom>
                            Total Subjects
                        </Typography>
                        <Typography variant="h3">{analysis.total_subjects}</Typography>
                    </CardContent>
                </Card>
                <Card sx={{ bgcolor: '#FFCDD2' }}>
                    <CardContent>
                        <Typography color="text.secondary" gutterBottom>
                            Critical Students
                        </Typography>
                        <Typography variant="h3" color="error">
                            {analysis.category_distribution.critical || 0}
                        </Typography>
                    </CardContent>
                </Card>
                <Card sx={{ bgcolor: '#C8E6C9' }}>
                    <CardContent>
                        <Typography color="text.secondary" gutterBottom>
                            Safe Students
                        </Typography>
                        <Typography variant="h3" sx={{ color: '#4caf50' }}>
                            {analysis.category_distribution.safe || 0}
                        </Typography>
                    </CardContent>
                </Card>
            </Box>

            {/* Chart */}
            <Paper sx={{ p: 3, mb: 4 }}>
                <Typography variant="h6" gutterBottom>
                    Category Distribution
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="category" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="count" name="Students">
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </Paper>

            {/* Filters */}
            <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
                <TextField
                    label="Search Student"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    variant="outlined"
                    size="small"
                    sx={{ flex: 1 }}
                />
                <TextField
                    select
                    label="Filter by Category"
                    value={filterCategory}
                    onChange={(e) => setFilterCategory(e.target.value)}
                    variant="outlined"
                    size="small"
                    sx={{ minWidth: 200 }}
                >
                    <MenuItem value="all">All Categories</MenuItem>
                    <MenuItem value="critical">Critical</MenuItem>
                    <MenuItem value="danger">Not Safe</MenuItem>
                    <MenuItem value="border">Border</MenuItem>
                    <MenuItem value="safe">Safe</MenuItem>
                </TextField>
            </Box>

            {/* Student Table */}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell><strong>Student ID</strong></TableCell>
                            <TableCell><strong>Student Name</strong></TableCell>
                            <TableCell><strong>Overall %</strong></TableCell>
                            <TableCell><strong>Category</strong></TableCell>
                            <TableCell><strong>Subjects</strong></TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredStudents.map((student) => (
                            <TableRow key={student.student_id}>
                                <TableCell>{student.student_id}</TableCell>
                                <TableCell>{student.student_name || '-'}</TableCell>
                                <TableCell>
                                    <Typography
                                        sx={{
                                            fontWeight: 'bold',
                                            color: CATEGORY_COLORS[student.overall_category],
                                        }}
                                    >
                                        {student.overall_percentage.toFixed(2)}%
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={CATEGORY_LABELS[student.overall_category]}
                                        size="small"
                                        sx={{
                                            bgcolor: CATEGORY_COLORS[student.overall_category],
                                            color: 'white',
                                        }}
                                    />
                                </TableCell>
                                <TableCell>
                                    {student.subjects.map((subject, idx) => {
                                        const subjectKey = `${student.student_id}-${subject.subject_code}`;
                                        const isExpanded = expandedSubjects[subjectKey] || false;

                                        return (
                                            <Box key={idx} sx={{ mb: 0.5 }}>
                                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                    {subject.is_combined && (
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => setExpandedSubjects(prev => ({
                                                                ...prev,
                                                                [subjectKey]: !prev[subjectKey]
                                                            }))}
                                                            sx={{ p: 0, mr: 0.5 }}
                                                        >
                                                            {isExpanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
                                                        </IconButton>
                                                    )}
                                                    <Typography variant="caption">
                                                        <strong>{subject.subject_code}</strong>:
                                                        {subject.od_ml_adjusted ? (
                                                            <>
                                                                <span style={{ textDecoration: 'line-through', color: '#999', marginLeft: '4px' }}>
                                                                    {subject.original_percentage.toFixed(1)}%
                                                                </span>
                                                                <span style={{ margin: '0 4px' }}>→</span>
                                                                <span style={{ color: '#4caf50', fontWeight: 'bold' }}>
                                                                    {subject.final_percentage.toFixed(1)}%
                                                                </span>
                                                                <span style={{ fontSize: '0.85em', color: '#1976d2', marginLeft: '4px' }}>
                                                                    (OD/ML)
                                                                </span>
                                                            </>
                                                        ) : (
                                                            <span style={{ marginLeft: '4px' }}>
                                                                {subject.final_percentage.toFixed(1)}%
                                                            </span>
                                                        )}
                                                        {subject.is_combined && (
                                                            <span style={{ fontSize: '0.85em', color: '#ff9800', marginLeft: '4px', fontWeight: 'bold' }}>
                                                                (T+L)
                                                            </span>
                                                        )}
                                                    </Typography>
                                                </Box>

                                                {subject.is_combined && (
                                                    <Collapse in={isExpanded}>
                                                        <Box sx={{ ml: 3, mt: 0.5, pl: 1, borderLeft: '2px solid #e0e0e0' }}>
                                                            {/* Display detailed components if available */}
                                                            {subject.components && subject.components.length > 0 ? (
                                                                subject.components.map((comp, i) => {
                                                                    const isTheory = comp.subject_code.endsWith('T');
                                                                    const isLab = comp.subject_code.endsWith('L');
                                                                    const label = isTheory ? 'Theory' : isLab ? 'Lab' : comp.subject_code;

                                                                    return (
                                                                        <Box key={i} sx={{ mb: 0.5 }}>
                                                                            <Typography variant="caption" sx={{ display: 'block', color: '#444', fontWeight: 500, fontSize: '0.75rem' }}>
                                                                                {label} ({comp.subject_code})
                                                                            </Typography>
                                                                            <Typography variant="caption" sx={{ display: 'block', color: '#666', fontSize: '0.7rem' }}>
                                                                                Details: {comp.classes_attended}/{comp.classes_conducted} ({comp.percentage}%)
                                                                                {comp.od_count > 0 && ` | OD: ${comp.od_count}`}
                                                                                {comp.ml_count > 0 && ` | ML: ${comp.ml_count}`}
                                                                            </Typography>
                                                                        </Box>
                                                                    );
                                                                })
                                                            ) : (
                                                                // Fallback for backward compatibility
                                                                subject.combined_from?.map((code, i) => (
                                                                    <Typography key={i} variant="caption" sx={{ display: 'block', color: '#666', fontSize: '0.7rem' }}>
                                                                        {code}
                                                                    </Typography>
                                                                ))
                                                            )}

                                                            <Typography variant="caption" sx={{ display: 'block', color: '#1976d2', fontSize: '0.7rem', mt: 0.5, fontStyle: 'italic' }}>
                                                                Total: {subject.classes_attended}/{subject.classes_conducted}
                                                                {subject.od_count > 0 && ` | OD: ${subject.od_count}`}
                                                                {subject.ml_count > 0 && ` | ML: ${subject.ml_count}`}
                                                            </Typography>
                                                        </Box>
                                                    </Collapse>
                                                )}
                                            </Box>
                                        );
                                    })}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {filteredStudents.length === 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                    No students match the current filters
                </Alert>
            )}
        </Box>
    );
};

export default AttendanceDashboard;
