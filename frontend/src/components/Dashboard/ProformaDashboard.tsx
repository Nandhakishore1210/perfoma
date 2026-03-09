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
    Button,
    TextField,
    MenuItem,
    Tab,
    Tabs,
    CircularProgress,
    Alert,
    Chip,
    Menu,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import {
    getProformaStudents, updateProformaEntry, uploadProof,
    approveStudent,
    generateProformaReport,
    downloadReport
} from '../../services/api';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import TableChartIcon from '@mui/icons-material/TableChart';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import DownloadIcon from '@mui/icons-material/Download';

interface ProformaDashboardProps {
    uploadId: string;
    selectedDepartment?: string;
}

const REASONS_1A = [
    "Medical Leave (Insufficient)",
    "Personal Reasons",
    "Other"
];

const ProformaDashboard: React.FC<ProformaDashboardProps> = ({ uploadId, selectedDepartment = 'all' }) => {
    const [tabValue, setTabValue] = useState(0);
    const [students1A, setStudents1A] = useState<any[]>([]); // Now holds subject-wise rows
    const [students1B, setStudents1B] = useState<any[]>([]); // Now holds subject-wise rows
    const [loading, setLoading] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [downloadAnchorEl, setDownloadAnchorEl] = useState<null | HTMLElement>(null);

    const handleOpenDownloadMenu = (event: React.MouseEvent<HTMLButtonElement>) => {
        setDownloadAnchorEl(event.currentTarget);
    };

    const handleCloseDownloadMenu = () => {
        setDownloadAnchorEl(null);
    };

    useEffect(() => {
        loadData();
    }, [uploadId, tabValue, selectedDepartment]);

    const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
            if (tabValue === 0) {
                const data = await getProformaStudents(uploadId, '1A', selectedDepartment);
                setStudents1A(data);
            } else {
                const data = await getProformaStudents(uploadId, '1B', selectedDepartment);
                setStudents1B(data);
            }
        } catch (err: any) {
            setError("Failed to load proforma data");
        } finally {
            setLoading(false);
        }
    };

    const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
        setTabValue(newValue);
    };

    const handleReasonChange = async (studentId: string, subjectCode: string, reason: string, type: '1A' | '1B') => {
        // Optimistic update
        const updateRow = (row: any) => {
            if (row.student_id === studentId && row.subject_code === subjectCode) {
                return { ...row, proforma_entry: { ...row.proforma_entry, reason } };
            }
            return row;
        };

        if (type === '1A') {
            setStudents1A(prev => prev.map(updateRow));
        } else {
            setStudents1B(prev => prev.map(updateRow));
        }

        try {
            await updateProformaEntry({
                upload_id: uploadId,
                student_id: studentId,
                subject_code: subjectCode,
                proforma_type: type,
                reason
            });
        } catch (err) {
            console.error("Failed to update reason", err);
            // Revert logic would go here
        }
    };

    const handleMoveTo1B = async (studentId: string, subjectCode: string) => {
        const key = `${studentId}-${subjectCode}`;
        setActionLoading(key);
        try {
            await updateProformaEntry({
                upload_id: uploadId,
                student_id: studentId,
                subject_code: subjectCode,
                proforma_type: '1B',
                status: 'Pending'
            });
            // Remove from 1A list locally
            setStudents1A(prev => prev.filter(s => !(s.student_id === studentId && s.subject_code === subjectCode)));
        } catch (err) {
            console.error("Failed to move to 1B", err);
        } finally {
            setActionLoading(null);
        }
    };

    const handleFileUpload = async (studentId: string, subjectCode: string, file: File) => {
        const key = `${studentId}-${subjectCode}`;
        setActionLoading(key);
        try {
            await uploadProof(uploadId, studentId, subjectCode, file);
            const path = URL.createObjectURL(file); // Temporary preview
            setStudents1B(prev => prev.map(s =>
                (s.student_id === studentId && s.subject_code === subjectCode)
                    ? { ...s, proforma_entry: { ...s.proforma_entry, proof_path: path } }
                    : s
            ));
            alert("File uploaded successfully");
        } catch (err) {
            console.error("Upload failed", err);
            alert("Upload failed");
        } finally {
            setActionLoading(null);
        }
    };

    const handleApprove = async (studentId: string, subjectCode: string) => {
        const key = `${studentId}-${subjectCode}`;
        setActionLoading(key);
        try {
            await approveStudent(uploadId, studentId, subjectCode);
            setStudents1B(prev => prev.map(s =>
                (s.student_id === studentId && s.subject_code === subjectCode)
                    ? { ...s, proforma_entry: { ...s.proforma_entry, status: 'Approved' } }
                    : s
            ));
        } catch (err) {
            console.error("Approval failed", err);
        } finally {
            setActionLoading(null);
        }
    };

    const handleDownload = async (format: 'pdf' | 'excel') => {
        setDownloading(true);
        try {
            const type = tabValue === 0 ? '1A' : '1B';
            const reportData = await generateProformaReport(uploadId, type, format, selectedDepartment);

            // Use the shared, working download endpoint
            const url = downloadReport(reportData.filename);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', reportData.filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Download failed", err);
            alert(`Failed to download ${format.toUpperCase()}`);
        } finally {
            setDownloading(false);
        }
    };

    return (
        <Box sx={{ width: '100%' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Tabs value={tabValue} onChange={handleTabChange} aria-label="proforma tabs">
                    <Tab label="Proforma 1A (< 65%)" />
                    <Tab label="Proforma 1B (65% - 74%)" />
                </Tabs>
                <Box sx={{ display: 'flex', gap: 1, mr: 2 }}>
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
                        <MenuItem onClick={() => { handleCloseDownloadMenu(); handleDownload('pdf'); }}>
                            <PictureAsPdfIcon sx={{ mr: 1, color: 'error.main' }} fontSize="small" />
                            Download PDF
                        </MenuItem>
                        <MenuItem onClick={() => { handleCloseDownloadMenu(); handleDownload('excel'); }}>
                            <TableChartIcon sx={{ mr: 1, color: 'success.main' }} fontSize="small" />
                            Download Excel
                        </MenuItem>
                    </Menu>
                </Box>
            </Box>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
            ) : (
                <>
                    {/* Proforma 1A Panel */}
                    <div role="tabpanel" hidden={tabValue !== 0}>
                        {tabValue === 0 && (
                            <TableContainer component={Paper}>
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Sl. No</TableCell>
                                            <TableCell>Register No.</TableCell>
                                            <TableCell>Name</TableCell>
                                            <TableCell>Subject</TableCell>
                                            <TableCell align="center">Attended</TableCell>
                                            <TableCell align="center">Conducted</TableCell>
                                            <TableCell align="center">Posted</TableCell>
                                            <TableCell>Attendance %</TableCell>
                                            <TableCell>Reason for not being eligible</TableCell>
                                            <TableCell>Action</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {students1A.length > 0 ? (
                                            students1A.map((row, index) => {
                                                const key = `${row.student_id}-${row.subject_code}`;
                                                return (
                                                    <TableRow key={key}>
                                                        <TableCell>{index + 1}</TableCell>
                                                        <TableCell>{row.student_id}</TableCell>
                                                        <TableCell>{row.student_name}</TableCell>
                                                        <TableCell>{row.subject_code} - {row.subject_name}</TableCell>
                                                        <TableCell align="center">{row.classes_attended}</TableCell>
                                                        <TableCell align="center">{row.classes_conducted}</TableCell>
                                                        <TableCell align="center">{row.classes_posted}</TableCell>
                                                        <TableCell>
                                                            <Typography
                                                                fontWeight="bold"
                                                                color={row.attendance_percentage < 65 ? 'error' : 'warning.main'}
                                                            >
                                                                {row.attendance_percentage.toFixed(2)}%
                                                            </Typography>
                                                        </TableCell>
                                                        <TableCell>
                                                            <TextField
                                                                select
                                                                size="small"
                                                                value={row.proforma_entry?.reason || ''}
                                                                onChange={(e) => handleReasonChange(row.student_id, row.subject_code, e.target.value, '1A')}
                                                                sx={{ minWidth: 200 }}
                                                                label="Select Reason"
                                                            >
                                                                {REASONS_1A.map((r) => (
                                                                    <MenuItem key={r} value={r}>{r}</MenuItem>
                                                                ))}
                                                            </TextField>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Button
                                                                variant="contained"
                                                                color="primary"
                                                                size="small"
                                                                endIcon={<ArrowForwardIcon />}
                                                                onClick={() => handleMoveTo1B(row.student_id, row.subject_code)}
                                                                disabled={actionLoading === key}
                                                            >
                                                                Move to 1B
                                                            </Button>
                                                        </TableCell>
                                                    </TableRow>
                                                );
                                            })
                                        ) : (
                                            <TableRow>
                                                <TableCell colSpan={10} align="center">No students found for Proforma 1A</TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        )}
                    </div>

                    {/* Proforma 1B Panel */}
                    <div role="tabpanel" hidden={tabValue !== 1}>
                        {tabValue === 1 && (
                            <TableContainer component={Paper}>
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Sl. No</TableCell>
                                            <TableCell>Register No.</TableCell>
                                            <TableCell>Name</TableCell>
                                            <TableCell>Subject</TableCell>
                                            <TableCell align="center">Attended</TableCell>
                                            <TableCell align="center">Conducted</TableCell>
                                            <TableCell align="center">Posted</TableCell>
                                            <TableCell>Attendance %</TableCell>
                                            <TableCell>Reason for Recommendation</TableCell>
                                            <TableCell>Proof</TableCell>
                                            <TableCell>Status</TableCell>
                                            <TableCell>Actions</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {students1B.length > 0 ? (
                                            students1B.map((row, index) => {
                                                const key = `${row.student_id}-${row.subject_code}`;
                                                return (
                                                    <TableRow key={key}>
                                                        <TableCell>{index + 1}</TableCell>
                                                        <TableCell>{row.student_id}</TableCell>
                                                        <TableCell>{row.student_name}</TableCell>
                                                        <TableCell>{row.subject_code} - {row.subject_name}</TableCell>
                                                        <TableCell align="center">{row.classes_attended}</TableCell>
                                                        <TableCell align="center">{row.classes_conducted}</TableCell>
                                                        <TableCell align="center">{row.classes_posted}</TableCell>
                                                        <TableCell>
                                                            <Typography
                                                                fontWeight="bold"
                                                                color={row.attendance_percentage < 65 ? 'error' : 'warning.main'}
                                                            >
                                                                {row.attendance_percentage.toFixed(2)}%
                                                            </Typography>
                                                        </TableCell>
                                                        <TableCell>
                                                            <TextField
                                                                size="small"
                                                                value={row.proforma_entry?.reason || ''}
                                                                onChange={(e) => handleReasonChange(row.student_id, row.subject_code, e.target.value, '1B')}
                                                                placeholder="Enter reason..."
                                                                sx={{ minWidth: 200 }}
                                                            />
                                                        </TableCell>
                                                        <TableCell>
                                                            <Button
                                                                component="label"
                                                                variant="outlined"
                                                                size="small"
                                                                startIcon={<CloudUploadIcon />}
                                                                disabled={actionLoading === key}
                                                            >
                                                                Upload
                                                                <input
                                                                    type="file"
                                                                    hidden
                                                                    onChange={(e) => e.target.files && handleFileUpload(row.student_id, row.subject_code, e.target.files[0])}
                                                                />
                                                            </Button>
                                                            {row.proforma_entry?.proof_path && (
                                                                <Typography variant="caption" display="block" color="success.main">
                                                                    File Uploaded
                                                                </Typography>
                                                            )}
                                                        </TableCell>
                                                        <TableCell>
                                                            <Chip
                                                                label={row.proforma_entry?.status || "Pending"}
                                                                color={row.proforma_entry?.status === "Approved" ? "success" : "warning"}
                                                                size="small"
                                                            />
                                                        </TableCell>
                                                        <TableCell>
                                                            {row.proforma_entry?.status !== "Approved" ? (
                                                                <Button
                                                                    variant="contained"
                                                                    color="success"
                                                                    size="small"
                                                                    startIcon={<CheckCircleIcon />}
                                                                    onClick={() => handleApprove(row.student_id, row.subject_code)}
                                                                    disabled={actionLoading === key}
                                                                >
                                                                    Approve
                                                                </Button>
                                                            ) : (
                                                                <Typography variant="body2" color="success.main">Approved</Typography>
                                                            )}
                                                        </TableCell>
                                                    </TableRow>
                                                );
                                            })
                                        ) : (
                                            <TableRow>
                                                <TableCell colSpan={12} align="center">No students found for Proforma 1B</TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        )}
                    </div>
                </>
            )}
        </Box>
    );
};

export default ProformaDashboard;
