"""
Test script for Smart Resume Parser API
Tests the new layout-aware parsing endpoints
"""
import requests
import json
import time
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """Test health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_smart_parse_single(pdf_path: str):
    """Test smart parsing for single resume"""
    print(f"Testing smart parse: {Path(pdf_path).name}")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/parse/smart", files=files)
        elapsed = time.time() - start
        
        print(f"Status: {response.status_code}")
        print(f"Time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            print(f"Filename: {result.get('filename')}")
            print(f"Pipeline used: {result['metadata']['pipeline_used']}")
            print(f"Processing time: {result['metadata']['processing_time']:.2f}s")
            print(f"Sections found: {len(result['sections'])}")
            
            # Print sections
            for section in result['sections']:
                lines_count = len(section.get('lines', []))
                print(f"  - {section['section_name']}: {lines_count} lines")
            
            print("\nSimplified output sample:")
            simplified = json.loads(result['simplified_output'])
            for section in simplified[:2]:  # First 2 sections
                print(f"\n  {section['section']}:")
                for line in section['lines'][:3]:  # First 3 lines
                    print(f"    - {line}")
        else:
            print(f"Error: {response.json()}")
    print()

def test_smart_parse_force_pdf(pdf_path: str):
    """Test smart parsing with forced PDF pipeline"""
    print(f"Testing smart parse (forced PDF): {Path(pdf_path).name}")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        params = {'force_pipeline': 'pdf'}
        
        response = requests.post(f"{BASE_URL}/parse/smart", files=files, params=params)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Pipeline used: {result['metadata']['pipeline_used']}")
            print(f"Sections: {len(result['sections'])}")
        else:
            print(f"Error: {response.json()}")
    print()

def test_smart_parse_force_ocr(pdf_path: str):
    """Test smart parsing with forced OCR pipeline"""
    print(f"Testing smart parse (forced OCR): {Path(pdf_path).name}")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        params = {'force_pipeline': 'ocr'}
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/parse/smart", files=files, params=params)
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Pipeline used: {result['metadata']['pipeline_used']}")
            print(f"Sections: {len(result['sections'])}")
        else:
            print(f"Error: {response.json()}")
    print()

def test_batch_smart_parse(pdf_paths: list):
    """Test batch smart parsing"""
    print(f"Testing batch smart parse: {len(pdf_paths)} files")
    
    files = []
    for path in pdf_paths:
        files.append(('files', (Path(path).name, open(path, 'rb'), 'application/pdf')))
    
    try:
        response = requests.post(f"{BASE_URL}/batch/smart-parse", files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            job_id = result['job_id']
            print(f"Job ID: {job_id}")
            print(f"Total files: {result['total_files']}")
            print(f"Estimated time: {result['estimated_time_seconds']}s")
            
            # Poll for status
            print("\nPolling for completion...")
            max_polls = 60
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(2)
                status_response = requests.get(f"{BASE_URL}/batch/status/{job_id}")
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"  Status: {status['status']} | Completed: {status['completed']}/{status['total']} | Failed: {status['failed']}")
                    
                    if status['status'] in ['completed', 'failed']:
                        print("\nFinal results:")
                        print(f"  Total: {status['total']}")
                        print(f"  Completed: {status['completed']}")
                        print(f"  Failed: {status['failed']}")
                        
                        if status['results']:
                            print("\nSample results:")
                            for result in status['results'][:2]:
                                print(f"  - {result['filename']}: {len(result.get('sections', []))} sections, pipeline: {result.get('pipeline_used')}")
                        
                        if status['errors']:
                            print("\nErrors:")
                            for error in status['errors']:
                                print(f"  - {error['filename']}: {error['error']}")
                        break
                
                poll_count += 1
            
            if poll_count >= max_polls:
                print("Polling timeout")
        else:
            print(f"Error: {response.json()}")
    finally:
        # Close file handles
        for _, file_tuple in files:
            file_tuple[1].close()
    
    print()

def main():
    """Run all tests"""
    print("="*60)
    print("Smart Resume Parser API Tests")
    print("="*60)
    print()
    
    # Check if server is running
    try:
        test_health()
    except requests.exceptions.ConnectionError:
        print("❌ Error: API server not running!")
        print("Start the server with: python -m src.api")
        return
    
    # Test files
    test_files = [
        "freshteams_resume/Resumes/Nikhil_Matta.pdf",
        "freshteams_resume/Resumes/QA_Resume_Pravallika.pdf",
        "freshteams_resume/Resumes/Vishnu_Sunil_CV.pdf",
    ]
    
    # Check if test files exist
    existing_files = [f for f in test_files if Path(f).exists()]
    
    if not existing_files:
        print("❌ No test files found. Please place resume PDFs in freshteams_resume/Resumes/")
        return
    
    print(f"Found {len(existing_files)} test files\n")
    
    # Test single file parsing
    if existing_files:
        test_smart_parse_single(existing_files[0])
        
        # Test with forced pipelines
        # test_smart_parse_force_pdf(existing_files[0])
        # test_smart_parse_force_ocr(existing_files[0])
    
    # Test batch parsing
    if len(existing_files) >= 2:
        test_batch_smart_parse(existing_files[:3])
    
    print("="*60)
    print("Tests completed!")
    print("="*60)

if __name__ == "__main__":
    main()
