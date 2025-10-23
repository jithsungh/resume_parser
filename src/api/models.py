"""
Pydantic models for API request/response validation
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class ProcessingStatus(str, Enum):
    """Status of async processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperienceEntry(BaseModel):
    """Single work experience entry"""
    company_name: Optional[str] = None
    role: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    duration_months: Optional[int] = None
    skills: List[str] = []


class ContactInfo(BaseModel):
    """Contact information"""
    name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    location: Optional[str] = None


class ResumeParseResult(BaseModel):
    """Complete resume parsing result"""
    name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    location: Optional[str] = None
    total_experience_years: float = 0.0
    primary_role: Optional[str] = None
    experiences: List[ExperienceEntry] = []
    filename: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata from smart parser
    error: Optional[str] = None  # Error message if parsing failed


class NEREntity(BaseModel):
    """Named Entity Recognition result"""
    word: str
    entity_group: str
    score: float
    start: Optional[int] = None
    end: Optional[int] = None


class NERResult(BaseModel):
    """NER extraction result"""
    entities: List[NEREntity]
    text_analyzed: str
    entity_count: int
    processing_time_seconds: Optional[float] = None


class SectionSegment(BaseModel):
    """Document section segment"""
    section_name: str
    content: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    confidence: Optional[float] = None


class SectionSegmentResult(BaseModel):
    """Section segmentation result"""
    sections: List[SectionSegment]
    total_sections: int
    filename: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata from smart parser


class BatchProcessRequest(BaseModel):
    """Batch processing request"""
    job_id: str = Field(..., description="Unique job identifier")
    process_ner: bool = Field(default=True, description="Run NER extraction")
    process_sections: bool = Field(default=False, description="Run section segmentation")


class BatchProcessStatus(BaseModel):
    """Batch processing status"""
    job_id: str
    status: ProcessingStatus
    total_files: int
    processed_files: int
    failed_files: int
    results: List[ResumeParseResult] = []
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    model_loaded: bool
    spacy_available: bool
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str


class BatchSegmentationRequest(BaseModel):
    """Batch segmentation debug request"""
    include_full_content: bool = Field(default=True, description="Include full section content in results")
    include_text_preview: bool = Field(default=True, description="Include text preview")


class SectionDebugInfo(BaseModel):
    """Detailed section information for debugging"""
    section_name: str
    content_length: int
    content_preview: Optional[str] = None
    full_content: Optional[str] = None
    line_count: int
    word_count: int


class FileSegmentationResult(BaseModel):
    """Segmentation result for a single file"""
    filename: str
    file_path: Optional[str] = None
    status: str  # 'success', 'error', 'empty'
    text_length: Optional[int] = None
    text_preview: Optional[str] = None
    sections_found: List[str] = []
    section_count: int
    sections: List[SectionDebugInfo] = []
    error: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class BatchSegmentationStatus(BaseModel):
    """Batch segmentation processing status"""
    job_id: str
    status: ProcessingStatus
    total_files: int
    processed_files: int
    failed_files: int
    empty_files: int
    results: List[FileSegmentationResult] = []
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None
