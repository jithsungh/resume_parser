"""
Smart Resume Parser - Layout-aware parsing with automatic pipeline selection.

This module:
1. Detects PDF layout characteristics
2. Routes to optimal pipeline (PDF or OCR)
3. Returns standardized results

Philosophy: Use the right tool for the right job.
"""

from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import time
import json

import src.detect_layout as ld
from src.PDF_pipeline.pipeline import run_pipeline as run_pdf_pipeline

# Lazy import for OCR to avoid OpenCV/EasyOCR import errors on headless servers
_ocr_pipeline = None

def _get_ocr_pipeline():
    """Lazy load OCR pipeline only when needed"""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        try:
            from src.IMG_pipeline.pipeline import run_pipeline_ocr
            _ocr_pipeline = run_pipeline_ocr
        except ImportError as e:
            raise ImportError(
                f"OCR pipeline not available. Missing dependencies: {e}\n"
                "On headless Linux servers, install: sudo yum install mesa-libGL (RHEL/CentOS) "
                "or sudo apt-get install libgl1 (Ubuntu/Debian)"
            )
    return _ocr_pipeline


def smart_parse_resume(
    pdf_path: str,
    force_pipeline: Optional[str] = None,
    ocr_dpi: int = 300,
    ocr_languages: list = None,
    verbose: bool = True
) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    """
    Smart resume parser that automatically selects the best pipeline.
    
    Args:
        pdf_path: Path to PDF resume
        force_pipeline: Force 'pdf' or 'ocr' pipeline (None = auto-detect)
        ocr_dpi: DPI for OCR (if used)
        ocr_languages: Languages for OCR (if used)
        verbose: Print progress
        
    Returns:
        Tuple of (result_dict, simplified_json, metadata)
        
    Metadata contains:
        - pipeline_used: 'pdf' or 'ocr'
        - layout_analysis: dict from detector
        - processing_time: float
        - success: bool
    """
    if ocr_languages is None:
        ocr_languages = ['en']
    
    metadata = {
        'pipeline_used': None,
        'layout_analysis': None,
        'processing_time': 0.0,
        'file_name': Path(pdf_path).name,
        'success': False
    }
    
    start_time = time.time()
    
    # Detect layout
    if force_pipeline:
        use_pipeline = force_pipeline.lower()
        if verbose:
            print(f"[Smart Parser] Forced to use {use_pipeline.upper()} pipeline")
        metadata['layout_analysis'] = {'forced': True, 'pipeline': use_pipeline}
    else:
        if verbose:
            print(f"[Smart Parser] Detecting layout...")
        
        analysis = ld.detect_resume_layout(pdf_path)
        use_pipeline = analysis['recommended_pipeline']
        metadata['layout_analysis'] = analysis
        
        if verbose:
            print(f"[Smart Parser] Auto-detected: {use_pipeline.upper()} pipeline")
            print(f"  Confidence: {analysis['confidence']:.1%}")
            print(f"  Columns: {analysis['num_columns']}")
            print(f"  Scanned: {analysis['is_scanned']}")
            print(f"  Complexity: {analysis['layout_complexity']}")
    
    # Run appropriate pipeline
    try:
        if use_pipeline == 'pdf':
            if verbose:
                print(f"[Smart Parser] Running PDF pipeline (PyMuPDF)...")
            
            result, simplified = run_pdf_pipeline(
                pdf_path=pdf_path,
                verbose=verbose
            )
            metadata['pipeline_used'] = 'pdf'
        else:  # ocr
            if verbose:
                print(f"[Smart Parser] Running OCR pipeline (EasyOCR)...")
            
            # Get OCR pipeline (lazy load)
            run_pipeline_ocr = _get_ocr_pipeline()
            
            result, simplified = run_pipeline_ocr(
                pdf_path=pdf_path,
                dpi=ocr_dpi,
                languages=ocr_languages,
                verbose=verbose,
                gpu=False  # CPU mode for compatibility
            )
            metadata['pipeline_used'] = 'ocr'
        
        metadata['processing_time'] = time.time() - start_time
        metadata['success'] = True
        
        if verbose:
            print(f"[Smart Parser] Completed in {metadata['processing_time']:.2f}s")
            sections_count = len(result.get('sections', []))
            print(f"  Sections found: {sections_count}")
            
            total_lines = sum(len(s.get('lines', [])) for s in result.get('sections', []))
            print(f"  Total lines: {total_lines}")
        
        return result, simplified, metadata
        
    except Exception as e:
        metadata['processing_time'] = time.time() - start_time
        metadata['success'] = False
        metadata['error'] = str(e)
        
        if verbose:
            print(f"[Smart Parser] Error: {e}")
        
        # Return empty result
        empty = {
            "meta": {
                "pages": 0,
                "columns": 0,
                "sections": 0,
                "lines_total": 0
            },
            "sections": [],
            "contact": {}
        }
        return empty, "[]", metadata


