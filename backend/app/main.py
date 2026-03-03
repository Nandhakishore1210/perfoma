from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.routes import upload, analysis, proforma
import os
import sys

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Automated Faculty Proforma/Attendance Analysis System",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Create database tables
from app.core.database import engine
from app.models import sql_models
import logging

logger = logging.getLogger(__name__)

try:
    sql_models.Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Simplified for standalone exe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(proforma.router, prefix="/api", tags=["Proforma"])

# Serve frontend static files
# When bundled with PyInstaller, the frontend files will be in a directory 
# defined by sys._MEIPASS or relative to the executable.
def get_frontend_path():
    if getattr(sys, 'frozen', False):
        # In --onedir with --contents-directory, _MEIPASS usually points 
        # to the directory containing the files.
        base_path = sys._MEIPASS
    else:
        # Running in development
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Try multiple common locations to be safe
    paths_to_check = [
        os.path.join(base_path, "frontend", "dist"),
        os.path.join(base_path, "internal", "frontend", "dist"),
    ]
    
    for p in paths_to_check:
        if os.path.exists(p):
            return p
            
    return paths_to_check[0] # Fallback

frontend_path = get_frontend_path()

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {"message": "Frontend not found, but API is running", "path": frontend_path}

@app.get("/api/health")
async def health_check():
    """API health check"""
    return {"status": "healthy", "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open("http://127.0.0.1:8000")

    # Only open browser if we're not in reload mode
    if not settings.DEBUG or os.environ.get("RUN_BROWSER"):
        Timer(1.5, open_browser).start()

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=settings.DEBUG)
