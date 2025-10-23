#!/usr/bin/env python3
"""
Check Resume Section Segmentation - Debug tool for single resume files

Usage:
    python check_segmentation.py <path_to_resume.pdf>
    
Example:
    python check_segmentation.py "freshteams_resume/ReactJs/UI_Developer.pdf"
"""

import sys
import json
from pathlib import Path
from src.PDF_pipeline.get_words import get_words_from_pdf
from src.PDF_pipeline.split_columns import split_columns
from src.PDF_pipeline.get_lines import get_column_wise_lines
from src.PDF_pipeline.segment_sections import segment_sections_from_columns


def print_section_details(section):
    """Print detailed information about a section"""
    section_name = section.get('section', 'Unknown')
    lines = section.get('lines', [])
    
    print(f"\n{'='*70}")
    print(f"📑 Section: {section_name}")
    print(f"{'='*70}")
    print(f"Total lines: {len(lines)}")
    
    if lines:
        print(f"\nFirst 5 lines:")
        for i, line in enumerate(lines[:5], 1):
            text = line.get('text', '')[:80]
            print(f"  [{i}] {text}")
        
        if len(lines) > 5:
            print(f"\n  ... ({len(lines) - 5} more lines)")
            print(f"\nLast 3 lines:")
            for i, line in enumerate(lines[-3:], len(lines) - 2):
                text = line.get('text', '')[:80]
                print(f"  [{i}] {text}")


def check_resume_segmentation(resume_path: str, verbose: bool = False, save_json: bool = False):
    """
    Check section segmentation for a single resume
    
    Args:
        resume_path: Path to the resume PDF file
        verbose: Show detailed output
        save_json: Save results to JSON file
    """
    resume_file = Path(resume_path)
    
    if not resume_file.exists():
        print(f"❌ Error: Resume not found: {resume_file}")
        return None
    
    if resume_file.suffix.lower() != '.pdf':
        print(f"❌ Error: Only PDF files are supported. Got: {resume_file.suffix}")
        return None
    
    print(f"\n🔍 Analyzing: {resume_file.name}")
    print(f"📂 Full path: {resume_file}")
    print("="*70)
    
    try:
        # Step 1: Extract words
        print("\n1️⃣  Extracting words from PDF...")
        pages = get_words_from_pdf(str(resume_file))
        print(f"   ✅ Extracted {len(pages)} page(s)")
        
        if not pages:
            print("   ❌ No pages extracted!")
            return None
        
        # Step 2: Split columns
        print("\n2️⃣  Detecting columns...")
        columns = split_columns(pages, min_words_per_column=10, dynamic_min_words=True)
        print(f"   ✅ Found {len(columns)} column(s)")
        
        if verbose:
            for i, col in enumerate(columns, 1):
                words = col.get('words', [])
                print(f"      Column {i}: {len(words)} words")
        
        # Step 3: Build lines
        print("\n3️⃣  Building text lines...")
        columns_with_lines = get_column_wise_lines(columns, y_tolerance=1.0)
        print(f"   ✅ Built lines for {len(columns_with_lines)} column(s)")
        
        # Step 4: Segment sections
        print("\n4️⃣  Segmenting sections...")
        result = segment_sections_from_columns(columns_with_lines)
        
        sections = result.get('sections', [])
        print(f"   ✅ Found {len(sections)} section(s)")
        
        # Display summary
        print("\n" + "="*70)
        print("📊 SEGMENTATION SUMMARY")
        print("="*70)
        
        section_names = [s.get('section', 'Unknown') for s in sections]
        for i, section_name in enumerate(section_names, 1):
            lines_count = len(sections[i-1].get('lines', []))
            print(f"  {i}. {section_name:<30} ({lines_count} lines)")
        
        # Show detailed view for each section
        if verbose:
            for section in sections:
                print_section_details(section)
        
        # Save to JSON if requested
        if save_json:
            output_file = resume_file.stem + "_segmentation.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Saved segmentation to: {output_file}")
        
        print("\n" + "="*70)
        print("✅ Analysis complete!")
        print("="*70)
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n❌ Error: Please provide a resume file path")
        print("\nExamples:")
        print('  python check_segmentation.py "freshteams_resume/ReactJs/UI_Developer.pdf"')
        print('  python check_segmentation.py "freshteams_resume/Backend Java Developer/JavaDeveloper.pdf" --verbose')
        print('  python check_segmentation.py resume.pdf --save-json')
        sys.exit(1)
    
    resume_path = sys.argv[1]
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    save_json = '--save-json' in sys.argv or '--json' in sys.argv
    
    result = check_resume_segmentation(resume_path, verbose=verbose, save_json=save_json)
    
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
