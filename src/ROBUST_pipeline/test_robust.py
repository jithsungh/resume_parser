"""
Test and demonstration script for robust pipeline.
Shows comparison between standard pipeline and robust pipeline.
"""

import sys
from pathlib import Path
import time
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ROBUST_pipeline.pipeline import robust_pipeline
from src.ROBUST_pipeline.adaptive_thresholds import AdaptiveThresholds
from src.PDF_pipeline.pipeline import run_pipeline
from src.IMG_pipeline.pipeline import run_pipeline_ocr


def test_single_resume(pdf_path: str, use_robust: bool = True, use_standard: bool = True):
    """
    Test both pipelines on a single resume and compare results.
    
    Args:
        pdf_path: Path to PDF file
        use_robust: Whether to run robust pipeline
        use_standard: Whether to run standard pipeline
    """
    print("=" * 80)
    print(f"Testing: {pdf_path}")
    print("=" * 80)
    
    results = {}
    
    # Test robust pipeline
    if use_robust:
        print("\n[1] ROBUST PIPELINE")
        print("-" * 80)
        try:
            start = time.time()
            result_robust, simple_robust = robust_pipeline(
                path=pdf_path,
                use_ocr=True,
                use_gpu=False,
                dpi=300,
                max_depth=3,
                verbose=True
            )
            elapsed = time.time() - start
            
            print(f"\n✓ Robust pipeline completed in {elapsed:.2f}s")
            print(f"  Pages: {result_robust['meta']['pages']}")
            print(f"  Sections: {result_robust['meta']['sections']}")
            print(f"  Total lines: {result_robust['meta']['total_lines']}")
            
            sections = result_robust.get('sections', [])
            print(f"\n  Detected sections:")
            for sec in sections:
                print(f"    - {sec['section']}: {sec['line_count']} lines")
            
            results['robust'] = {
                'time': elapsed,
                'result': result_robust,
                'simplified': simple_robust,
            }
            
        except Exception as e:
            print(f"\n✗ Robust pipeline failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test standard PDF pipeline
    if use_standard:
        print("\n[2] STANDARD PDF PIPELINE")
        print("-" * 80)
        try:
            start = time.time()
            result_std, simple_std = run_pipeline(
                pdf_path=pdf_path,
                verbose=True
            )
            elapsed = time.time() - start
            
            print(f"\n✓ Standard pipeline completed in {elapsed:.2f}s")
            print(f"  Sections: {result_std['meta']['sections']}")
            
            sections = result_std.get('sections', [])
            print(f"\n  Detected sections:")
            for sec in sections:
                print(f"    - {sec['section']}: {len(sec['lines'])} lines")
            
            results['standard'] = {
                'time': elapsed,
                'result': result_std,
                'simplified': simple_std,
            }
            
        except Exception as e:
            print(f"\n✗ Standard pipeline failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Comparison
    if 'robust' in results and 'standard' in results:
        print("\n[3] COMPARISON")
        print("-" * 80)
        
        robust_sections = set(s['section'] for s in results['robust']['result'].get('sections', []))
        std_sections = set(s['section'] for s in results['standard']['result'].get('sections', []))
        
        print(f"\nRobust pipeline sections: {len(robust_sections)}")
        print(f"Standard pipeline sections: {len(std_sections)}")
        
        only_robust = robust_sections - std_sections
        only_std = std_sections - robust_sections
        common = robust_sections & std_sections
        
        print(f"\nCommon sections ({len(common)}): {', '.join(sorted(common))}")
        
        if only_robust:
            print(f"\nOnly in robust ({len(only_robust)}): {', '.join(sorted(only_robust))}")
        
        if only_std:
            print(f"\nOnly in standard ({len(only_std)}): {', '.join(sorted(only_std))}")
        
        print(f"\nProcessing time:")
        print(f"  Robust: {results['robust']['time']:.2f}s")
        print(f"  Standard: {results['standard']['time']:.2f}s")
        print(f"  Ratio: {results['robust']['time'] / results['standard']['time']:.2f}x")
    
    return results


def test_adaptive_thresholds(pdf_paths: list):
    """
    Test adaptive threshold adjustment across multiple documents.
    
    Args:
        pdf_paths: List of PDF paths
    """
    print("\n" + "=" * 80)
    print("ADAPTIVE THRESHOLD TEST")
    print("=" * 80)
    
    adaptive = AdaptiveThresholds()
    
    print(f"\nDefault thresholds:")
    for key, value in adaptive.get_current_thresholds().items():
        print(f"  {key}: {value}")
    
    # Process each document
    all_results = []
    
    for pdf_path in pdf_paths:
        print(f"\n\nProcessing: {pdf_path}")
        print("-" * 80)
        
        try:
            result, _ = robust_pipeline(
                path=pdf_path,
                use_ocr=True,
                use_gpu=False,
                verbose=False
            )
            
            all_results.append(result)
            
            # Analyze this document
            stats = adaptive.analyze_document([result])
            
            print(f"\nDocument statistics:")
            print(f"  Pages: {stats.get('num_pages', 0)}")
            print(f"  Avg lines/page: {stats.get('avg_lines_per_page', 0):.1f}")
            print(f"  Primary layout: {stats.get('primary_layout', 'unknown')}")
            
            if 'font_size_mean' in stats:
                print(f"  Font size: {stats['font_size_mean']:.1f} ± {stats.get('font_size_std', 0):.1f}")
            
            if 'spacing_median' in stats:
                print(f"  Spacing median: {stats['spacing_median']:.1f}")
            
        except Exception as e:
            print(f"Failed: {e}")
    
    # Adjust thresholds based on all documents
    if all_results:
        print("\n" + "=" * 80)
        print("OVERALL ADAPTIVE ADJUSTMENT")
        print("=" * 80)
        
        # Combine stats from all documents
        combined_stats = adaptive.analyze_document(all_results)
        adjusted = adaptive.adjust_thresholds(combined_stats)
        
        print(f"\nAdjusted thresholds:")
        for key, value in adjusted.items():
            print(f"  {key}: {value}")


def demo_layout_detection():
    """
    Demonstrate layout detection capabilities.
    """
    print("\n" + "=" * 80)
    print("LAYOUT DETECTION DEMO")
    print("=" * 80)
    
    from src.ROBUST_pipeline.pipeline import (
        load_and_preprocess,
        remove_lines,
        detect_text_blocks,
        analyze_block_layout,
    )
    
    # This would need actual test files
    print("\nLayout detection demo requires test PDF files.")
    print("Create test files with different layouts:")
    print("  1. Single column (vertical)")
    print("  2. Two column (horizontal)")
    print("  3. Mixed (hybrid)")
    print("\nThen run: python test_robust.py --demo <pdf_path>")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test robust pipeline")
    parser.add_argument("--pdf", help="Single PDF to test")
    parser.add_argument("--batch", nargs='+', help="Multiple PDFs for adaptive test")
    parser.add_argument("--demo", help="Demo layout detection on a PDF")
    parser.add_argument("--no-robust", action="store_true", help="Skip robust pipeline")
    parser.add_argument("--no-standard", action="store_true", help="Skip standard pipeline")
    
    args = parser.parse_args()
    
    if args.pdf:
        test_single_resume(
            args.pdf,
            use_robust=not args.no_robust,
            use_standard=not args.no_standard
        )
    
    elif args.batch:
        test_adaptive_thresholds(args.batch)
    
    elif args.demo:
        # For demo, just run robust pipeline with verbose output
        print("Running layout-aware demo...")
        result, simplified = robust_pipeline(
            path=args.demo,
            use_ocr=True,
            use_gpu=False,
            verbose=True
        )
        
        print("\n" + "=" * 80)
        print("SIMPLIFIED OUTPUT")
        print("=" * 80)
        print(simplified)
    
    else:
        print("Usage:")
        print("  Test single file:")
        print("    python test_robust.py --pdf path/to/resume.pdf")
        print("\n  Test adaptive thresholds:")
        print("    python test_robust.py --batch resume1.pdf resume2.pdf resume3.pdf")
        print("\n  Demo layout detection:")
        print("    python test_robust.py --demo path/to/resume.pdf")
        print("\nOptions:")
        print("  --no-robust      Skip robust pipeline")
        print("  --no-standard    Skip standard pipeline")
