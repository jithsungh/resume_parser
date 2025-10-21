"""
FastAPI Routes for Resume Parsing
"""
import os
import time
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse

from .models import (
    ResumeParseResult, NERResult, SectionSegmentResult,
    BatchProcessStatus, ProcessingStatus, HealthCheckResponse,
    ErrorResponse, BatchSegmentationStatus
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


@router.post("/batch/segment", response_model=BatchSegmentationStatus)
async def batch_segment_sections(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Multiple resume files"),
    include_full_content: bool = Query(default=True, description="Include full section content"),
    include_text_preview: bool = Query(default=True, description="Include text preview")
):
    """
    Segment multiple resumes in batch for debugging (async processing)
    
    This endpoint helps debug segmentation issues by:
    - Processing multiple resumes and extracting sections
    - Showing section boundaries and content
    - Identifying files with no sections detected
    - Providing statistics about section detection
    
    Returns a job_id to track progress.
    Use GET /batch/segment/status/{job_id} to check progress
    Use GET /batch/segment/download/{job_id}?format=json to download results
    """
    if not parser_service:
        raise HTTPException(status_code=503, detail="Parser service not initialized")
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 files allowed per batch")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded files temporarily
    temp_file_info = []
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_file_info.append({
                'path': tmp_file.name,
                'filename': file.filename
            })
    
    # Initialize job status
    batch_jobs[job_id] = {
        'type': 'segmentation',
        'status': ProcessingStatus.PENDING,
        'total_files': len(temp_file_info),
        'processed_files': 0,
        'failed_files': 0,
        'empty_files': 0,
        'results': [],
        'started_at': datetime.utcnow().isoformat(),
        'completed_at': None,
        'error_message': None,
        'include_full_content': include_full_content,
        'include_text_preview': include_text_preview
    }
    
    # Add background task
    background_tasks.add_task(
        process_batch_segmentation_job,
        job_id,
        temp_file_info,
        include_full_content,
        include_text_preview
    )
    
    return BatchSegmentationStatus(
        job_id=job_id,
        status=ProcessingStatus.PENDING,
        total_files=len(temp_file_info),
        processed_files=0,
        failed_files=0,
        empty_files=0,
        started_at=datetime.utcnow().isoformat()
    )


@router.get("/batch/segment/status/{job_id}", response_model=BatchSegmentationStatus)
async def get_batch_segmentation_status(job_id: str):
    """
    Get status of batch segmentation job
    
    Returns current progress and results (if completed)
    """
    if job_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = batch_jobs[job_id]
    
    if job.get('type') != 'segmentation':
        raise HTTPException(status_code=400, detail="Job is not a segmentation job")
    
    # Calculate statistics if completed
    statistics = None
    if job['status'] == ProcessingStatus.COMPLETED:
        statistics = calculate_segmentation_statistics(job['results'])
    
    return BatchSegmentationStatus(
        job_id=job_id,
        status=job['status'],
        total_files=job['total_files'],
        processed_files=job['processed_files'],
        failed_files=job['failed_files'],
        empty_files=job.get('empty_files', 0),
        results=job['results'],
        error_message=job.get('error_message'),
        started_at=job['started_at'],
        completed_at=job.get('completed_at'),
        statistics=statistics
    )


@router.get("/batch/segment/download/{job_id}")
async def download_batch_segmentation_results(
    job_id: str,
    format: str = Query(default="json", regex="^(json|csv)$")
):
    """
    Download batch segmentation results
    
    Formats:
    - json: Detailed JSON with full section content
    - csv: CSV summary with section counts and previews
    """
    if job_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = batch_jobs[job_id]
    
    if job.get('type') != 'segmentation':
        raise HTTPException(status_code=400, detail="Job is not a segmentation job")
    
    if job['status'] != ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    import json
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    if format == "json":
        # Return JSON
        content = json.dumps(job['results'], indent=2, ensure_ascii=False)
        
        return StreamingResponse(
            io.BytesIO(content.encode('utf-8')),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=segmentation_{job_id}.json"
            }
        )
    
    elif format == "csv":
        # Convert to CSV
        output = io.StringIO()
        
        # Define CSV columns
        fieldnames = [
            'Filename', 'Status', 'Text Length', 'Section Count',
            'Sections Found', 'Error', 'Text Preview'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in job['results']:
            writer.writerow({
                'Filename': result.get('filename', ''),
                'Status': result.get('status', ''),
                'Text Length': result.get('text_length', 0),
                'Section Count': result.get('section_count', 0),
                'Sections Found': ', '.join(result.get('sections_found', [])),
                'Error': result.get('error', ''),
                'Text Preview': result.get('text_preview', '')[:200]
            })
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=segmentation_{job_id}.csv"
            }
        )


async def process_batch_segmentation_job(
    job_id: str, 
    file_info: List[Dict[str, str]],
    include_full_content: bool,
    include_text_preview: bool
):
    """Background task to process batch segmentation job"""
    job = batch_jobs[job_id]
    job['status'] = ProcessingStatus.PROCESSING
    
    try:
        results = await parser_service.batch_segment_resumes(
            file_info,
            include_full_content=include_full_content,
            include_text_preview=include_text_preview,
            progress_callback=lambda processed, total: job.update({'processed_files': processed})
        )
        
        job['results'] = results
        job['status'] = ProcessingStatus.COMPLETED
        job['completed_at'] = datetime.utcnow().isoformat()
        
        # Count failures and empty files
        job['failed_files'] = sum(1 for r in results if r.get('status') == 'error')
        job['empty_files'] = sum(1 for r in results if r.get('status') == 'empty')
        
    except Exception as e:
        job['status'] = ProcessingStatus.FAILED
        job['error_message'] = str(e)
        job['completed_at'] = datetime.utcnow().isoformat()
    
    finally:
        # Cleanup temp files
        for info in file_info:
            file_path = info['path']
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except:
                    pass


def calculate_segmentation_statistics(results: List[Dict]) -> Dict[str, Any]:
    """Calculate statistics from segmentation results"""
    total = len(results)
    success = sum(1 for r in results if r.get('status') == 'success')
    errors = sum(1 for r in results if r.get('status') == 'error')
    empty = sum(1 for r in results if r.get('status') == 'empty')
    
    # Section frequency
    section_counts = {}
    for result in results:
        for section in result.get('sections_found', []):
            section_counts[section] = section_counts.get(section, 0) + 1
    
    # Files with no sections
    no_sections = sum(1 for r in results if r.get('section_count', 0) == 0)
    
    return {
        'total_files': total,
        'successful': success,
        'errors': errors,
        'empty': empty,
        'no_sections_detected': no_sections,
        'section_frequency': section_counts,
        'most_common_sections': sorted(section_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    }


def set_parser_service(service: ResumeParserService):
    """Set the global parser service instance"""
    global parser_service
    parser_service = service
