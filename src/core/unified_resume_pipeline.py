"""
Step 7: Unified Resume Parsing Pipeline
========================================
Integrates all components into a single, cohesive parsing system.

Pipeline Flow:
1. Document Type Detection
2. Word Extraction with Metadata
3. Layout Detection via Histograms
4. Column Segmentation
5. Line & Section Grouping
6. Unknown Section Detection
7. Output Generation

Features:
- Modular and scalable architecture
- Handles both text-based and scanned documents
- Lazy loading for heavy modules (OCR, embeddings)
- Intermediate result caching for debugging
- Comprehensive error handling
"""

from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import json
import time

from .document_detector import DocumentDetector, DocumentType
from .word_extractor import WordExtractor, WordMetadata
from .layout_detector_histogram import LayoutDetector, LayoutType
from .column_segmenter import ColumnSegmenter, Column
from .line_section_grouper import LineGrouper, SectionDetector, Line, Section
from .unknown_section_detector import UnknownSectionDetector, UnknownSection


@dataclass
class PipelineResult:
    """Complete pipeline result"""
    # Input info
    file_path: str
    file_name: str
    
    # Step results
    document_type: DocumentType
    total_words: int
    total_pages: int
    layouts: List[LayoutType]
    total_columns: int
    total_lines: int
    sections: List[Section]
    unknown_sections: List[UnknownSection]
    
    # Metadata
    processing_time: float
    pipeline_version: str = "2.0.0"
    success: bool = True
    error: Optional[str] = None
    
    # Debug info (optional)
    debug_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'file_path': self.file_path,
            'file_name': self.file_name,
            'document_type': {
                'file_type': self.document_type.file_type,
                'is_scanned': self.document_type.is_scanned,
                'recommended_extraction': self.document_type.recommended_extraction,
                'confidence': self.document_type.confidence
            },
            'statistics': {
                'total_words': self.total_words,
                'total_pages': self.total_pages,
                'total_columns': self.total_columns,
                'total_lines': self.total_lines,
                'total_sections': len(self.sections),
                'unknown_sections_count': len(self.unknown_sections)
            },
            'layouts': [
                {
                    'page': i,
                    'type': layout.type_name,
                    'num_columns': layout.num_columns,
                    'confidence': layout.confidence
                }
                for i, layout in enumerate(self.layouts)
            ],
            'sections': [
                {
                    'section_name': section.section_name,
                    'page': section.page,
                    'column_id': section.column_id,
                    'line_count': section.line_count,
                    'content': section.content_text,
                    'full_text': section.full_text
                }
                for section in self.sections
            ],
            'unknown_sections': [
                {
                    'section_name': unk.section.section_name,
                    'reason': unk.reason,
                    'confidence': unk.confidence,
                    'similar_to': unk.similar_to
                }
                for unk in self.unknown_sections
            ],
            'metadata': {
                'processing_time': self.processing_time,
                'pipeline_version': self.pipeline_version,
                'success': self.success,
                'error': self.error
            }
        }
        
        if include_debug and self.debug_data:
            result['debug'] = self.debug_data
        
        return result
    
    def to_json(self, include_debug: bool = False, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(include_debug=include_debug), indent=indent)


