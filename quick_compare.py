#!/usr/bin/env python3
"""
Quick comparison script between PDF pipeline and IMG (OCR) pipeline
"""

import sys
import json
from pathlib import Path

from src.PDF_pipeline.pipeline import run_pipeline
from src.IMG_pipeline.pipeline import run_pipeline_ocr


def compare_pipelines(pdf_path: str):
    """Compare PDF and IMG pipelines side by side."""
    
    print("=" * 80)
    print(f"Comparing pipelines on: {pdf_path}")
    print("=" * 80)
    
    # Run PDF pipeline
    print("\n[1] PDF PIPELINE (PyMuPDF)")
    print("-" * 80)
    try:
        result_pdf, _ = run_pipeline(pdf_path, verbose=True)
        
        pdf_sections = result_pdf.get('sections', [])
        print(f"\nFound {len(pdf_sections)} sections:")
        for sec in pdf_sections:
            print(f"  - {sec['section']}: {len(sec['lines'])} lines")
            
    except Exception as e:
        print(f"PDF pipeline failed: {e}")
        result_pdf = None
    
    # Run IMG/OCR pipeline
    print("\n[2] IMG PIPELINE (EasyOCR)")
    print("-" * 80)
    try:
        result_ocr, _ = run_pipeline_ocr(
            pdf_path, 
            dpi=200,  # Lower DPI for speed
            verbose=True,
            gpu=False
        )
        
        ocr_sections = result_ocr.get('sections', [])
        print(f"\nFound {len(ocr_sections)} sections:")
        for sec in ocr_sections:
            print(f"  - {sec['section']}: {len(sec['lines'])} lines")
            
    except Exception as e:
        print(f"IMG pipeline failed: {e}")
        result_ocr = None
    
    # Compare
    if result_pdf and result_ocr:
        print("\n[3] COMPARISON")
        print("-" * 80)
        
        pdf_section_names = set(s['section'] for s in result_pdf.get('sections', []))
        ocr_section_names = set(s['section'] for s in result_ocr.get('sections', []))
        
        common = pdf_section_names & ocr_section_names
        only_pdf = pdf_section_names - ocr_section_names
        only_ocr = ocr_section_names - pdf_section_names
        
        print(f"\nCommon sections ({len(common)}):")
        for sec in sorted(common):
            print(f"  ✓ {sec}")
        
        if only_pdf:
            print(f"\nOnly in PDF pipeline ({len(only_pdf)}):")
            for sec in sorted(only_pdf):
                print(f"  + {sec}")
        
        if only_ocr:
            print(f"\nOnly in OCR pipeline ({len(only_ocr)}):")
            for sec in sorted(only_ocr):
                print(f"  + {sec}")
        
        # Total lines
        pdf_lines = sum(len(s['lines']) for s in result_pdf.get('sections', []))
        ocr_lines = sum(len(s['lines']) for s in result_ocr.get('sections', []))
        
        print(f"\nTotal lines extracted:")
        print(f"  PDF: {pdf_lines}")
        print(f"  OCR: {ocr_lines}")
        
        # Contact info comparison
        pdf_contact = result_pdf.get('contact', {})
        ocr_contact = result_ocr.get('contact', {})
        
        print(f"\nContact information:")
        print(f"  PDF: {json.dumps(pdf_contact, indent=6)}")
        print(f"  OCR: {json.dumps(ocr_contact, indent=6)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_compare.py <path_to_pdf>")
        print("\nExample:")
        print("  python quick_compare.py freshteams_resume/Resumes/Gaganasri-M-FullStack_1.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    compare_pipelines(pdf_path)
