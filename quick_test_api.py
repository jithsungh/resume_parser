#!/usr/bin/env python3
"""
Quick test to verify the API is working with smart parser
"""
import requests
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """Test health endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Make sure the server is running:")
        print("  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        return False

def test_parse_single(pdf_path):
    """Test single resume parsing"""
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return False
    
    print(f"\nTesting /parse/single with {Path(pdf_path).name}...")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/parse/single", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Parsing successful!")
            print(f"   Name: {result.get('name')}")
            print(f"   Email: {result.get('email')}")
            print(f"   Experience: {result.get('total_experience_years')} years")
            
            if result.get('metadata'):
                print(f"   Smart Parser: {result['metadata'].get('smart_parser_used', False)}")
                print(f"   Pipeline: {result['metadata'].get('pipeline_used')}")
                print(f"   Sections: {result['metadata'].get('sections_detected')}")
            
            return True
        else:
            print(f"❌ Parsing failed: {response.status_code}")
            print(f"   Error: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_smart_parse(pdf_path):
    """Test smart parsing endpoint"""
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return False
    
    print(f"\nTesting /parse/smart with {Path(pdf_path).name}...")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/parse/smart", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Smart parsing successful!")
            print(f"   Sections: {len(result.get('sections', []))}")
            print(f"   Pipeline: {result['metadata'].get('pipeline_used')}")
            print(f"   Processing time: {result['metadata'].get('processing_time'):.2f}s")
            
            # Print section summary
            for section in result.get('sections', [])[:5]:
                lines_count = len(section.get('lines', []))
                print(f"     - {section['section_name']}: {lines_count} lines")
            
            return True
        else:
            print(f"❌ Smart parsing failed: {response.status_code}")
            print(f"   Error: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("="*60)
    print("Resume Parser API - Quick Test")
    print("="*60)
    
    # Test health
    if not test_health():
        sys.exit(1)
    
    # Find a test PDF
    test_files = [
        "freshteams_resume/Resumes/Nikhil_Matta.pdf",
        "freshteams_resume/Resumes/QA_Resume_Pravallika.pdf",
        "freshteams_resume/Resumes/Vishnu_Sunil_CV.pdf",
    ]
    
    test_pdf = None
    for pdf in test_files:
        if Path(pdf).exists():
            test_pdf = pdf
            break
    
    if not test_pdf:
        print("\n❌ No test PDFs found. Please place a resume PDF in freshteams_resume/Resumes/")
        sys.exit(1)
    
    # Test endpoints
    parse_ok = test_parse_single(test_pdf)
    smart_ok = test_smart_parse(test_pdf)
    
    print("\n" + "="*60)
    if parse_ok and smart_ok:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("="*60)

if __name__ == "__main__":
    main()