def batch_smart_parse(
    input_dir: str,
    output_dir: Optional[str] = None,
    file_pattern: str = "*.pdf",
    max_files: Optional[int] = None,
    verbose: bool = True,
    save_results: bool = True
) -> list:
    """
    Batch process resumes with smart routing.
    
    Args:
        input_dir: Directory containing PDFs
        output_dir: Optional output directory for saving results
        file_pattern: Glob pattern for files
        max_files: Maximum number of files to process
        verbose: Print progress
        save_results: Save individual results to files
        
    Returns:
        List of (file_path, result, simplified, metadata) tuples
    """
    from pathlib import Path
    import json
    
    input_path = Path(input_dir)
    files = list(input_path.glob(file_pattern))
    
    if max_files:
        files = files[:max_files]
    
    if not files:
        print(f"No files found matching {file_pattern} in {input_dir}")
        return []
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Smart Batch Processing")
        print(f"{'='*60}")
        print(f"Files found: {len(files)}")
        print(f"Input: {input_dir}")
        if output_dir:
            print(f"Output: {output_dir}")
        print(f"{'='*60}\n")
    
    results = []
    
    for i, file_path in enumerate(files, 1):
        if verbose:
            print(f"\n[{i}/{len(files)}] Processing: {file_path.name}")
            print("-" * 60)
        
        try:
            result, simplified, metadata = smart_parse_resume(
                str(file_path),
                verbose=verbose
            )
            
            results.append((file_path, result, simplified, metadata))
            
            # Save if output directory specified
            if output_dir and save_results:
                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                
                stem = file_path.stem
                
                # Save full result
                with open(out_path / f"{stem}_full.json", 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                # Save simplified
                with open(out_path / f"{stem}_simple.json", 'w', encoding='utf-8') as f:
                    f.write(simplified)
                
                # Save metadata
                with open(out_path / f"{stem}_metadata.json", 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            if verbose:
                print(f"ERROR: {e}")
            results.append((file_path, None, None, {
                'error': str(e),
                'success': False,
                'file_name': file_path.name
            }))
    
    # Summary
    if verbose:
        print(f"\n{'='*60}")
        print(f"Batch Processing Summary")
        print(f"{'='*60}")
        
        pdf_count = sum(1 for _, _, _, m in results if m.get('pipeline_used') == 'pdf')
        ocr_count = sum(1 for _, _, _, m in results if m.get('pipeline_used') == 'ocr')
        error_count = sum(1 for _, _, _, m in results if 'error' in m)
        success_count = sum(1 for _, _, _, m in results if m.get('success', False))
        
        print(f"Total files: {len(results)}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  PDF pipeline: {pdf_count}")
        print(f"  OCR pipeline: {ocr_count}")
        
        if results:
            avg_time = sum(m.get('processing_time', 0) for _, _, _, m in results) / len(results)
            print(f"\nAverage processing time: {avg_time:.2f}s")
        
        print(f"{'='*60}\n")
    
    return results


def compare_pipelines(pdf_path: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Compare PDF and OCR pipelines side-by-side for debugging.
    
    Args:
        pdf_path: Path to PDF file
        verbose: Print progress
        
    Returns:
        Dictionary with comparison results
    """
    comparison = {
        'file': Path(pdf_path).name,
        'pdf_pipeline': {},
        'ocr_pipeline': {},
        'layout_analysis': {}
    }
    
    # Layout detection
    if verbose:
        print(f"Analyzing layout...")
    analysis = ld.detect_resume_layout(pdf_path)
    comparison['layout_analysis'] = analysis
    
    if verbose:
        print(f"Recommended: {analysis['recommended_pipeline']}")
    
    # PDF Pipeline
    if verbose:
        print(f"\nTesting PDF pipeline...")
    try:
        start = time.time()
        result_pdf, simple_pdf = run_pdf_pipeline(pdf_path, verbose=False)
        pdf_time = time.time() - start
        
        comparison['pdf_pipeline'] = {
            'success': True,
            'time': pdf_time,
            'sections': len(result_pdf.get('sections', [])),
            'lines': sum(len(s.get('lines', [])) for s in result_pdf.get('sections', [])),
            'result': result_pdf,
            'simplified': simple_pdf
        }
        
        if verbose:
            print(f"  Time: {pdf_time:.2f}s")
            print(f"  Sections: {comparison['pdf_pipeline']['sections']}")
            print(f"  Lines: {comparison['pdf_pipeline']['lines']}")
    except Exception as e:
        comparison['pdf_pipeline'] = {
            'success': False,
            'error': str(e)
        }
        if verbose:
            print(f"  Error: {e}")
      # OCR Pipeline
    if verbose:
        print(f"\nTesting OCR pipeline...")
    try:
        # Get OCR pipeline (lazy load)
        run_pipeline_ocr = _get_ocr_pipeline()
        
        start = time.time()
        result_ocr, simple_ocr = run_pipeline_ocr(pdf_path, verbose=False, gpu=False)
        ocr_time = time.time() - start
        
        comparison['ocr_pipeline'] = {
            'success': True,
            'time': ocr_time,
            'sections': len(result_ocr.get('sections', [])),
            'lines': sum(len(s.get('lines', [])) for s in result_ocr.get('sections', [])),
            'result': result_ocr,
            'simplified': simple_ocr
        }
        
        if verbose:
            print(f"  Time: {ocr_time:.2f}s")
            print(f"  Sections: {comparison['ocr_pipeline']['sections']}")
            print(f"  Lines: {comparison['ocr_pipeline']['lines']}")
    except Exception as e:
        comparison['ocr_pipeline'] = {
            'success': False,
            'error': str(e)
        }
        if verbose:
            print(f"  Error: {e}")
    
    return comparison


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Smart resume parser with automatic pipeline selection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse single resume (auto-detect pipeline)
  python -m src.smart_parser --pdf resume.pdf
  
  # Force PDF pipeline
  python -m src.smart_parser --pdf resume.pdf --force pdf
  
  # Batch process directory
  python -m src.smart_parser --batch freshteams_resume/Resumes --output outputs/parsed
  
  # Compare pipelines
  python -m src.smart_parser --pdf resume.pdf --compare
        """
    )
    
    parser.add_argument("--pdf", help="Single PDF file to parse")
    parser.add_argument("--batch", help="Directory of PDFs to batch process")
    parser.add_argument("--output", help="Output directory for batch processing")
    parser.add_argument("--force", choices=['pdf', 'ocr'], help="Force specific pipeline")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for OCR")
    parser.add_argument("--max", type=int, help="Max files for batch processing")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("--compare", action="store_true", help="Compare both pipelines")
    parser.add_argument("--no-save", action="store_true", help="Don't save individual files in batch mode")
    
    args = parser.parse_args()
    
    if args.pdf:
        if args.compare:
            # Compare mode
            print(f"\n{'='*60}")
            print(f"Pipeline Comparison")
            print(f"{'='*60}")
            
            comparison = compare_pipelines(args.pdf, verbose=not args.quiet)
            
            print(f"\n{'='*60}")
            print(f"Summary")
            print(f"{'='*60}")
            print(f"Recommended: {comparison['layout_analysis']['recommended_pipeline']}")
            
            if comparison['pdf_pipeline'].get('success'):
                print(f"\nPDF Pipeline:")
                print(f"  Time: {comparison['pdf_pipeline']['time']:.2f}s")
                print(f"  Sections: {comparison['pdf_pipeline']['sections']}")
                print(f"  Lines: {comparison['pdf_pipeline']['lines']}")
            
            if comparison['ocr_pipeline'].get('success'):
                print(f"\nOCR Pipeline:")
                print(f"  Time: {comparison['ocr_pipeline']['time']:.2f}s")
                print(f"  Sections: {comparison['ocr_pipeline']['sections']}")
                print(f"  Lines: {comparison['ocr_pipeline']['lines']}")
        
        else:
            # Single file mode
            result, simplified, metadata = smart_parse_resume(
                args.pdf,
                force_pipeline=args.force,
                ocr_dpi=args.dpi,
                verbose=not args.quiet
            )
            
            print("\n" + "="*60)
            print("SIMPLIFIED OUTPUT")
            print("="*60)
            print(simplified)
            
            if not args.quiet:
                print("\n" + "="*60)
                print("METADATA")
                print("="*60)
                print(f"Pipeline: {metadata['pipeline_used']}")
                print(f"Time: {metadata['processing_time']:.2f}s")
                print(f"Success: {metadata['success']}")
        
    elif args.batch:
        # Batch processing
        results = batch_smart_parse(
            input_dir=args.batch,
            output_dir=args.output,
            max_files=args.max,
            verbose=not args.quiet,
            save_results=not args.no_save
        )
        
    else:
        parser.print_help()
