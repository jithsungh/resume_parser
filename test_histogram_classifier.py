#!/usr/bin/env python3
"""
Test script for histogram-based Type 2/3 classifier

Demonstrates the new quantitative histogram valley analysis for
distinguishing between Type 2 (clean two-column) and Type 3 (hybrid/complex)
layouts.

Usage:
    python test_histogram_classifier.py <resume_pdf>
    python test_histogram_classifier.py <resume_pdf> --visualize
    python test_histogram_classifier.py --batch <folder> --visualize
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
from src.core.layout_detector_y_overlap import EnhancedLayoutDetector, visualize_histogram


def test_single_resume(pdf_path: str, visualize: bool = False, verbose: bool = True):
    """Test histogram classifier on a single resume"""
    print("="*80)
    print(f"Testing Histogram-Based Classifier: {Path(pdf_path).name}")
    print("="*80)
    
    # Step 1: Detect document type
    if verbose:
        print("\n[1/3] Document Detection")
    doc_detector = DocumentDetector(verbose=False)
    doc_type = doc_detector.detect(pdf_path)
    
    if doc_type.file_type != 'pdf':
        print(f"Error: Only PDF files supported (got {doc_type.file_type})")
        return None
      # Step 2: Extract words
    if verbose:
        print("[2/3] Word Extraction")
    word_extractor = WordExtractor(verbose=False)
    pages_words = word_extractor.extract_pdf_text_based(pdf_path)
    
    if not pages_words or not pages_words[0]:
        print("Error: No words extracted from PDF")
        return None
    
    # Step 3: Layout detection with histogram analysis
    if verbose:
        print("[3/3] Layout Detection with Histogram Analysis\n")
      
    detector = EnhancedLayoutDetector(
        bin_width=5,
        min_gap_width=20,
        min_column_width=80,
        adaptive_threshold=True,
        valley_threshold=0.3,  # Valley must drop below 30% for Type 2 (more sensitive)
        verbose=verbose
    )
    
    # Analyze first page
    layout = detector.detect_layout(pages_words[0])
    
    # Print results
    print("\n" + "="*80)
    print("CLASSIFICATION RESULTS")
    print("="*80)
    print(f"Layout Type: {layout.type_name} (Type {layout.type})")
    print(f"Confidence: {layout.confidence:.1%}")
    print(f"Columns: {layout.num_columns}")
    print(f"Detection Method: {layout.metadata.get('detection_method', 'unknown')}")
    print(f"Column Boundaries: {layout.column_boundaries}")
    
    # Interpretation guide
    print("\n" + "-"*80)
    print("INTERPRETATION GUIDE:")
    print("-"*80)
    if layout.type == 1:
        print("✓ Type 1 (Single Column): Standard vertical flow resume")
    elif layout.type == 2:
        print("✓ Type 2 (Multi-Column): Clean newspaper-style columns")
        print("  - Deep histogram valley (columns well-separated)")
        print("  - Low Y-overlap between columns")
        print("  - Minimal horizontal sections spanning both columns")
    elif layout.type == 3:
        print("✓ Type 3 (Hybrid/Complex): Mixed layout structure")
        print("  - Shallow histogram valley (content crosses columns)")
        print("  - High Y-overlap (side-by-side content at same Y-level)")
        print("  - Horizontal sections mixed with vertical columns")
    
    # Visualize if requested
    if visualize:
        print("\n" + "-"*80)
        print("HISTOGRAM VISUALIZATION")
        print("-"*80)
        save_path = Path(pdf_path).stem + "_histogram.png"
        visualize_histogram(layout, pages_words[0], save_path=save_path, show=True)
    
    print("="*80 + "\n")
    
    return layout


def test_batch(folder_path: str, visualize: bool = False):
    """Test histogram classifier on a batch of resumes"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder not found: {folder_path}")
        return
    
    # Find all PDFs
    pdf_files = list(folder.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in: {folder_path}")
        return
    
    print(f"\n{'='*80}")
    print(f"BATCH TESTING: {len(pdf_files)} PDFs found")
    print(f"{'='*80}\n")
    
    # Track results
    results = {1: [], 2: [], 3: []}
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        print("-"*80)
        
        try:
            layout = test_single_resume(str(pdf_path), visualize=visualize, verbose=False)
            if layout:
                results[layout.type].append(pdf_path.name)
                print(f"✓ Type {layout.type} ({layout.type_name}), Confidence: {layout.confidence:.1%}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("BATCH SUMMARY")
    print("="*80)
    print(f"Type 1 (Single Column): {len(results[1])} files")
    for name in results[1]:
        print(f"  - {name}")
    
    print(f"\nType 2 (Multi-Column): {len(results[2])} files")
    for name in results[2]:
        print(f"  - {name}")
    
    print(f"\nType 3 (Hybrid/Complex): {len(results[3])} files")
    for name in results[3]:
        print(f"  - {name}")
    
    print(f"\nTotal: {sum(len(v) for v in results.values())} files processed")
    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Test histogram-based Type 2/3 classifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test single resume with verbose output
  python test_histogram_classifier.py resume.pdf
  
  # Test with visualization (shows histogram plot)
  python test_histogram_classifier.py resume.pdf --visualize
  
  # Batch test a folder
  python test_histogram_classifier.py --batch ./resumes/ --visualize
        """
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        help='Path to PDF file or folder (if using --batch)'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Process all PDFs in the specified folder'
    )
    
    parser.add_argument(
        '--visualize', '-v',
        action='store_true',
        help='Generate histogram visualization plots'
    )
    
    args = parser.parse_args()
    
    if not args.path:
        parser.print_help()
        return
    
    if args.batch:
        test_batch(args.path, visualize=args.visualize)
    else:
        test_single_resume(args.path, visualize=args.visualize)


if __name__ == "__main__":
    main()
