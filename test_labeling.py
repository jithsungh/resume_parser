"""
Quick test script for resume labeling system
Tests feature extraction on a single PDF
"""

from pathlib import Path
from resume_feature_extractor import ResumeFeatureExtractor
import sys


def test_feature_extraction(pdf_path: str):
    """Test feature extraction on a single PDF"""
    
    print(f"Testing feature extraction on: {pdf_path}")
    print("=" * 80)
    
    extractor = ResumeFeatureExtractor(verbose=True)
    
    # Extract words and bounding boxes
    print("\n[1] Extracting words and bounding boxes...")
    words, page_width, page_height = extractor.extract_words_and_bbox(pdf_path)
    print(f"✓ Extracted {len(words)} words")
    print(f"✓ Page dimensions: {page_width:.1f} x {page_height:.1f}")
    
    # Compute features
    print("\n[2] Computing layout features...")
    features = extractor.compute_features(words, page_width, page_height)
    
    print("\n[3] Feature Summary:")
    print("=" * 80)
    features_dict = features.to_dict()
    
    print("\n📊 Column Detection:")
    print(f"  • Number of Columns: {features_dict['num_columns']}")
    print(f"  • Gutter Coverage: {features_dict['coverage_gutter']:.4f}")
    print(f"  • Valley Depth Ratio: {features_dict['valley_depth_ratio']:.4f}")
    
    print("\n📐 Layout Structure:")
    print(f"  • Full-Width Line Ratio: {features_dict['full_width_line_ratio']:.4f}")
    print(f"  • Horizontal Lines Count: {features_dict['horizontal_lines_count']}")
    print(f"  • Header Fraction: {features_dict['header_fraction']:.4f}")
    
    print("\n📝 Text Distribution:")
    print(f"  • Mean Y-Overlap: {features_dict['mean_y_overlap']:.4f}")
    print(f"  • Avg Word Width Ratio: {features_dict['avg_word_width_ratio']:.4f}")
    print(f"  • Line Density Variance: {features_dict['line_density_variance']:.4f}")
    
    print("\n" + "=" * 80)
    print("✓ Feature extraction successful!")
    
    # Suggest layout type based on features
    if features_dict['num_columns'] == 1:
        suggested_type = "Type 1 (Single Column)"
    elif features_dict['coverage_gutter'] >= 0.7 and features_dict['full_width_line_ratio'] < 0.15:
        suggested_type = "Type 2 (Multi-Column)"
    else:
        suggested_type = "Type 3 (Hybrid/Complex)"
    
    print(f"\n💡 Suggested Layout Type: {suggested_type}")
    print("=" * 80)


def main():
    # Test with a sample PDF
    test_pdfs = [
        "./freshteams_resume/Resumes/1.pdf",
        "./freshteams_resume/Resumes/2.pdf",
        "./freshteams_resume/Resumes/3.pdf",
    ]
    
    # Find first existing PDF
    for pdf_path in test_pdfs:
        if Path(pdf_path).exists():
            test_feature_extraction(pdf_path)
            return
    
    # If no test PDFs found, ask user
    print("No test PDFs found in default locations.")
    print("\nUsage: python test_labeling.py [path/to/resume.pdf]")
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if Path(pdf_path).exists():
            test_feature_extraction(pdf_path)
        else:
            print(f"Error: PDF not found: {pdf_path}")
    else:
        # Try to find any PDF in freshteams_resume directory
        resume_dir = Path("./freshteams_resume/Resumes")
        if resume_dir.exists():
            pdfs = list(resume_dir.glob("*.pdf"))
            if pdfs:
                print(f"\nFound {len(pdfs)} PDFs in {resume_dir}")
                print(f"Testing first PDF: {pdfs[0].name}\n")
                test_feature_extraction(str(pdfs[0]))
            else:
                print(f"No PDFs found in {resume_dir}")


if __name__ == "__main__":
    main()
