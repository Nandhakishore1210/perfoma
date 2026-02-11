import { useState } from 'react';
import { Container, Box, Typography, Paper, Stepper, Step, StepLabel } from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import FileUpload from './components/FileUpload/FileUpload';
import AttendanceDashboard from './components/Dashboard/AttendanceDashboard';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
});

function App() {
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [filename, setFilename] = useState<string>('');
  const [regulation, setRegulation] = useState<string>('U18');
  const [activeStep, setActiveStep] = useState(0);

  const handleUploadSuccess = (id: string, name: string, reg: string) => {
    setUploadId(id);
    setFilename(name);
    setRegulation(reg);
    setActiveStep(1);
  };

  const handleReset = () => {
    setUploadId(null);
    setFilename('');
    setRegulation('U18');
    setActiveStep(0);
  };

  const steps = ['Upload File', 'View Analysis'];

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: '100vh',
          bgcolor: 'background.default',
          py: 4,
        }}
      >
        <Container maxWidth="xl">
          {/* Header */}
          <Paper
            elevation={3}
            sx={{
              p: 4,
              mb: 4,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
            }}
          >
            <Typography variant="h3" gutterBottom fontWeight="bold">
              Faculty Proforma System
            </Typography>
            <Typography variant="h6">
              Automated Attendance Analysis & Reporting
            </Typography>
          </Paper>

          {/* Stepper */}
          <Paper sx={{ p: 3, mb: 4 }}>
            <Stepper activeStep={activeStep}>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>

          {/* Main Content */}
          <Paper sx={{ p: 4 }}>
            {activeStep === 0 && <FileUpload onUploadSuccess={handleUploadSuccess} />}

            {activeStep === 1 && uploadId && (
              <Box>
                <AttendanceDashboard uploadId={uploadId} filename={filename} regulation={regulation} />
                <Box sx={{ mt: 3, textAlign: 'center' }}>
                  <Typography
                    variant="body2"
                    color="primary"
                    sx={{ cursor: 'pointer', textDecoration: 'underline' }}
                    onClick={handleReset}
                  >
                    Upload Another File
                  </Typography>
                </Box>
              </Box>
            )}
          </Paper>

          {/* Footer */}
          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Automated Faculty Proforma System v1.0
            </Typography>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