class UnifiedResumeParser:
    """
    Unified resume parsing pipeline
    
    This is the main entry point for all resume parsing operations.
    """
    
    def __init__(
        self,
        # Component configuration
        use_ocr_if_scanned: bool = True,
        use_embeddings: bool = True,
        
        # Tuning parameters
        histogram_bin_width: int = 5,
        y_tolerance: float = 2.0,
        column_overlap_threshold: float = 0.5,
        
        # Options
        save_debug: bool = False,
        verbose: bool = False
    ):
        """
        Initialize unified parser
        
        Args:
            use_ocr_if_scanned: Use OCR for scanned documents
            use_embeddings: Use semantic embeddings for section detection
            histogram_bin_width: Bin width for histogram analysis
            y_tolerance: Y-tolerance for line grouping
            column_overlap_threshold: Overlap threshold for column assignment
            save_debug: Save debug/intermediate data
            verbose: Print verbose progress
        """
        self.use_ocr_if_scanned = use_ocr_if_scanned
        self.use_embeddings = use_embeddings
        self.save_debug = save_debug
        self.verbose = verbose
        
        # Initialize components
        self.doc_detector = DocumentDetector(verbose=verbose)
        self.word_extractor = WordExtractor(verbose=verbose)
        self.layout_detector = LayoutDetector(
            bin_width=histogram_bin_width,
            verbose=verbose
        )
        self.column_segmenter = ColumnSegmenter(
            overlap_threshold=column_overlap_threshold,
            verbose=verbose
        )
        self.line_grouper = LineGrouper(
            y_tolerance=y_tolerance,
            verbose=verbose
        )
        self.section_detector = SectionDetector(
            use_embeddings=use_embeddings,
            verbose=verbose
        )
        self.unknown_detector = UnknownSectionDetector(
            use_embeddings=use_embeddings,
            verbose=verbose
        )
        
        if self.verbose:
            print("[UnifiedResumeParser] Initialized successfully")
            print(f"  OCR enabled: {use_ocr_if_scanned}")
            print(f"  Embeddings enabled: {use_embeddings}")
    
    def parse(self, file_path: str) -> PipelineResult:
        """
        Parse resume file through complete pipeline
        
        Args:
            file_path: Path to resume file
            
        Returns:
            PipelineResult with all extracted data
        """
        start_time = time.time()
        file_path = str(Path(file_path).resolve())
        file_name = Path(file_path).name
        
        if self.verbose:
            print("\n" + "="*70)
            print(f"UNIFIED RESUME PARSER - {file_name}")
            print("="*70)
        
        debug_data = {} if self.save_debug else None
        
        try:
            # Step 1: Document Type Detection
            if self.verbose:
                print("\n[1/7] Document Type Detection")
            
            doc_type = self.doc_detector.detect(file_path)
            
            if self.save_debug:
                debug_data['document_type'] = asdict(doc_type)
            
            if self.verbose:
                print(f"  Type: {doc_type.file_type.upper()}")
                print(f"  Scanned: {doc_type.is_scanned}")
                print(f"  Extraction: {doc_type.recommended_extraction.upper()}")
            
            # Step 2: Word Extraction
            if self.verbose:
                print("\n[2/7] Word Extraction with Metadata")
            
            pages_words = self._extract_words(file_path, doc_type)
            
            total_words = sum(len(page) for page in pages_words)
            
            if self.save_debug:
                debug_data['word_extraction'] = {
                    'total_words': total_words,
                    'total_pages': len(pages_words),
                    # Save first 100 words as sample
                    'sample_words': [w.to_dict() for w in pages_words[0][:100]] if pages_words and pages_words[0] else []
                }
            
            if self.verbose:
                print(f"  Extracted: {total_words} words from {len(pages_words)} pages")
            
            # Step 3: Layout Detection
            if self.verbose:
                print("\n[3/7] Layout Detection via Histograms")
            
            layouts = []
            for page_num, words in enumerate(pages_words):
                layout = self.layout_detector.detect_layout(words)
                layouts.append(layout)
                
                if self.verbose:
                    print(f"  Page {page_num + 1}: {layout.type_name}, {layout.num_columns} columns")
            
            if self.save_debug:
                debug_data['layouts'] = [
                    {
                        'page': i,
                        'type': layout.type,
                        'type_name': layout.type_name,
                        'num_columns': layout.num_columns,
                        'confidence': layout.confidence,
                        'peaks': layout.peaks,
                        'valleys': layout.valleys
                    }
                    for i, layout in enumerate(layouts)
                ]
            
            # Step 4: Column Segmentation
            if self.verbose:
                print("\n[4/7] Column Segmentation")
            
            all_columns = self.column_segmenter.segment_document(pages_words, layouts)
            total_columns = sum(len(page_cols) for page_cols in all_columns)
            
            if self.save_debug:
                debug_data['columns'] = {
                    'total_columns': total_columns,
                    'columns_per_page': [len(page_cols) for page_cols in all_columns]
                }
            
            if self.verbose:
                print(f"  Total columns: {total_columns}")
            
            # Step 5: Line & Section Grouping
            if self.verbose:
                print("\n[5/7] Line & Section Grouping")
            
            all_lines = []
            for page_columns in all_columns:
                page_lines = self.line_grouper.group_columns_into_lines(page_columns)
                all_lines.extend(page_lines)
            
            sections = self.section_detector.detect_sections(all_lines)
            
            if self.save_debug:
                debug_data['lines_and_sections'] = {
                    'total_lines': len(all_lines),
                    'total_sections': len(sections),
                    'section_names': [s.section_name for s in sections]
                }
            
            if self.verbose:
                print(f"  Lines: {len(all_lines)}")
                print(f"  Sections: {len(sections)}")
                for section in sections:
                    print(f"    - {section.section_name}: {len(section.content_lines)} lines")
            
            # Step 6: Unknown Section Detection
            if self.verbose:
                print("\n[6/7] Unknown Section Detection")
            
            unknown_sections = self.unknown_detector.detect_unknown_sections(sections)
            
            if self.save_debug:
                debug_data['unknown_sections'] = [
                    {
                        'section_name': unk.section.section_name,
                        'reason': unk.reason,
                        'confidence': unk.confidence,
                        'similar_to': unk.similar_to
                    }
                    for unk in unknown_sections
                ]
            
            if self.verbose:
                print(f"  Unknown sections: {len(unknown_sections)}")
                if unknown_sections:
                    for unk in unknown_sections:
                        print(f"    - '{unk.section.section_name}': {unk.reason}")
            
            # Step 7: Final Result
            processing_time = time.time() - start_time
            
            result = PipelineResult(
                file_path=file_path,
                file_name=file_name,
                document_type=doc_type,
                total_words=total_words,
                total_pages=len(pages_words),
                layouts=layouts,
                total_columns=total_columns,
                total_lines=len(all_lines),
                sections=sections,
                unknown_sections=unknown_sections,
                processing_time=processing_time,
                success=True,
                error=None,
                debug_data=debug_data
            )
            
            if self.verbose:
                print("\n" + "="*70)
                print(f"✅ PARSING COMPLETE - {processing_time:.2f}s")
                print("="*70)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            if self.verbose:
                print(f"\n❌ ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Return error result
            return PipelineResult(
                file_path=file_path,
                file_name=file_name,
                document_type=doc_type if 'doc_type' in locals() else None,
                total_words=0,
                total_pages=0,
                layouts=[],
                total_columns=0,
                total_lines=0,
                sections=[],
                unknown_sections=[],
                processing_time=processing_time,
                success=False,
                error=str(e),
                debug_data=debug_data
            )
    
    def _extract_words(
        self,
        file_path: str,
        doc_type: DocumentType
    ) -> List[List[WordMetadata]]:
        """Extract words based on document type"""
        
        if doc_type.file_type == 'pdf':
            if doc_type.recommended_extraction == 'ocr' and self.use_ocr_if_scanned:
                return self.word_extractor.extract_pdf_ocr(file_path)
            else:
                return self.word_extractor.extract_pdf_text_based(file_path)
        
        elif doc_type.file_type == 'docx':
            return self.word_extractor.extract_docx(file_path)
        
        else:
            raise ValueError(f"Unsupported file type: {doc_type.file_type}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python unified_pipeline.py <file_path> [--save-json]")
        print("\nOptions:")
        print("  --save-json    Save result to JSON file")
        print("  --debug        Include debug data in output")
        print("  --no-verbose   Disable verbose output")
        sys.exit(1)
    
    file_path = sys.argv[1]
    save_json = '--save-json' in sys.argv
    include_debug = '--debug' in sys.argv
    verbose = '--no-verbose' not in sys.argv
    
    # Create parser
    parser = UnifiedResumeParser(
        use_ocr_if_scanned=True,
        use_embeddings=True,
        save_debug=include_debug,
        verbose=verbose
    )
    
    # Parse
    result = parser.parse(file_path)
    
    # Save to JSON if requested
    if save_json and result.success:
        output_path = Path(file_path).stem + '_parsed.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.to_json(include_debug=include_debug, indent=2))
        
        print(f"\n💾 Saved to: {output_path}")
    
    # Print summary
    if not verbose:
        print("\n" + "="*70)
        print("PARSING SUMMARY")
        print("="*70)
        print(f"File: {result.file_name}")
        print(f"Success: {result.success}")
        if result.success:
            print(f"Words: {result.total_words}")
            print(f"Pages: {result.total_pages}")
            print(f"Sections: {len(result.sections)}")
            print(f"Processing time: {result.processing_time:.2f}s")
        else:
            print(f"Error: {result.error}")
