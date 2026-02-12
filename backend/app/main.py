"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import upload, analysis

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
    # Continue startup even if DB fails, though API calls might fail later


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """API health check"""
    return {"status": "healthy", "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
