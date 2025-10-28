"""
Debug Histogram Analysis
=========================
Analyzes histogram values to understand valley depths for Type 2 vs Type 3 classification
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
from src.core.layout_detector_y_overlap import EnhancedLayoutDetector
import numpy as np


def analyze_histogram(file_path: str):
    """Analyze histogram in detail"""
    print(f"\n{'='*80}")
    print(f"HISTOGRAM ANALYSIS: {Path(file_path).name}")
    print(f"{'='*80}\n")
    
    # Extract words
    doc_detector = DocumentDetector()
    doc_type = doc_detector.detect(file_path)
    
    word_extractor = WordExtractor()
    if doc_type.recommended_extraction == 'ocr':
        pages = word_extractor.extract_pdf_ocr(file_path)
    else:
        pages = word_extractor.extract_pdf_text_based(file_path)
    
    if not pages or not pages[0]:
        print("No words found!")
        return
    
    words = pages[0]
    page_width = max(w.bbox[2] for w in words) + 10
    
    print(f"Words: {len(words)}")
    print(f"Page width: {page_width:.1f}")
    print()
    
    # Create detector
    detector = EnhancedLayoutDetector(verbose=True)
    
    # Detect layout
    layout = detector.detect_layout(words, page_width)
    
    print(f"\n{'─'*80}")
    print("HISTOGRAM DETAILS")
    print(f"{'─'*80}")
    
    # Analyze histogram
    histogram = layout.histogram
    if not histogram:
        print("No histogram data")
        return
    
    bins = sorted(histogram.keys())
    values = [histogram[b] for b in bins]
    
    print(f"Histogram bins: {len(bins)}")
    print(f"Max value: {max(values)}")
    print(f"Min value: {min(values)}")
    print(f"Mean value: {np.mean(values):.2f}")
    print()
    
    # Find valleys (bins with low values)
    mean_val = np.mean(values)
    valleys_10pct = [b for b in bins if histogram[b] < mean_val * 0.10]
    valleys_20pct = [b for b in bins if histogram[b] < mean_val * 0.20]
    valleys_30pct = [b for b in bins if histogram[b] < mean_val * 0.30]
    
    print(f"Bins below 10% of mean ({mean_val*0.10:.1f}): {len(valleys_10pct)}")
    print(f"Bins below 20% of mean ({mean_val*0.20:.1f}): {len(valleys_20pct)}")
    print(f"Bins below 30% of mean ({mean_val*0.30:.1f}): {len(valleys_30pct)}")
    print()
    
    # Check for consecutive low-value bins (potential column gaps)
    consecutive_zeros = 0
    max_consecutive_zeros = 0
    zero_threshold = mean_val * 0.10
    
    for b in bins:
        if histogram[b] <= zero_threshold:
            consecutive_zeros += 1
            max_consecutive_zeros = max(max_consecutive_zeros, consecutive_zeros)
        else:
            consecutive_zeros = 0
    
    print(f"Max consecutive bins near 0: {max_consecutive_zeros}")
    print(f"  (Indicates gap width: ~{max_consecutive_zeros * detector.bin_width:.1f}pt)")
    print()
    
    # ASCII histogram visualization
    print("ASCII Histogram (X-axis):")
    print(f"{'─'*80}")
    
    # Normalize values to 20 rows
    max_val = max(values)
    heights = [int((v / max_val) * 20) if max_val > 0 else 0 for v in values]
    
    # Print from top to bottom
    for row in range(20, 0, -1):
        line = ""
        for h in heights:
            if h >= row:
                line += "█"
            else:
                line += " "
        print(line[:80])  # Limit to 80 chars
    
    # X-axis labels
    print("─" * 80)
    print(f"0{' ' * 35}{page_width/2:.0f}{' ' * 35}{page_width:.0f}")
    print()
    
    # Find deepest valley
    if len(layout.peaks) >= 2:
        print("Valley Analysis Between Peaks:")
        print(f"{'─'*80}")
        
        for i in range(len(layout.peaks) - 1):
            peak1_bin = layout.peaks[i]
            peak2_bin = layout.peaks[i + 1]
            
            peak1_x = peak1_bin * detector.bin_width
            peak2_x = peak2_bin * detector.bin_width
            
            # Find minimum between peaks
            min_val = float('inf')
            min_bin = peak1_bin
            for b in range(peak1_bin, peak2_bin + 1):
                if b in histogram and histogram[b] < min_val:
                    min_val = histogram[b]
                    min_bin = b
            
            valley_x = min_bin * detector.bin_width
            peak1_val = histogram.get(peak1_bin, 0)
            peak2_val = histogram.get(peak2_bin, 0)
            
            ratio = min_val / max(peak1_val, peak2_val) if max(peak1_val, peak2_val) > 0 else 1.0
            
            print(f"  Valley {i+1}:")
            print(f"    Between peaks at x={peak1_x:.1f} and x={peak2_x:.1f}")
            print(f"    Valley at x={valley_x:.1f}")
            print(f"    Valley value: {min_val:.1f}")
            print(f"    Peak values: {peak1_val:.1f}, {peak2_val:.1f}")
            print(f"    Valley/Peak ratio: {ratio:.1%}")
            
            if ratio < 0.10:
                print(f"    ✓ DEEP VALLEY (Type 2 indicator)")
            elif ratio < 0.30:
                print(f"    ○ Moderate valley (Type 3 indicator)")
            else:
                print(f"    ✗ Shallow valley (Type 1/3 indicator)")
            print()
    
    # Final classification
    print(f"\n{'='*80}")
    print("CLASSIFICATION")
    print(f"{'='*80}")
    print(f"Layout Type: {layout.type_name} (Type {layout.type})")
    print(f"Columns: {layout.num_columns}")
    print(f"Confidence: {layout.confidence:.1%}")
    print(f"Detection method: {layout.metadata.get('detection_method', 'unknown')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_histogram_analysis.py <pdf_file>")
        sys.exit(1)
    
    analyze_histogram(sys.argv[1])
