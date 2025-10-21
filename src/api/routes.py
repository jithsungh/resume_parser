"""
FastAPI Routes for Resume Parsing
"""
import os
import time
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from .models import (
    ResumeParseResult, NERResult, SectionSegmentResult,
    BatchProcessStatus, ProcessingStatus, HealthCheckResponse,
    ErrorResponse
)
from .service import ResumeParserService


# Initialize router
router = APIRouter()

# Global service instance (will be initialized on startup)
parser_service: Optional[ResumeParserService] = None

# In-memory job storage (in production, use Redis or database)
batch_jobs = {}


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns service status and model availability
    """
    return HealthCheckResponse(
        status="healthy" if parser_service else "initializing",
        version="1.0.0",
        model_loaded=parser_service is not None and parser_service.parser is not None,
        spacy_available=parser_service is not None and 
                       parser_service.name_location_extractor is not None and
                       parser_service.name_location_extractor.spacy_available,
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/parse/single", response_model=ResumeParseResult)
async def parse_single_resume(
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, TXT)")
):
    """
    Parse a single resume file
    
    Extracts:
    - Contact information (name, email, mobile, location)
    - Work experience history
    - Total years of experience
    - Primary role
    - Skills from each experience
    
    Supports: PDF, DOCX, TXT files
    """
    if not parser_service:
        raise HTTPException(status_code=503, detail="Parser service not initialized")
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Parse the resume
        result = await parser_service.parse_resume_file(tmp_file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


@router.post("/parse/text", response_model=ResumeParseResult)
async def parse_resume_text(
    text: str,
    filename: Optional[str] = None
):
    """
    Parse resume from raw text
    
    Useful when you already have extracted text from a file
    or want to test with text directly
    """
    if not parser_service:
        raise HTTPException(status_code=503, detail="Parser service not initialized")
    
    if not text or len(text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short or empty")
    
    try:
        result = await parser_service.parse_resume_text(text, filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing text: {str(e)}")


@router.post("/ner/extract", response_model=NERResult)
async def extract_entities(
    text: str = Query(..., description="Text to extract entities from", min_length=10)
):
    """
    Extract named entities using NER model
    
    Extracts:
    - COMPANY names
    - JOB ROLES
    - DATES
    - TECHNOLOGIES/SKILLS
    
    Returns entities with confidence scores
    """
    if not parser_service:
        raise HTTPException(status_code=503, detail="Parser service not initialized")
    
    try:
        result = await parser_service.extract_ner_entities(text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting entities: {str(e)}")


@router.post("/sections/segment", response_model=SectionSegmentResult)
async def segment_sections(
    file: UploadFile = File(None, description="Resume file (optional)"),
    text: Optional[str] = None,
    filename: Optional[str] = None
):
    """
    Segment resume into sections
    
    Identifies and extracts sections like:
    - Personal Information
    - Summary/Objective
    - Work Experience
    - Education
    - Skills
    - Certifications
    - Projects
    
    Can accept either a file or raw text
    """
    if not parser_service:
        raise HTTPException(status_code=503, detail="Parser service not initialized")
    
    if not parser_service.section_splitter:
        raise HTTPException(status_code=503, detail="Section splitter not available")
    
    # Get text from file or direct input
    if file:
        file_ext = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Extract text from file
            if file_ext == '.pdf':
                text = await parser_service._extract_text_from_pdf(tmp_file_path)
            elif file_ext in ['.docx', '.doc']:
                text = await parser_service._extract_text_from_docx(tmp_file_path)
            elif file_ext == '.txt':
                with open(tmp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            
            filename = file.filename
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    elif text:
        if len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Text too short")
    else:
        raise HTTPException(status_code=400, detail="Either file or text must be provided")
    
    try:
        result = await parser_service.segment_sections(text, filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error segmenting sections: {str(e)}")


@router.post("/contact/extract")
async def extract_contact_info(
    file: UploadFile = File(None, description="Resume file (optional)"),
    text: Optional[str] = None
):
    """
    Extract only contact information
    
    Fast endpoint for extracting:
    - Name
    - Email
    - Mobile number
    - Location
    
    Can accept either a file or raw text
    """
    if not parser_service:
        raise HTTPException(status_code=503, detail="Parser service not initialized")
    
    # Get text from file or direct input
    filename = None
    if file:
        file_ext = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Extract text from file
            if file_ext == '.pdf':
                text = await parser_service._extract_text_from_pdf(tmp_file_path)
            elif file_ext in ['.docx', '.doc']:
                text = await parser_service._extract_text_from_docx(tmp_file_path)
            elif file_ext == '.txt':
                with open(tmp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            
            filename = file.filename
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    elif text:
        if len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Text too short")
    else:
        raise HTTPException(status_code=400, detail="Either file or text must be provided")
    
    try:
        result = await parser_service.extract_contact_info(text, filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting contact info: {str(e)}")


@router.post("/batch/parse", response_model=BatchProcessStatus)
async def batch_parse_resumes(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Multiple resume files")
):
    """
    Parse multiple resumes in batch (async processing)
    
    Uploads multiple files and processes them in the background.
    Returns a job_id to track progress.
    
    Use GET /batch/status/{job_id} to check progress
    """
    if not parser_service:
        raise HTTPException(status_code=503, detail="Parser service not initialized")
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files allowed per batch")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded files temporarily
    temp_files = []
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_files.append(tmp_file.name)
    
    # Initialize job status
    batch_jobs[job_id] = {
        'status': ProcessingStatus.PENDING,
        'total_files': len(temp_files),
        'processed_files': 0,
        'failed_files': 0,
        'results': [],
        'started_at': datetime.utcnow().isoformat(),
        'completed_at': None,
        'error_message': None
    }
    
    # Add background task
    background_tasks.add_task(
        process_batch_job,
        job_id,
        temp_files
    )
    
    return BatchProcessStatus(
        job_id=job_id,
        status=ProcessingStatus.PENDING,
        total_files=len(temp_files),
        processed_files=0,
        failed_files=0,
        started_at=datetime.utcnow().isoformat()
    )


@router.get("/batch/status/{job_id}", response_model=BatchProcessStatus)
async def get_batch_status(job_id: str):
    """
    Get status of batch processing job
    
    Returns current progress and results (if completed)
    """
    if job_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = batch_jobs[job_id]
    
    return BatchProcessStatus(
        job_id=job_id,
        status=job['status'],
        total_files=job['total_files'],
        processed_files=job['processed_files'],
        failed_files=job['failed_files'],
        results=job['results'],
        error_message=job.get('error_message'),
        started_at=job['started_at'],
        completed_at=job.get('completed_at')
    )


async def process_batch_job(job_id: str, file_paths: List[str]):
    """Background task to process batch job"""
    job = batch_jobs[job_id]
    job['status'] = ProcessingStatus.PROCESSING
    
    try:
        def progress_callback(processed, total):
            job['processed_files'] = processed
        
        results = await parser_service.batch_parse_resumes(
            file_paths,
            progress_callback=progress_callback
        )
        
        job['results'] = results
        job['status'] = ProcessingStatus.COMPLETED
        job['completed_at'] = datetime.utcnow().isoformat()
        
        # Count failures
        job['failed_files'] = sum(1 for r in results if hasattr(r, 'error'))
        
    except Exception as e:
        job['status'] = ProcessingStatus.FAILED
        job['error_message'] = str(e)
        job['completed_at'] = datetime.utcnow().isoformat()
    
    finally:
        # Cleanup temp files
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except:
                    pass


def set_parser_service(service: ResumeParserService):
    """Set the global parser service instance"""
    global parser_service
    parser_service = service
