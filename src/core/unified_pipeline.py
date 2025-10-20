"""
Unified Resume Parsing Pipeline
================================

Main entry point that orchestrates all parsing strategies:
1. File type detection
2. Layout analysis
3. Strategy selection (PDF, OCR, Region-based)
4. Extraction and validation
5. Section learning

This is the single interface for all resume parsing operations.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from src.app.file_detector import FileDetector
from src.app.layout_analyzer import LayoutAnalyzer
from src.app.strategy_selector import StrategySelector
from src.app.quality_validator import QualityValidator
from src.core.section_learner import SectionLearner


class UnifiedPipeline:
    """
    Unified pipeline for intelligent resume parsing.
    Handles all file types, layouts, and extraction strategies.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        enable_learning: bool = True,
        verbose: bool = False
    ):
        """
        Initialize the unified pipeline.
        
        Args:
            config_path: Path to sections_database.json config
            enable_learning: Enable section learning from parsed resumes
            verbose: Print detailed progress
        """
        self.verbose = verbose
        self.enable_learning = enable_learning
        
        # Initialize components
        self.file_detector = FileDetector()
        self.layout_analyzer = LayoutAnalyzer()
        self.strategy_selector = StrategySelector()
        self.validator = QualityValidator()
        
        # Initialize section learner if enabled
        if enable_learning:
            if config_path is None:
                config_path = "config/sections_database.json"
            self.learner = SectionLearner(config_path)
        else:
            self.learner = None
        if self.verbose:
            print("[Unified Pipeline] Initialized")
    
    def parse(
        self,
        file_path: str,
        force_strategy: Optional[str] = None,
        save_debug: bool = False,
        verbose: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Parse a resume file using the best strategy.
        
        Args:
            file_path: Path to resume file (PDF, DOCX, etc.)
            force_strategy: Force specific strategy ('pdf', 'ocr', 'region')
            save_debug: Save debug information
            verbose: Override instance verbose setting
            
        Returns:
            Dictionary with:
                - success: bool
                - result: parsed resume data
                - metadata: processing metadata
                - strategy: strategy used
        """
        # Allow per-call verbose override
        if verbose is None:
            verbose = self.verbose
        else:
            verbose = verbose
        start_time = time.time()
        
        result = {
            'success': False,
            'result': None,
            'metadata': {
                'file_path': str(file_path),
                'file_name': Path(file_path).name,
                'strategy': None,
                'processing_time': 0.0,
                'attempts': []
            },
            'strategy': None        }
        
        try:
            if verbose:
                print(f"\n{'='*60}")
                print(f"[Unified Pipeline] Processing: {Path(file_path).name}")
                print(f"{'='*60}")
            
            # Step 1: File type detection
            file_info = self.file_detector.detect(file_path)
            result['metadata']['file_type'] = file_info['type']
            
            if verbose:
                print(f"[Step 1] File Type: {file_info['type'].upper()}")
            
            # Step 2: Layout analysis (for PDFs)
            if file_info['type'] == 'pdf':
                layout_info = self.layout_analyzer.analyze(file_path)
                result['metadata']['layout'] = layout_info
                
                if verbose:
                    print(f"[Step 2] Layout: {layout_info['num_columns']} columns, "
                          f"{layout_info['num_regions']} regions, "
                          f"Scanned: {layout_info['is_scanned']}")
            else:
                layout_info = {'type': 'unknown'}
            
            # Step 3: Select strategy
            if force_strategy:
                strategy = force_strategy
                if verbose:
                    print(f"[Step 3] Strategy: {strategy.upper()} (forced)")
            else:
                strategy = self.strategy_selector.select(file_info, layout_info)
                if verbose:
                    print(f"[Step 3] Strategy: {strategy.upper()} (auto-selected)")
            
            result['strategy'] = strategy
            result['metadata']['strategy'] = strategy
            
            # Step 4: Execute strategy
            if verbose:
                print(f"[Step 4] Executing {strategy.upper()} extraction...")
            
            extraction_result = self._execute_strategy(
                file_path, strategy, file_info, layout_info
            )
            
            result['metadata']['attempts'].append({
                'strategy': strategy,
                'success': extraction_result['success'],                'duration': extraction_result.get('duration', 0.0)
            })
            
            if not extraction_result['success']:
                # Try fallback strategies
                if verbose:
                    print(f"[Step 4] Strategy failed, trying fallback...")
                
                fallback_result = self._try_fallbacks(
                    file_path, strategy, file_info, layout_info, verbose
                )
                
                if fallback_result['success']:
                    extraction_result = fallback_result                    
                    result['strategy'] = fallback_result['strategy']
                    result['metadata']['strategy'] = fallback_result['strategy']
            
            # Step 5: Validate quality
            if extraction_result['success']:
                quality = self.validator.validate(extraction_result['data'])
                result['metadata']['quality'] = quality
                
                if verbose:
                    print(f"[Step 5] Quality: {quality['score']:.0%}, "
                          f"Sections: {quality['num_sections']}, "
                          f"Lines: {quality['total_lines']}")
                
                # Step 6: Learn new sections and re-classify (if enabled)
                if self.enable_learning and self.learner:
                    # First, learn from the result
                    learned = self.learner.learn_from_result(extraction_result['data'])
                    
                    if learned:
                        if verbose:
                            print(f"[Step 6] Learned {len(learned)} new section variants")
                        
                        # Re-classify sections with the newly learned vocabulary
                        sections = extraction_result['data'].get('sections', [])
                        reclassified_count = 0
                        for section in sections:
                            section_name = section.get('section', '')
                            
                            # Only re-classify "Unknown Sections"
                            if section_name == 'Unknown Sections':
                                # Try to classify each line as a potential section header
                                lines = section.get('lines', [])
                                if lines:
                                    # The first line might be a section header
                                    potential_header = lines[0] if isinstance(lines[0], str) else str(lines[0])
                                    
                                    # Skip if it's empty or just whitespace
                                    if not potential_header or not potential_header.strip():
                                        continue
                                    
                                    is_valid, matched_section, confidence = self.learner.classify_section(potential_header)
                                    
                                    if is_valid and confidence > 0.7:
                                        section['section'] = matched_section
                                        section['confidence'] = confidence
                                        reclassified_count += 1
                                        
                                        if verbose:
                                            print(f"         Re-classified '{potential_header}' -> '{matched_section}' ({confidence:.2f})")
                        
                        if reclassified_count > 0:
                            if verbose:
                                print(f"[Step 6] Re-classified {reclassified_count} unknown sections")
                            
                            # Update quality after re-classification
                            quality = self.validator.validate(extraction_result['data'])
                            result['metadata']['quality'] = quality
                
                result['success'] = True
                result['result'] = extraction_result['data']
            
            else:
                if verbose:
                    print(f"[Failed] All strategies failed")
                
                result['success'] = False
                result['result'] = self._empty_result()
        except Exception as e:
            if verbose:
                print(f"[Error] {e}")
            
            result['success'] = False
            result['result'] = self._empty_result()
            result['metadata']['error'] = str(e)
        
        finally:
            result['metadata']['processing_time'] = time.time() - start_time
            
            if verbose:
                status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
                print(f"\n{status} - Time: {result['metadata']['processing_time']:.2f}s")
        
        return result
    
    def _execute_strategy(
        self,
        file_path: str,
        strategy: str,
        file_info: Dict[str, Any],
        layout_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific parsing strategy."""
        start_time = time.time()
        
        try:
            if strategy == 'pdf':
                from src.PDF_pipeline.pipeline import run_pipeline
                parsed, _ = run_pipeline(
                    pdf_path=file_path,
                    use_histogram_columns=True,
                    verbose=False
                )
                
                return {
                    'success': True,
                    'data': parsed,
                    'strategy': 'pdf',
                    'duration': time.time() - start_time
                }
            
            elif strategy == 'ocr':
                from src.IMG_pipeline.pipeline import run_pipeline_ocr
                parsed, _ = run_pipeline_ocr(
                    pdf_path=file_path,
                    dpi=300,
                    languages=['en'],
                    verbose=False,
                    gpu=False
                )
                
                return {
                    'success': True,
                    'data': parsed,
                    'strategy': 'ocr',
                    'duration': time.time() - start_time
                }
            
            elif strategy == 'region':
                from src.PDF_pipeline.pipeline import run_pipeline
                parsed, _ = run_pipeline(
                    pdf_path=file_path,
                    use_region_detection=True,
                    verbose=False
                )
                
                return {
                    'success': True,
                    'data': parsed,
                    'strategy': 'region',
                    'duration': time.time() - start_time
                }
            
            else:
                return {
                    'success': False,
                    'error': f"Unknown strategy: {strategy}",
                    'duration': time.time() - start_time
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),                'duration': time.time() - start_time
            }
    
    def _try_fallbacks(
        self,
        file_path: str,
        failed_strategy: str,
        file_info: Dict[str, Any],
        layout_info: Dict[str, Any],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Try fallback strategies if primary fails."""
        
        # Define fallback order based on what failed
        if failed_strategy == 'pdf':
            fallbacks = ['region', 'ocr']
        elif failed_strategy == 'region':
            fallbacks = ['pdf', 'ocr']
        elif failed_strategy == 'ocr':
            fallbacks = ['pdf', 'region']
        else:
            fallbacks = ['pdf', 'ocr']
        
        for fallback in fallbacks:
            if verbose:
                print(f"  Trying fallback: {fallback.upper()}")
            
            result = self._execute_strategy(
                file_path, fallback, file_info, layout_info
            )
            
            if result['success']:
                return result
        
        return {'success': False}
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "meta": {
                "pages": 0,
                "columns": 0,
                "sections": 0,
                "lines_total": 0
            },
            "sections": [],
            "contact": {}
        }
