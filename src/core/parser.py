"""
Core Parser Engine
==================
Unified resume parsing pipeline with automatic fallback strategies.
Handles PDF, DOCX, and scanned documents with intelligent routing.
"""

import time
import json
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path
from enum import Enum


class ParserStrategy(Enum):
    """Available parsing strategies"""
    PDF_NATIVE = "pdf_native"
    PDF_HISTOGRAM = "pdf_histogram"
    PDF_REGION_BASED = "pdf_region"
    OCR_EASYOCR = "ocr_easyocr"
    DOCX_NATIVE = "docx_native"


class ParsingResult:
    """Structured parsing result with metadata"""
    
    def __init__(self):
        self.success: bool = False
        self.strategy_used: Optional[ParserStrategy] = None
        self.data: Dict[str, Any] = {}
        self.simplified_json: str = "[]"
        self.processing_time: float = 0.0
        self.attempts: List[Dict[str, Any]] = []
        self.quality_score: float = 0.0
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy_used.value if self.strategy_used else None,
            "data": self.data,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "warnings": self.warnings,
            "errors": self.errors,
            "attempts": len(self.attempts)
        }


class ResumeParser:
    """
    Unified resume parser with automatic strategy selection.
    
    Strategies (in order of preference):
    1. PDF Native (fast, works for clean single-column PDFs)
    2. PDF Histogram (handles multi-column layouts)
    3. PDF Region-based (handles hybrid layouts with horizontal separators)
    4. OCR (for scanned documents)
    5. DOCX (for Word documents)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize parser with optional config.
        
        Args:
            config_path: Path to sections_database.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "sections_database.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load section mapping configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            return {"sections": {}, "learning": {"new_sections_discovered": [], "false_positives": []}}
    
    def detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension"""
        suffix = Path(file_path).suffix.lower()
        if suffix == '.pdf':
            return 'pdf'
        elif suffix in ['.docx', '.doc']:
            return 'docx'
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def analyze_pdf_layout(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze PDF layout characteristics.
        
        Returns:
            - is_scanned: bool
            - has_text_layer: bool
            - num_columns: int (1, 2, 3+)
            - has_regions: bool (hybrid layout)
            - page_count: int
        """
        import fitz
        from src.PDF_pipeline.region_detector import detect_page_regions
        
        try:
            pdf_path = str(Path(pdf_path).resolve())
            doc = fitz.open(pdf_path)
            
            analysis = {
                'is_scanned': False,
                'has_text_layer': True,
                'num_columns': 1,
                'has_regions': False,
                'page_count': len(doc)
            }
            
            if len(doc) == 0:
                doc.close()
                analysis['is_scanned'] = True
                return analysis
            
            # Check first page
            page = doc[0]
            text = page.get_text().strip()
            
            # Scanned check
            if len(text) < 50:
                analysis['is_scanned'] = True
                analysis['has_text_layer'] = False
                doc.close()
                return analysis
            
            # Get words for layout analysis
            words = page.get_text("words")
            
            # Column detection
            if len(words) >= 20:
                x_positions = [w[0] for w in words]
                x_positions.sort()
                page_width = page.rect.width
                mid_x = page_width / 2
                
                left_count = sum(1 for x in x_positions if x < mid_x)
                right_count = sum(1 for x in x_positions if x >= mid_x)
                
                if left_count > 10 and right_count > 10:
                    ratio = min(left_count, right_count) / max(left_count, right_count)
                    if ratio > 0.25:
                        analysis['num_columns'] = 2
            
            # Region detection (hybrid layout check)
            try:
                from src.PDF_pipeline.get_words import get_words_from_pdf
                pages = get_words_from_pdf(pdf_path)
                if pages:
                    regions = detect_page_regions(pages[0])
                    if len(regions) > 1:
                        analysis['has_regions'] = True
            except Exception:
                pass
            
            doc.close()
            return analysis
            
        except Exception as e:
            print(f"Warning: Layout analysis failed: {e}")
            return {
                'is_scanned': False,
                'has_text_layer': True,
                'num_columns': 1,
                'has_regions': False,
                'page_count': 1
            }
    
    def calculate_quality_score(self, result: Dict[str, Any]) -> float:
        """
        Calculate quality score (0-100) based on extraction results.
        
        Factors:
        - Number of sections found (40 points)
        - Total lines extracted (30 points)
        - Contact info completeness (20 points)
        - Text coherence (10 points)
        """
        score = 0.0
        
        sections = result.get('sections', [])
        num_sections = len(sections)
        
        # Sections (max 40 points)
        if num_sections >= 5:
            score += 40
        elif num_sections >= 3:
            score += 30
        elif num_sections >= 1:
            score += 15
        
        # Lines (max 30 points)
        total_lines = sum(len(s.get('lines', [])) for s in sections)
        if total_lines >= 30:
            score += 30
        elif total_lines >= 15:
            score += 20
        elif total_lines >= 5:
            score += 10
        
        # Contact info (max 20 points)
        contact = result.get('contact', {})
        if contact.get('email'):
            score += 7
        if contact.get('phone'):
            score += 7
        if contact.get('name'):
            score += 6
        
        # Text coherence (max 10 points)
        # Check for suspiciously long lines (indicates jumbled text)
        has_jumbled = False
        for section in sections:
            for line in section.get('lines', []):
                if len(line) > 500:
                    has_jumbled = True
                    break
            if has_jumbled:
                break
        
        if not has_jumbled:
            score += 10
        else:
            score += 5  # Partial credit
        
        return min(100.0, score)
    
    def parse(
        self,
        file_path: str,
        force_strategy: Optional[ParserStrategy] = None,
        verbose: bool = False
    ) -> ParsingResult:
        """
        Parse resume with automatic strategy selection.
        
        Args:
            file_path: Path to resume file
            force_strategy: Force specific parsing strategy
            verbose: Print detailed progress
            
        Returns:
            ParsingResult object
        """
        from src.PDF_pipeline.pipeline import run_pipeline as run_pdf_pipeline
        from src.IMG_pipeline.pipeline import run_pipeline_ocr
        
        start_time = time.time()
        result = ParsingResult()
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"Resume Parser: {Path(file_path).name}")
            print(f"{'='*70}")
        
        try:
            # Detect file type
            file_type = self.detect_file_type(file_path)
            
            if file_type == 'docx':
                result.errors.append("DOCX parsing not yet implemented")
                return result
            
            # Analyze PDF layout
            layout = self.analyze_pdf_layout(file_path)
            
            if verbose:
                print(f"Layout Analysis:")
                print(f"  Scanned: {layout['is_scanned']}")
                print(f"  Columns: {layout['num_columns']}")
                print(f"  Regions: {layout['has_regions']}")
                print(f"  Pages: {layout['page_count']}")
            
            # Strategy selection
            if force_strategy:
                strategies = [force_strategy]
            elif layout['is_scanned']:
                strategies = [ParserStrategy.OCR_EASYOCR]
            elif layout['has_regions']:
                strategies = [
                    ParserStrategy.PDF_REGION_BASED,
                    ParserStrategy.PDF_HISTOGRAM,
                    ParserStrategy.OCR_EASYOCR
                ]
            elif layout['num_columns'] >= 2:
                strategies = [
                    ParserStrategy.PDF_HISTOGRAM,
                    ParserStrategy.PDF_REGION_BASED,
                    ParserStrategy.OCR_EASYOCR
                ]
            else:
                strategies = [
                    ParserStrategy.PDF_NATIVE,
                    ParserStrategy.PDF_HISTOGRAM,
                    ParserStrategy.OCR_EASYOCR
                ]
            
            # Try strategies in order
            for strategy in strategies:
                if verbose:
                    print(f"\nAttempting: {strategy.value}")
                
                attempt_start = time.time()
                attempt = {
                    'strategy': strategy.value,
                    'start_time': attempt_start,
                    'success': False
                }
                
                try:
                    if strategy == ParserStrategy.PDF_NATIVE:
                        data, simplified = run_pdf_pipeline(
                            pdf_path=file_path,
                            use_histogram_columns=False,
                            use_region_detection=False,
                            verbose=False
                        )
                    
                    elif strategy == ParserStrategy.PDF_HISTOGRAM:
                        data, simplified = run_pdf_pipeline(
                            pdf_path=file_path,
                            use_histogram_columns=True,
                            use_region_detection=False,
                            verbose=False
                        )
                    
                    elif strategy == ParserStrategy.PDF_REGION_BASED:
                        data, simplified = run_pdf_pipeline(
                            pdf_path=file_path,
                            use_histogram_columns=True,
                            use_region_detection=True,
                            verbose=False
                        )
                    
                    elif strategy == ParserStrategy.OCR_EASYOCR:
                        data, simplified = run_pipeline_ocr(
                            pdf_path=file_path,
                            dpi=300,
                            languages=['en'],
                            verbose=False,
                            gpu=False
                        )
                    
                    else:
                        continue
                    
                    attempt['duration'] = time.time() - attempt_start
                    attempt['success'] = True
                    
                    # Calculate quality
                    quality = self.calculate_quality_score(data)
                    attempt['quality'] = quality
                    
                    result.attempts.append(attempt)
                    
                    if verbose:
                        print(f"  Success! Quality: {quality:.1f}/100")
                        print(f"  Sections: {len(data.get('sections', []))}")
                        print(f"  Duration: {attempt['duration']:.2f}s")
                    
                    # Accept if quality is good enough
                    if quality >= 60:  # Threshold for acceptable quality
                        result.success = True
                        result.strategy_used = strategy
                        result.data = data
                        result.simplified_json = simplified
                        result.quality_score = quality
                        break
                    else:
                        if verbose:
                            print(f"  Quality too low, trying next strategy...")
                
                except Exception as e:
                    attempt['duration'] = time.time() - attempt_start
                    attempt['error'] = str(e)
                    result.attempts.append(attempt)
                    
                    if verbose:
                        print(f"  Failed: {e}")
            
            # If nothing worked, return best attempt
            if not result.success and result.attempts:
                best_attempt = max(result.attempts, key=lambda x: x.get('quality', 0))
                if 'data' in locals() and best_attempt.get('quality', 0) > 0:
                    result.success = True
                    result.strategy_used = ParserStrategy(best_attempt['strategy'])
                    result.data = data
                    result.simplified_json = simplified
                    result.quality_score = best_attempt['quality']
                    result.warnings.append(f"Low quality extraction ({best_attempt['quality']:.1f}/100)")
            
            result.processing_time = time.time() - start_time
            
            if verbose:
                print(f"\n{'='*70}")
                print(f"Final Result: {'SUCCESS' if result.success else 'FAILED'}")
                if result.success:
                    print(f"Strategy: {result.strategy_used.value}")
                    print(f"Quality: {result.quality_score:.1f}/100")
                print(f"Time: {result.processing_time:.2f}s")
                print(f"{'='*70}\n")
            
            return result
            
        except Exception as e:
            result.processing_time = time.time() - start_time
            result.errors.append(str(e))
            if verbose:
                print(f"Error: {e}")
            return result


# Convenience function
def parse_resume(file_path: str, verbose: bool = False) -> ParsingResult:
    """
    Quick parse function for single resume.
    
    Args:
        file_path: Path to resume file
        verbose: Print progress
        
    Returns:
        ParsingResult object
    """
    parser = ResumeParser()
    return parser.parse(file_path, verbose=verbose)
