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
    Tabs,
    Tab,
    Menu,
} from '@mui/material';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import TableChartIcon from '@mui/icons-material/TableChart';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DownloadIcon from '@mui/icons-material/Download';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import type { AttendanceAnalysis } from '../../types/index';
import { analyzeAttendance, generateReport, downloadReport } from '../../services/api';
import ProformaDashboard from './ProformaDashboard';

interface AttendanceDashboardProps {
    uploadId: string;
    filename: string;
    regulation: string;
    selectedDepartment: string;
}

const CATEGORY_COLORS: Record<string, string> = {
    critical: '#f44336',
    danger: '#ff9800',
    border: '#ffc107',
    safe: '#4caf50',
};

const CATEGORY_LABELS: Record<string, string> = {
    critical: 'Critical (< 65%)',
    danger: 'Not Safe (65% - 75%)',
    border: 'Border (75% - 80%)',
    safe: 'Safe (≥ 80%)',
};

const AttendanceDashboard: React.FC<AttendanceDashboardProps> = ({ uploadId, filename, regulation, selectedDepartment }) => {
    const [analysis, setAnalysis] = useState<AttendanceAnalysis | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterCategory, setFilterCategory] = useState('all');
    const [filterSubject, setFilterSubject] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedSubjects, setExpandedSubjects] = useState<Record<string, boolean>>({});
    const [downloading, setDownloading] = useState(false);
    const [mainTab, setMainTab] = useState(0);
    const [downloadAnchorEl, setDownloadAnchorEl] = useState<null | HTMLElement>(null);

    const handleOpenDownloadMenu = (event: React.MouseEvent<HTMLButtonElement>) => {
        setDownloadAnchorEl(event.currentTarget);
    };

    const handleCloseDownloadMenu = () => {
        setDownloadAnchorEl(null);
    };

    useEffect(() => {
        loadAnalysis();
    }, [uploadId]);

    const loadAnalysis = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await analyzeAttendance(uploadId, regulation);
            setAnalysis(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to analyze attendance');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadReport = async (format: 'excel' | 'pdf') => {
        setDownloading(true);
        try {
            const reportData = await generateReport(uploadId, format, selectedDepartment);

            // Create a temporary link to trigger download
            const url = downloadReport(reportData.filename);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', reportData.filename);
            document.body.appendChild(link);
            link.click();

            // Cleanup
            document.body.removeChild(link);
        } catch (err: any) {
            console.error("Download failed:", err);
            setError('Failed to generate report');
        } finally {
            setDownloading(false);
        }
    };

    // Get unique subjects for filter - Moved before early returns to follow Rules of Hooks
    const uniqueSubjects = React.useMemo(() => {
        if (!analysis) return [];
        const subjects = new Map<string, string>();
        analysis.students
            .filter(student => selectedDepartment === 'all' || student.department === selectedDepartment)
            .forEach(student => {
                student.subjects.forEach(sub => {
                    if (!subjects.has(sub.subject_code)) {
                        subjects.set(sub.subject_code, sub.subject_name || sub.subject_code);
                    }
                });
            });
        return Array.from(subjects.entries())
            .map(([code, name]) => ({ code, name }))
            .sort((a, b) => a.code.localeCompare(b.code));
    }, [analysis, selectedDepartment]);

    // Calculate dynamic distribution and summary stats - Moved before early returns
    const { dynamicDistribution, dynamicTotalStudents, displayStudents } = React.useMemo(() => {
        if (!analysis) return {
            dynamicDistribution: { critical: 0, danger: 0, border: 0, safe: 0 },
            dynamicTotalStudents: 0,
            displayStudents: []
        };

        const dist: Record<string, number> = { critical: 0, danger: 0, border: 0, safe: 0 };
        let count = 0;

        const processed = analysis.students
            .filter(student => selectedDepartment === 'all' || student.department === selectedDepartment)
            .map(student => {
                let statusCategory = student.overall_category;
                let displayOriginal = student.overall_original_percentage;
                let displayFinal = student.overall_final_percentage;
                let displayAdjusted = student.overall_od_ml_adjusted;
                let hasSubject = true;

                if (filterSubject !== 'all') {
                    const sub = student.subjects.find(s => s.subject_code === filterSubject);
                    if (sub) {
                        statusCategory = sub.category;
                        displayOriginal = sub.original_percentage;
                        displayFinal = sub.final_percentage;
                        displayAdjusted = sub.od_ml_adjusted;
                    } else {
                        hasSubject = false;
                    }
                }

                if (!hasSubject) return null;

                // Apply filters
                const matchesCategory = filterCategory === 'all' || statusCategory === filterCategory;
                const matchesSearch =
                    !searchQuery ||
                    student.student_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    (student.student_name && student.student_name.toLowerCase().includes(searchQuery.toLowerCase()));

                if (matchesCategory && matchesSearch) {
                    dist[statusCategory] = (dist[statusCategory] || 0) + 1;
                    count++;
                    return {
                        ...student,
                        displayPercentage: displayOriginal, // Default to showing original per user request
                        displayOriginalPercentage: displayOriginal,
                        displayFinalPercentage: displayFinal,
                        displayCategory: statusCategory,
                        displayAdjusted: displayAdjusted
                    };
                }
                return null;
            }).filter(Boolean) as any[];

        return {
            dynamicDistribution: dist,
            dynamicTotalStudents: count,
            displayStudents: processed
        };
    }, [analysis, filterSubject, filterCategory, searchQuery, selectedDepartment]);

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ p: 2 }}>
                <Alert severity="error">{error}</Alert>
            </Box>
        );
    }

    if (!analysis) {
        return (
            <Box sx={{ p: 2 }}>
                <Alert severity="info">No analysis data available</Alert>
            </Box>
        );
    }

    // Prepare chart data
    const chartData = Object.entries(dynamicDistribution).map(([key, value]) => ({
        category: CATEGORY_LABELS[key] || key,
        count: value,
        color: CATEGORY_COLORS[key],
    }));

    const selectedSubjectName = filterSubject === 'all' ? 'Overall' : uniqueSubjects.find(s => s.code === filterSubject)?.name || filterSubject;

    return (
        <Box>
            {/* Header */}
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" gutterBottom>
                        Attendance Analysis {selectedDepartment !== 'all' && `- ${selectedDepartment}`}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        File: {filename} • Regulation: <Chip label={regulation} size="small" color="primary" variant="outlined" sx={{ ml: 1, height: 20, fontSize: '0.75rem' }} />
                        {filterSubject !== 'all' && (
                            <Chip label={`Filtered: ${filterSubject}`} size="small" color="secondary" sx={{ ml: 1, height: 20, fontSize: '0.75rem' }} />
                        )}
                    </Typography>
                </Box>
                <Box sx={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
                    <Tabs value={mainTab} onChange={(_e, v) => setMainTab(v)}>
                        <Tab label="Attendance Overview" />
                        <Tab label="Proforma Report" />
                    </Tabs>
                </Box>
                {mainTab === 0 && (
                    <Box>
                        <Button
                            variant="contained"
                            color="primary"
                            startIcon={downloading ? <CircularProgress size={20} color="inherit" /> : <DownloadIcon />}
                            endIcon={<KeyboardArrowDownIcon />}
                            onClick={handleOpenDownloadMenu}
                            disabled={downloading}
                        >
                            Download
                        </Button>
                        <Menu
                            anchorEl={downloadAnchorEl}
                            open={Boolean(downloadAnchorEl)}
                            onClose={handleCloseDownloadMenu}
                        >
                            <MenuItem onClick={() => { handleCloseDownloadMenu(); handleDownloadReport('pdf'); }}>
                                <PictureAsPdfIcon sx={{ mr: 1, color: 'error.main' }} fontSize="small" />
                                Download PDF
                            </MenuItem>
                            <MenuItem onClick={() => { handleCloseDownloadMenu(); handleDownloadReport('excel'); }}>
                                <TableChartIcon sx={{ mr: 1, color: 'success.main' }} fontSize="small" />
                                Download Excel
                            </MenuItem>
                        </Menu>
                    </Box>
                )}
            </Box>

            <Box sx={{ display: mainTab === 0 ? 'block' : 'none' }}>
                {/* Summary Information Header */}
                <Box sx={{ mb: 2, display: 'flex', gap: 3 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        Total Students: <span style={{ color: '#1976d2' }}>{dynamicTotalStudents}</span>
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        Total Subjects: <span style={{ color: '#1976d2' }}>{analysis.total_subjects}</span>
                    </Typography>
                </Box>

                {/* Summary Cards */}
                <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' },
                    gap: 2,
                    mb: 4
                }}>
                    <Card sx={{ borderLeft: '5px solid #f44336', bgcolor: '#fff5f5' }}>
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                            <Typography color="error" variant="overline" sx={{ fontWeight: 'bold', display: 'block' }}>
                                Critical {"(< 65%)"}
                            </Typography>
                            <Typography variant="h4" color="error">
                                {dynamicDistribution.critical || 0}
                            </Typography>
                        </CardContent>
                    </Card>
                    <Card sx={{ borderLeft: '5px solid #ff9800', bgcolor: '#fff9f0' }}>
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                            <Typography sx={{ color: '#ff9800', fontWeight: 'bold', display: 'block' }} variant="overline">
                                Not Safe (65% - 75%)
                            </Typography>
                            <Typography variant="h4" sx={{ color: '#ff9800' }}>
                                {dynamicDistribution.danger || 0}
                            </Typography>
                        </CardContent>
                    </Card>
                    <Card sx={{ borderLeft: '5px solid #ffc107', bgcolor: '#fffcf0' }}>
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                            <Typography sx={{ color: '#ffc107', fontWeight: 'bold', display: 'block' }} variant="overline">
                                Border (75% - 80%)
                            </Typography>
                            <Typography variant="h4" sx={{ color: '#ffc107' }}>
                                {dynamicDistribution.border || 0}
                            </Typography>
                        </CardContent>
                    </Card>
                    <Card sx={{ borderLeft: '5px solid #4caf50', bgcolor: '#f5fff5' }}>
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                            <Typography sx={{ color: '#4caf50', fontWeight: 'bold', display: 'block' }} variant="overline">
                                Safe (≥ 80%)
                            </Typography>
                            <Typography variant="h4" sx={{ color: '#4caf50' }}>
                                {dynamicDistribution.safe || 0}
                            </Typography>
                        </CardContent>
                    </Card>
                </Box>

                {/* Chart */}
                <Paper sx={{ p: 3, mb: 4 }}>
                    <Typography variant="h6" gutterBottom>
                        Risk Distribution: {selectedSubjectName}
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
                        label="Filter by Subject"
                        value={filterSubject}
                        onChange={(e) => setFilterSubject(e.target.value)}
                        variant="outlined"
                        size="small"
                        sx={{ minWidth: 200 }}
                    >
                        <MenuItem value="all">All Subjects (Overall)</MenuItem>
                        {uniqueSubjects.map((sub) => (
                            <MenuItem key={sub.code} value={sub.code}>
                                {sub.code} - {sub.name}
                            </MenuItem>
                        ))}
                    </TextField>
                    <TextField
                        select
                        label="Filter by Category"
                        value={filterCategory}
                        onChange={(e) => setFilterCategory(e.target.value)}
                        variant="outlined"
                        size="small"
                        sx={{ minWidth: 250 }}
                    >
                        <MenuItem value="all">All Categories</MenuItem>
                        <MenuItem value="critical">Critical {"(< 65%)"}</MenuItem>
                        <MenuItem value="danger">Not Safe (65% - 75%)</MenuItem>
                        <MenuItem value="border">Border (75% - 80%)</MenuItem>
                        <MenuItem value="safe">Safe (≥ 80%)</MenuItem>
                    </TextField>
                </Box>

                {/* Student Table */}
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell><strong>Student ID</strong></TableCell>
                                <TableCell><strong>Student Name</strong></TableCell>
                                <TableCell><strong>{filterSubject === 'all' ? 'Overall %' : 'Subject %'}</strong></TableCell>
                                <TableCell><strong>Status</strong></TableCell>
                                <TableCell><strong>Subjects Breakdown</strong></TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {displayStudents.map((student: any) => (
                                <TableRow key={student.student_id}>
                                    <TableCell>{student.student_id}</TableCell>
                                    <TableCell>{student.student_name || '-'}</TableCell>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                                            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                                                {student.displayAdjusted ? (
                                                    <>
                                                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                            <span style={{ textDecoration: 'line-through', color: '#999', marginRight: '4px', fontSize: '0.9em' }}>
                                                                {student.total_attended}/{student.total_conducted} ({student.displayOriginalPercentage.toFixed(2)}%)
                                                            </span>
                                                        </Box>
                                                        <Box sx={{ display: 'flex', alignItems: 'center', color: CATEGORY_COLORS[student.displayCategory], fontWeight: 'bold' }}>
                                                            <span style={{ marginRight: '4px' }}>→</span>
                                                            <span>
                                                                {student.total_adjusted_attended}/{student.total_conducted} ({student.displayFinalPercentage.toFixed(2)}%)
                                                            </span>
                                                        </Box>
                                                    </>
                                                ) : (
                                                    <Typography
                                                        sx={{
                                                            fontWeight: 'bold',
                                                            color: CATEGORY_COLORS[student.displayCategory],
                                                        }}
                                                    >
                                                        {student.total_attended}/{student.total_conducted} ({student.displayPercentage.toFixed(2)}%)
                                                    </Typography>
                                                )}
                                            </Box>
                                            {filterSubject === 'all' && (
                                                <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: '#1976d2', fontStyle: 'italic', lineHeight: 1 }}>
                                                    Total used: OD:{student.total_od} ML:{student.total_ml}
                                                </Typography>
                                            )}
                                        </Box>
                                    </TableCell>
                                    <TableCell>
                                        <Chip
                                            label={CATEGORY_LABELS[student.displayCategory]}
                                            size="small"
                                            sx={{
                                                bgcolor: CATEGORY_COLORS[student.displayCategory],
                                                color: 'white',
                                            }}
                                        />
                                    </TableCell>
                                    <TableCell>
                                        {student.subjects
                                            .filter((s: any) => filterSubject === 'all' || s.subject_code === filterSubject)
                                            .map((subject: any, idx: number) => {
                                                const subjectKey = `${student.student_id}-${subject.subject_code}`;
                                                const isExpanded = expandedSubjects[subjectKey] || filterSubject !== 'all';

                                                return (
                                                    <Box key={idx} sx={{ mb: 0.5 }}>
                                                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                            {subject.is_combined && (
                                                                <IconButton
                                                                    size="small"
                                                                    disableRipple
                                                                    onClick={() => setExpandedSubjects(prev => ({
                                                                        ...prev,
                                                                        [subjectKey]: !prev[subjectKey]
                                                                    }))}
                                                                    sx={{ p: 0, mr: 0.5 }}
                                                                >
                                                                    {isExpanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
                                                                </IconButton>
                                                            )}
                                                            <Typography variant="caption" component="div">
                                                                <strong>{subject.subject_code}</strong>:
                                                                {subject.od_ml_adjusted ? (
                                                                    <>
                                                                        <Box sx={{ display: 'block', textDecoration: 'line-through', color: '#999', fontSize: '0.9em' }}>
                                                                            {subject.classes_attended}/{subject.classes_posted > 0 ? subject.classes_posted : subject.classes_conducted} ({subject.original_percentage.toFixed(1)}%)
                                                                        </Box>
                                                                        <Box sx={{ display: 'flex', alignItems: 'center', color: '#4caf50', fontWeight: 'bold' }}>
                                                                            <span style={{ marginRight: '4px' }}>→</span>
                                                                            {subject.adjusted_attended || Math.min(subject.classes_attended + subject.od_count + subject.ml_count, subject.classes_posted > 0 ? subject.classes_posted : subject.classes_conducted)}/{subject.classes_posted > 0 ? subject.classes_posted : subject.classes_conducted} ({subject.final_percentage.toFixed(1)}%)
                                                                            <Chip label="Eligible" size="small" color="success" sx={{ ml: 1, height: 20, fontSize: '0.65rem' }} />
                                                                        </Box>
                                                                    </>
                                                                ) : (
                                                                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                                        <span style={{ marginLeft: '4px' }}>
                                                                            {subject.classes_attended}/{subject.classes_posted > 0 ? subject.classes_posted : subject.classes_conducted} ({subject.final_percentage.toFixed(1)}%)
                                                                        </span>
                                                                        {(subject.od_count > 0 || subject.ml_count > 0) && (
                                                                            <Chip label="Not Eligible" size="small" color="error" variant="outlined" sx={{ ml: 1, height: 20, fontSize: '0.65rem' }} />
                                                                        )}
                                                                    </Box>
                                                                )}
                                                                {subject.is_combined && (
                                                                    <span style={{ fontSize: '0.85em', color: '#ff9800', marginLeft: '4px', fontWeight: 'bold' }}>
                                                                        (T+L)
                                                                    </span>
                                                                )}
                                                            </Typography>
                                                        </Box>

                                                        {/* Subject Attendance Details for ALL subjects (not just combined) */}
                                                        <Box sx={{ ml: subject.is_combined ? 3 : 0, mt: 0.2 }}>
                                                            {!subject.is_combined && (
                                                                <Typography variant="caption" sx={{ display: 'block', color: '#666', fontSize: '0.7rem' }}>
                                                                    Details: {subject.classes_attended}/{subject.classes_posted > 0 ? subject.classes_posted : subject.classes_conducted} | OD: {subject.od_count} | ML: {subject.ml_count}
                                                                </Typography>
                                                            )}
                                                        </Box>

                                                        {subject.is_combined && (
                                                            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                                                                <Box sx={{ ml: 3, mt: 0.5, pl: 1, borderLeft: '2px solid #e0e0e0' }}>
                                                                    {subject.components && subject.components.length > 0 ? (
                                                                        subject.components.map((comp: any, i: number) => {
                                                                            // Check for 'L' or 'J' (Project) followed by end of string OR hyphen (e.g., U18...L or U18...L-R21)
                                                                            // Also check if preceding character is a number to avoid false positives in names like "DIGITAL-LAB"
                                                                            const isLab = /[0-9][LJ](-|$)/.test(comp.subject_code) || comp.subject_code.endsWith('L') || comp.subject_code.endsWith('J');
                                                                            const isTheory = !isLab;
                                                                            const hasClaims = comp.od_count > 0 || comp.ml_count > 0;
                                                                            // If backend doesn't send final_percentage for components yet, fallback to percentage
                                                                            const finalPct = comp.final_percentage !== undefined ? comp.final_percentage : comp.percentage;
                                                                            const isAdjusted = comp.adjusted_attended > comp.classes_attended;

                                                                            return (
                                                                                <Box key={i} sx={{ mb: 1, p: 1, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                                                                                    <Typography variant="subtitle2" sx={{ display: 'flex', justifyContent: 'space-between', color: '#444' }}>
                                                                                        <span>{comp.subject_code} - {comp.subject_name || (isTheory ? 'Theory' : 'Lab')}</span>
                                                                                        <Box>
                                                                                            <Chip
                                                                                                label={isTheory ? 'Theory' : 'Lab'}
                                                                                                size="small"
                                                                                                variant="outlined"
                                                                                                sx={{ height: 20, fontSize: '0.65rem', mr: 1 }}
                                                                                            />
                                                                                            {hasClaims && (
                                                                                                <Chip
                                                                                                    label={isAdjusted ? "Eligible" : "Not Eligible"}
                                                                                                    size="small"
                                                                                                    color={isAdjusted ? "success" : "error"}
                                                                                                    variant={isAdjusted ? "filled" : "outlined"}
                                                                                                    sx={{ height: 20, fontSize: '0.65rem' }}
                                                                                                />
                                                                                            )}
                                                                                        </Box>
                                                                                    </Typography>

                                                                                    <Box sx={{ mt: 0.5, display: 'flex', alignItems: 'center', fontSize: '0.75rem', color: '#666' }}>
                                                                                        {isAdjusted ? (
                                                                                            <>
                                                                                                <span style={{ textDecoration: 'line-through', marginRight: '6px' }}>
                                                                                                    {comp.classes_attended}/{comp.classes_posted > 0 ? comp.classes_posted : comp.classes_conducted} ({comp.percentage.toFixed(1)}%)
                                                                                                </span>
                                                                                                <span style={{ marginRight: '6px' }}>→</span>
                                                                                                <strong style={{ color: '#4caf50' }}>
                                                                                                    {comp.adjusted_attended}/{comp.classes_posted > 0 ? comp.classes_posted : comp.classes_conducted} ({finalPct.toFixed(1)}%)
                                                                                                </strong>
                                                                                                <span style={{ color: '#1976d2', marginLeft: '4px' }}> (OD/ML used)</span>
                                                                                            </>
                                                                                        ) : (
                                                                                            <span style={{ color: comp.percentage < 65 ? '#d32f2f' : 'inherit' }}>
                                                                                                {comp.classes_attended}/{comp.classes_posted > 0 ? comp.classes_posted : comp.classes_conducted} ({comp.percentage.toFixed(1)}%)
                                                                                            </span>
                                                                                        )}
                                                                                    </Box>

                                                                                    {(comp.od_count > 0 || comp.ml_count > 0) && (
                                                                                        <Typography variant="caption" sx={{ display: 'block', mt: 0.2, color: isAdjusted ? '#2e7d32' : '#d32f2f', fontStyle: 'italic' }}>
                                                                                            OD: {comp.od_count} | ML: {comp.ml_count} {isAdjusted ? '(Applied)' : '(Not Eligible < 65%)'}
                                                                                        </Typography>
                                                                                    )}
                                                                                </Box>
                                                                            );
                                                                        })
                                                                    ) : (
                                                                        subject.combined_from?.map((code: string, i: number) => (
                                                                            <Typography key={i} variant="caption" sx={{ display: 'block', color: '#666', fontSize: '0.7rem' }}>
                                                                                {code}
                                                                            </Typography>
                                                                        ))
                                                                    )}

                                                                    <Typography variant="caption" sx={{ display: 'block', color: '#1976d2', fontSize: '0.7rem', mt: 0.5, fontStyle: 'italic' }}>
                                                                        Total: {subject.classes_attended}/{subject.classes_posted > 0 ? subject.classes_posted : subject.classes_conducted} | OD: {subject.od_count} | ML: {subject.ml_count}
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

                {
                    displayStudents.length === 0 && (
                        <Alert severity="info" sx={{ mt: 2 }}>
                            No students match the current filters
                        </Alert>
                    )
                }
            </Box>
            {mainTab === 1 && <ProformaDashboard uploadId={uploadId} selectedDepartment={selectedDepartment} />}
        </Box >
    );
};

export default AttendanceDashboard;
