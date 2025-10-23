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
from ..smart_parser import smart_parse_resume
from .models import (
    ResumeParseResult, NERResult, SectionSegmentResult,
    ExperienceEntry, NEREntity, SectionSegment
)

# Optional imports - may not be available
try:
    from ..core.section_splitter import SectionSplitter
    SECTION_SPLITTER_AVAILABLE = True
except ImportError:
    SectionSplitter = None
    SECTION_SPLITTER_AVAILABLE = False


class ResumeParserService:
    """Service for resume parsing operations"""
    
    def __init__(self, model_path: str):
        """Initialize parser service"""
        self.model_path = model_path
        self.parser = None
        self.name_location_extractor = None
        self.section_splitter = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
    def initialize(self):
        """Initialize all components"""
        print("🚀 Initializing Resume Parser Service...")
        
        # Initialize main parser
        self.parser = CompleteResumeParser(self.model_path)
        
        # Initialize name/location extractor
        self.name_location_extractor = NameLocationExtractor()
        
        # Initialize section splitter
        if SECTION_SPLITTER_AVAILABLE:
            try:
                self.section_splitter = SectionSplitter()
                print("✅ Section splitter initialized")
            except Exception as e:
                print(f"⚠️  Section splitter initialization failed: {e}")
                self.section_splitter = None
        else:
            print("⚠️  Section splitter not available")
            self.section_splitter = None
        
        print("✅ Resume Parser Service initialized!\n")
    
    async def smart_parse_pdf_file(
        self,
        file_path: str,
        force_pipeline: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse PDF/DOCX using smart layout-aware parser
        
        Args:
            file_path: Path to PDF or DOCX file
            force_pipeline: Optional - force 'pdf' or 'ocr' pipeline
            
        Returns:
            Dictionary with:
            - sections: List of extracted sections with lines
            - metadata: Pipeline used, processing time, etc.
            - simplified: Simplified JSON output
        """
        start_time = time.time()
        
        # Run smart parser in thread pool (it's CPU intensive)
        loop = asyncio.get_event_loop()
        result, simplified, metadata = await loop.run_in_executor(
            self._executor,
            smart_parse_resume,
            file_path,
            force_pipeline,
            300,  # OCR DPI
            ['en'],  # Languages
            False  # verbose
        )
        
        processing_time = time.time() - start_time
        
        return {
            'result': result,
            'simplified': simplified,
            'metadata': {
                **metadata,
                'total_processing_time': round(processing_time, 2)
            }
        }
    
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
        file_path: str,
        smart_parser: bool = True
    ) -> ResumeParseResult:
        """
        Parse resume from file fewufjgv
        
        Args:
            file_path: Path to resume file
            smart_parser: Use smart layout-aware parser for PDFs/DOCX (recommended)
            
        Returns:
            ResumeParseResult with parsed information
        """
        file_ext = Path(file_path).suffix.lower()
        filename = Path(file_path).name
        
        # Use smart parser for PDFs and DOCX (recommended)
        if use_smart_parser and file_ext in ['.pdf', '.docx', '.doc']:
            try:
                # Use smart parser for better section extraction
                smart_result = await self.smart_parse_pdf_file(file_path, force_pipeline=None)
                
                # Extract structured data from smart parser output
                sections_dict = {}
                for section in smart_result['result'].get('sections', []):
                    section_name = section.get('section_name', 'Unknown')
                    lines = section.get('lines', [])
                    sections_dict[section_name] = '\n'.join(lines)
                
                # Combine all text for NER-based parsing
                all_text = '\n\n'.join(
                    f"=== {name} ===\n{content}" 
                    for name, content in sections_dict.items()
                )
                
                # Run NER-based parser on the text
                result = await self.parse_resume_text(all_text, filename)
                
                # Enhance result with smart parser metadata
                result.metadata = {
                    'smart_parser_used': True,
                    'pipeline_used': smart_result['metadata'].get('pipeline_used'),
                    'sections_detected': len(smart_result['result'].get('sections', [])),
                    'layout_complexity': smart_result['metadata'].get('layout_analysis', {}).get('layout_complexity'),
                    'num_columns': smart_result['metadata'].get('layout_analysis', {}).get('num_columns')
                }
                
                return result
                
            except Exception as e:
                # Fallback to legacy parser if smart parser fails
                print(f"⚠️ Smart parser failed, falling back to legacy parser: {e}")
                pass  # Continue to legacy parser below
        
        # Legacy parser (fallback or for TXT files)
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
    
    
    async def segment_sections_from_file(
        self,
        file_path: str,
        smart_parser: bool = True
    ) -> SectionSegmentResult:
        
        """
        Segment resume into sections from file with smart strategy selection.
        
        Strategy hierarchy (with fallbacks):
        1. Smart Parser (layout-aware, auto-selects PDF/OCR)
        2. Legacy PDF/DOCX extraction + section splitter
        3. Basic text extraction + rule-based segmentatio
        Args:
            file_path: Path to resume file (PDF, DOCX, TXT)
            smart_parser: Use smart layout-aware parser (recommended for PDF/DOCX)
            
        Returns:
            SectionSegmentResult with identified sections and metadata
        """
        start_time = time.time()
        file_ext = Path(file_path).suffix.lower()
        filename = Path(file_path).name
        
        strategy_used = "unknown"
        error_log = []
        
        # STRATEGY 1: Smart Parser (PDF/DOCX only)
        if smart_parser and file_ext in ['.pdf', '.docx', '.doc']:
            try:
                print(f"[Segmentation] Strategy 1: Trying smart parser for {filename}...")
                
                smart_result = await self.smart_parse_pdf_file(file_path, force_pipeline=None)
                
                # Check if smart parser actually found sections
                sections_found = smart_result['result'].get('sections', [])
                
                if len(sections_found) > 0:
                    print(f"[Segmentation] ✓ Smart parser succeeded: {len(sections_found)} sections")
                    
                    # Convert to SectionSegmentResult format
                    section_list = []
                    for section in sections_found:
                        section_name = section.get('section_name', 'Unknown')
                        lines = section.get('lines', [])
                        content = '\n'.join(lines)
                        
                        section_list.append(
                            SectionSegment(
                                section_name=section_name,
                                content=content,
                                confidence=None
                            )
                        )
                    
                    processing_time = time.time() - start_time
                    strategy_used = "smart_parser"
                    
                    return SectionSegmentResult(
                        sections=section_list,
                        total_sections=len(section_list),
                        filename=filename,
                        processing_time_seconds=round(processing_time, 2),
                        metadata={
                            'strategy_used': strategy_used,
                            'pipeline_used': smart_result['metadata'].get('pipeline_used'),
                            'layout_analysis': smart_result['metadata'].get('layout_analysis'),
                            'fallback_attempts': error_log
                        }
                    )
                else:
                    error_msg = "Smart parser returned 0 sections"
                    print(f"[Segmentation] ⚠️ {error_msg}")
                    error_log.append({'strategy': 'smart_parser', 'error': error_msg})
                    
            except Exception as e:
                error_msg = f"Smart parser failed: {str(e)}"
                print(f"[Segmentation] ⚠️ {error_msg}")
                error_log.append({'strategy': 'smart_parser', 'error': error_msg})
        
        # STRATEGY 2: Legacy extraction with dynamic thresholds
        print(f"[Segmentation] Strategy 2: Trying legacy extraction with section splitter...")
        
        try:
            # Extract text based on file type
            if file_ext == '.pdf':
                text = await self._extract_text_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                text = await self._extract_text_from_docx(file_path)
            elif file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Check if we got meaningful text
            if not text or len(text.strip()) < 50:
                error_msg = f"Insufficient text extracted ({len(text)} chars)"
                print(f"[Segmentation] ⚠️ {error_msg}")
                error_log.append({'strategy': 'legacy_extraction', 'error': error_msg})
                raise ValueError(error_msg)
            
            print(f"[Segmentation] ✓ Extracted {len(text)} chars, segmenting sections...")
            
            # Use section splitter with dynamic thresholds
            result = await self.segment_sections(text, filename)
            
            if result.total_sections > 0:
                print(f"[Segmentation] ✓ Legacy segmentation succeeded: {result.total_sections} sections")
                strategy_used = "legacy_extraction"
                
                # Add strategy metadata
                result.metadata = {
                    'strategy_used': strategy_used,
                    'text_length': len(text),
                    'fallback_attempts': error_log
                }
                
                return result
            else:
                error_msg = "Section splitter returned 0 sections"
                print(f"[Segmentation] ⚠️ {error_msg}")
                error_log.append({'strategy': 'legacy_extraction', 'error': error_msg})
                
        except Exception as e:
            error_msg = f"Legacy extraction failed: {str(e)}"
            print(f"[Segmentation] ⚠️ {error_msg}")
            error_log.append({'strategy': 'legacy_extraction', 'error': error_msg})
        
        # STRATEGY 3: Basic fallback - return whole document as one section
        print(f"[Segmentation] Strategy 3: Using basic fallback (whole document)")
        
        try:
            # Try to get any text we can
            if file_ext == '.pdf':
                text = await self._extract_text_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                text = await self._extract_text_from_docx(file_path)
            elif file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                text = ""
            
            processing_time = time.time() - start_time
            strategy_used = "basic_fallback"
            
            print(f"[Segmentation] ✓ Basic fallback: 1 section ({len(text)} chars)")
            
            return SectionSegmentResult(
                sections=[
                    SectionSegment(
                        section_name="Document",
                        content=text,
                        confidence=0.5
                    )
                ],
                total_sections=1,
                filename=filename,
                processing_time_seconds=round(processing_time, 2),
                metadata={
                    'strategy_used': strategy_used,
                    'text_length': len(text),
                    'fallback_attempts': error_log,
                    'warning': 'All segmentation strategies failed, returning whole document'
                }
            )
            
        except Exception as e:
            # Absolute last resort
            processing_time = time.time() - start_time
            error_msg = f"All strategies failed including basic fallback: {str(e)}"
            print(f"[Segmentation] ✗ {error_msg}")
            error_log.append({'strategy': 'basic_fallback', 'error': error_msg})
            
            return SectionSegmentResult(
                sections=[],
                total_sections=0,
                filename=filename,
                processing_time_seconds=round(processing_time, 2),
                metadata={
                    'strategy_used': 'failed',
                    'fallback_attempts': error_log,
                    'error': error_msg
                }
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
            'mobile': contact_info.get('mobile'),            'location': name_location.get('location')
        }
    
    async def batch_parse_resumes(
        self,
        file_info: List[Dict[str, str]],
        progress_callback=None
    ) -> List[ResumeParseResult]:
        """
        Parse multiple resumes in batch
        
        Args:
            file_info: List of dicts with 'path' and 'filename' keys
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of ResumeParseResult
        """
        results = []
        
        for idx, info in enumerate(file_info):
            file_path = info['path']
            filename = info['filename']  # Use original filename
            
            try:
                # Extract text based on file type
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext == '.pdf':
                    text = await self._extract_text_from_pdf(file_path)
                elif file_ext in ['.docx', '.doc']:
                    text = await self._extract_text_from_docx(file_path)
                elif file_ext == '.txt':
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
                  # Parse with original filename for name extraction heuristics
                result = await self.parse_resume_text(text, filename)
                results.append(result)
            except Exception as e:
                print(f"Error parsing {filename}: {e}")
                results.append(
                    ResumeParseResult(
                        filename=filename,
                        error=str(e)
                    )
                )
            
            if progress_callback:
                progress_callback(idx + 1, len(file_info))
        
        return results
    
    async def batch_segment_resumes(
        self,
        file_info: List[Dict[str, str]],
        include_full_content: bool = True,
        include_text_preview: bool = True,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Segment multiple resumes in batch for debugging
        
        Args:
            file_info: List of dicts with 'path' and 'filename' keys
            include_full_content: Include full section content
            include_text_preview: Include text preview
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of segmentation results
        """
        results = []
        
        for idx, info in enumerate(file_info):
            file_path = info['path']
            filename = info['filename']
            
            start_time = time.time()
            
            try:
                # Extract text from file
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext == '.pdf':
                    text = await self._extract_text_from_pdf(file_path)
                elif file_ext in ['.docx', '.doc']:
                    text = await self._extract_text_from_docx(file_path)
                elif file_ext == '.txt':
                    loop = asyncio.get_event_loop()
                    text = await loop.run_in_executor(
                        self._executor,
                        lambda: open(file_path, 'r', encoding='utf-8', errors='ignore').read()
                    )
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
                
                # Check if text is empty
                if not text or len(text.strip()) < 50:
                    result = {
                        'filename': filename,
                        'file_path': file_path,
                        'status': 'empty',
                        'error': 'File appears empty or too short',
                        'text_length': len(text) if text else 0,
                        'section_count': 0,
                        'sections_found': [],
                        'sections': [],
                        'processing_time_seconds': round(time.time() - start_time, 2)
                    }
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(idx + 1, len(file_info))
                    continue
                  # Segment the resume using proper PDF pipeline with layout analysis
                loop = asyncio.get_event_loop()
                
                # For PDFs, use the advanced PDF pipeline for accurate segmentation
                if file_ext == '.pdf':
                    from ..PDF_pipeline.get_words import get_words_from_pdf
                    from ..PDF_pipeline.split_columns import split_columns
                    from ..PDF_pipeline.get_lines import get_column_wise_lines
                    from ..PDF_pipeline.segment_sections import segment_sections_from_columns
                    
                    # Extract with layout analysis
                    def segment_pdf_with_layout(pdf_path):
                        pages = get_words_from_pdf(pdf_path)
                        columns = split_columns(pages, min_words_per_column=10, dynamic_min_words=True)
                        columns_with_lines = get_column_wise_lines(columns, y_tolerance=1.0)
                        result = segment_sections_from_columns(columns_with_lines)
                        
                        # Convert to dict format
                        segments = {}
                        for section in result.get('sections', []):
                            section_name = section.get('section', 'Unknown')
                            lines = section.get('lines', [])
                            content = '\n'.join(line.get('text', '') for line in lines)
                            segments[section_name] = content
                        return segments
                    
                    segments = await loop.run_in_executor(
                        self._executor,
                        segment_pdf_with_layout,
                        file_path
                    )
                elif self.section_splitter:
                    # For text/DOCX, use text-based segmentation
                    segments = await loop.run_in_executor(
                        self._executor,
                        self.section_splitter.split_sections,
                        text
                    )
                else:
                    # Fallback segmentation
                    segments = await loop.run_in_executor(
                        self._executor,
                        self._fallback_segment,
                        text
                    )
                
                # Format sections
                sections_info = []
                for section_name, content in segments.items():
                    section_data = {
                        'section_name': section_name,
                        'content_length': len(content),
                        'line_count': len(content.split('\n')) if content else 0,
                        'word_count': len(content.split()) if content else 0
                    }
                    
                    if include_text_preview:
                        preview = content[:300].replace('\n', ' ')[:200] if content else ''
                        section_data['content_preview'] = preview + '...' if len(preview) == 200 else preview
                    
                    if include_full_content:
                        section_data['full_content'] = content
                    
                    sections_info.append(section_data)
                
                # Create result
                result = {
                    'filename': filename,
                    'file_path': file_path,
                    'status': 'success',
                    'text_length': len(text),
                    'sections_found': list(segments.keys()),
                    'section_count': len(segments),
                    'sections': sections_info,
                    'processing_time_seconds': round(time.time() - start_time, 2)
                }
                
                if include_text_preview:
                    preview = text[:500].replace('\n', ' ')[:200]
                    result['text_preview'] = preview + '...' if len(preview) == 200 else preview
                
                results.append(result)
                
            except Exception as e:
                result = {
                    'filename': filename,
                    'file_path': file_path,
                    'status': 'error',
                    'error': str(e),
                    'section_count': 0,
                    'sections_found': [],
                    'sections': [],
                    'processing_time_seconds': round(time.time() - start_time, 2)
                }
                results.append(result)
            
            if progress_callback:
                progress_callback(idx + 1, len(file_info))
        
        return results
    
    def _fallback_segment(self, text: str) -> Dict[str, str]:
        """Basic fallback segmentation using pattern matching"""
        import re
        
        sections = {}
        
        # Common section patterns
        patterns = {
            'Experience': r'(?i)^(experience|employment|work history)',
            'Education': r'(?i)^(education|academic|qualification)',
            'Skills': r'(?i)^(skills|technical|expertise|competencies)',
            'Summary': r'(?i)^(summary|objective|profile|about)',
            'Projects': r'(?i)^(projects|portfolio)',
            'Certifications': r'(?i)^(certifications|certificates|licenses)'
        }
        
        lines = text.split('\n')
        current_section = 'Unsegmented'
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check if line is a section header
            matched_section = None
            for section_name, pattern in patterns.items():
                if re.match(pattern, line_stripped):
                    matched_section = section_name
                    break
            
            if matched_section:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                # Start new section
                current_section = matched_section
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    async def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            import PyPDF2
        except ImportError:
            raise ValueError("PyPDF2 not installed. Install with: pip install PyPDF2")
        
        try:
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
        except ImportError:
            raise ValueError("python-docx not installed. Install with: pip install python-docx")
        
        try:
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
