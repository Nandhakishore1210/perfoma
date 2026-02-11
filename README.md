# Automated Faculty Proforma System

A modern, extensible system for automated attendance analysis and reporting for faculty members.

## 🚀 Features

- **📊 Intelligent Attendance Processing**
  - Automatically combines Theory (T) and Lab (L) subjects
  - OD/ML adjustment for students below 75%
  - Smart categorization: Critical (<65%), Danger (65-75%), Border (75-80%), Safe (≥80%)

- **📁 Multi-Format Support**
  - Excel (.xlsx, .xls)
  - PDF parsing
  - Flexible column detection

- **📈 Visual Analytics**
  - Category distribution charts
  - Student-wise detailed reports
  - Subject-wise analysis

- **📥 Comprehensive Reports**
  - Downloadable Excel reports with formatting
  - Color-coded categories
  - Summary statistics

- **🎨 Modern UI**
  - Drag-and-drop file upload
  - Real-time analysis
  - Responsive Material-UI design

## 🏗️ Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **Pandas** - Excel data processing
- **PDFPlumber** - PDF parsing
- **Pydantic** - Data validation
- **XlsxWriter** - Report generation

### Frontend
- **React 18** + **TypeScript**
- **Material-UI (MUI)** - Component library
- **Recharts** - Data visualization
- **React Dropzone** - File uploads
- **Axios** - API communication

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

## 🛠️ Installation & Setup

### Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the server
python -m app.main
```

Backend will run on `http://localhost:8000`

API Documentation available at: `http://localhost:8000/api/docs`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will run on `http://localhost:5173`

## 🐳 Docker Setup (Recommended for Production)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

## 🌐 Deployment

### Deploy to Render (Free, Global Access)

Your app can be deployed globally for **completely free** on Render.

📖 **[Full Deployment Guide →](DEPLOYMENT.md)**

**Quick Deploy:**
1. Push code to GitHub
2. Create Render account (free)
3. Deploy using `render.yaml` configuration
4. Your app will be live globally in ~10 minutes!

**What you get:**
- ✅ Global CDN
- ✅ Auto-deploy from Git
- ✅ Free HTTPS
- ✅ Free PostgreSQL (if needed)

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions.



## 📖 Usage Guide

### 1. Upload Attendance File

- Prepare an Excel or PDF file with the following columns:
  - Student ID / Roll No
  - Student Name (optional)
  - Subject Code (e.g., CS301T, CS301L)
  - Subject Name (optional)
  - Classes Conducted
  - Classes Attended
  - OD (On Duty) - optional
  - ML (Medical Leave) - optional

- Drag and drop or click to upload the file

### 2. View Analysis

The system will automatically:
- Combine Theory and Lab subjects (e.g., CS301T + CS301L → CS301)
- Calculate attendance percentages
- Apply OD/ML adjustments if attendance < 75%
- Categorize students by risk level

### 3. Download Reports

- Click "Download Report" to get a formatted Excel file
- Includes detailed breakdown and summary statistics
- Color-coded by category

## 📊 Sample Data

Sample attendance data is provided in `sample_data/attendance_sample.csv`

## 🔧 Configuration

### Attendance Rules

Edit `backend/app/core/rules.py` to customize:
- Category thresholds
- OD/ML adjustment rules
- Subject code patterns

### Backend Settings

Edit `backend/.env`:
```env
# File Upload
MAX_FILE_SIZE=10485760  # 10MB

# Attendance Rules
OD_ML_THRESHOLD=75
ENABLE_OD_ML_ADJUSTMENT=True
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm test
```

## 🔌 API Endpoints

### Upload
- `POST /api/upload` - Upload attendance file

### Analysis
- `POST /api/analyze/{upload_id}` - Process attendance
- `GET /api/analysis/{upload_id}` - Get analysis results
- `GET /api/summary/{upload_id}` - Get quick summary

### Reports
- `POST /api/reports/generate` - Generate report
- `GET /api/reports/download/{filename}` - Download report

Full API documentation: `http://localhost:8000/api/docs`

## 🚀 Future Enhancements

The system is designed for easy extensibility:

- [ ] SMS/Email alerts for critical attendance
- [ ] Student login portal
- [ ] Department-wise custom rules
- [ ] Semester-wise comparison
- [ ] AI-based risk prediction
- [ ] Bulk file processing
- [ ] Real-time notifications
- [ ] Mobile app

## 📁 Project Structure

```
perfoma/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── sample_data/
└── docker-compose.yml
```

## 📝 License

MIT License

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues and questions, please create an issue in the repository.

---

Built with ❤️ for educational institutions
