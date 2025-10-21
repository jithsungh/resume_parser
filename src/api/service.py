"""
Service layer for resume parsing operations
Handles business logic and coordination between parsers
"""
import os
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.complete_resume_parser import CompleteResumeParser
from ..core.name_location_extractor import NameLocationExtractor
from ..core.section_splitter import SectionSplitter
from ..PDF_pipeline.pipeline import PDFPipeline
from .models import (
    ResumeParseResult, NERResult, SectionSegmentResult,
    ExperienceEntry, NEREntity, SectionSegment
)


class ResumeParserService:
    """Service for resume parsing operations"""
    
    def __init__(self, model_path: str):
        """Initialize parser service"""
        self.model_path = model_path
        self.parser = None
        self.name_location_extractor = None
        self.section_splitter = None
        self.pdf_pipeline = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
    def initialize(self):
        """Initialize all components"""
        print("🚀 Initializing Resume Parser Service...")
        
        # Initialize main parser
        self.parser = CompleteResumeParser(self.model_path)
        
        # Initialize name/location extractor
        self.name_location_extractor = NameLocationExtractor()
        
        # Initialize section splitter
        try:
            self.section_splitter = SectionSplitter()
            print("✅ Section splitter initialized")
        except Exception as e:
            print(f"⚠️  Section splitter not available: {e}")
            self.section_splitter = None
        
        # Initialize PDF pipeline
        try:
            self.pdf_pipeline = PDFPipeline()
            print("✅ PDF pipeline initialized")
        except Exception as e:
            print(f"⚠️  PDF pipeline not available: {e}")
            self.pdf_pipeline = None
        
        print("✅ Resume Parser Service initialized!\n")
    
    async def parse_resume_text(
        self, 
        text: str, 
        filename: Optional[str] = None
    ) -> ResumeParseResult:
        """
        Parse resume from text
        
        Args:
            text: Resume text content
            filename: Optional filename for context
            
        Returns:
            ResumeParseResult with parsed information
        """
        start_time = time.time()
        
        # Run parser in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self.parser.parse_resume,
            text,
            filename
        )
        
        processing_time = time.time() - start_time
        
        # Convert to API model
        return ResumeParseResult(
            name=result.get('name'),
            email=result.get('email'),
            mobile=result.get('mobile'),
            location=result.get('location'),
            total_experience_years=result.get('total_experience_years', 0.0),
            primary_role=result.get('primary_role'),
            experiences=[
                ExperienceEntry(**exp) for exp in result.get('experiences', [])
            ],
            filename=filename,
            processing_time_seconds=round(processing_time, 2)
        )
    
    async def parse_resume_file(
        self, 
        file_path: str
    ) -> ResumeParseResult:
        """
        Parse resume from file
        
        Args:
            file_path: Path to resume file
            
        Returns:
            ResumeParseResult with parsed information
        """
        # Extract text based on file type
        file_ext = Path(file_path).suffix.lower()
        filename = Path(file_path).name
        
        if file_ext == '.pdf':
            text = await self._extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            text = await self._extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        return await self.parse_resume_text(text, filename)
    
    async def extract_ner_entities(
        self, 
        text: str
    ) -> NERResult:
        """
        Extract named entities from text
        
        Args:
            text: Text to analyze
            
        Returns:
            NERResult with extracted entities
        """
        start_time = time.time()
        
        # Run NER in thread pool
        loop = asyncio.get_event_loop()
        entities = await loop.run_in_executor(
            self._executor,
            self.parser.ner_pipeline,
            text
        )
        
        processing_time = time.time() - start_time
        
        # Convert to API model
        return NERResult(
            entities=[
                NEREntity(
                    word=ent['word'],
                    entity_group=ent['entity_group'],
                    score=ent['score'],
                    start=ent.get('start'),
                    end=ent.get('end')
                )
                for ent in entities
            ],
            text_analyzed=text[:500] + "..." if len(text) > 500 else text,
            entity_count=len(entities),
            processing_time_seconds=round(processing_time, 2)
        )
    
    async def segment_sections(
        self, 
        text: str,
        filename: Optional[str] = None
    ) -> SectionSegmentResult:
        """
        Segment resume into sections
        
        Args:
            text: Resume text
            filename: Optional filename
            
        Returns:
            SectionSegmentResult with identified sections
        """
        start_time = time.time()
        
        if not self.section_splitter:
            raise ValueError("Section splitter not available")
        
        # Run section splitting in thread pool
        loop = asyncio.get_event_loop()
        sections = await loop.run_in_executor(
            self._executor,
            self.section_splitter.split_sections,
            text
        )
        
        processing_time = time.time() - start_time
        
        # Convert to API model
        section_list = []
        for section_name, content in sections.items():
            section_list.append(
                SectionSegment(
                    section_name=section_name,
                    content=content,
                    confidence=None
                )
            )
        
        return SectionSegmentResult(
            sections=section_list,
            total_sections=len(section_list),
            filename=filename,
            processing_time_seconds=round(processing_time, 2)
        )
    
    async def extract_contact_info(
        self, 
        text: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract only contact information
        
        Args:
            text: Resume text
            filename: Optional filename
            
        Returns:
            Dictionary with contact information
        """
        loop = asyncio.get_event_loop()
        
        # Extract contact info
        contact_info = await loop.run_in_executor(
            self._executor,
            self.parser._extract_contact_info,
            text
        )
        
        # Extract name and location
        name_location = await loop.run_in_executor(
            self._executor,
            self.name_location_extractor.extract_name_and_location,
            text,
            filename,
            contact_info.get('email')
        )
        
        return {
            'name': name_location.get('name'),
            'email': contact_info.get('email'),
            'mobile': contact_info.get('mobile'),
            'location': name_location.get('location')
        }
    
    async def batch_parse_resumes(
        self,
        file_paths: List[str],
        progress_callback=None
    ) -> List[ResumeParseResult]:
        """
        Parse multiple resumes in batch
        
        Args:
            file_paths: List of file paths
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of ResumeParseResult
        """
        results = []
        
        for idx, file_path in enumerate(file_paths):
            try:
                result = await self.parse_resume_file(file_path)
                results.append(result)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                results.append(
                    ResumeParseResult(
                        filename=Path(file_path).name,
                        error=str(e)
                    )
                )
            
            if progress_callback:
                progress_callback(idx + 1, len(file_paths))
        
        return results
    
    async def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            import PyPDF2
            loop = asyncio.get_event_loop()
            
            def extract():
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                return text
            
            return await loop.run_in_executor(self._executor, extract)
        except Exception as e:
            raise ValueError(f"Error extracting PDF text: {e}")
    
    async def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            from docx import Document
            loop = asyncio.get_event_loop()
            
            def extract():
                doc = Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            
            return await loop.run_in_executor(self._executor, extract)
        except Exception as e:
            raise ValueError(f"Error extracting DOCX text: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        self._executor.shutdown(wait=True)
