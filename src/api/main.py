"""
FastAPI Application Entry Point
Resume Parser API Server
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

from .routes import router, set_parser_service
from .service import ResumeParserService
from .models import ErrorResponse


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("=" * 60)
    print("🚀 Starting Resume Parser API Server")
    print("=" * 60)
    
    # Get model path from environment or use default
    model_path = os.getenv('MODEL_PATH', './ml_model')
    
    if not os.path.exists(model_path):
        print(f"❌ Model path not found: {model_path}")
        print("   Please set MODEL_PATH environment variable or place model in ./ml_model")
    else:
        print(f"✅ Model path: {model_path}")
    
    # Initialize parser service
    service = ResumeParserService(model_path)
    service.initialize()
    set_parser_service(service)
    
    print("=" * 60)
    print("✅ Server started successfully!")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/api/v1/health")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("\n🛑 Shutting down Resume Parser API Server...")
    service.cleanup()
    print("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Resume Parser API",
    description="""
    Advanced Resume Parsing API with NER and Section Segmentation
    
    ## Features
    
    * **Single Resume Parsing**: Parse individual resume files (PDF, DOCX, TXT)
    * **Batch Processing**: Process multiple resumes asynchronously
    * **NER Extraction**: Extract named entities (companies, roles, dates, skills)
    * **Section Segmentation**: Identify and extract resume sections
    * **Contact Extraction**: Quick extraction of contact information
    
    ## Supported Formats
    
    * PDF (.pdf)
    * Microsoft Word (.docx, .doc)
    * Plain Text (.txt)
    
    ## Extracted Information
    
    * Name, Email, Mobile, Location
    * Total Years of Experience
    * Primary Role
    * Detailed Work History with:
        - Company Names
        - Job Roles
        - Employment Dates
        - Skills/Technologies
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )


# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Resume Parser"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "message": "Resume Parser API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
