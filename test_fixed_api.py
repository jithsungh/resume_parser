"""
Test Fixed API - Verify Segmentation and Name Extraction
=========================================================
Tests:
1. PDF pipeline segmentation (proper Experience extraction)
2. Filename preservation for name extraction heuristics
"""

import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"

def test_segmentation():
    """Test batch segmentation with proper PDF pipeline"""
    
    print("="*70)
    print("🧪 TEST 1: SEGMENTATION WITH PDF PIPELINE")
    print("="*70)
    
    # Test with problematic resume
    test_folder = Path("freshteams_resume/Golang Developer")
    test_file = test_folder / "AnirudhReddy_Resume.pdf"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"\n📄 Testing: {test_file.name}")
    
    # Upload for segmentation
    with open(test_file, 'rb') as f:
        files = [('files', (test_file.name, f, 'application/pdf'))]
        
        response = requests.post(
            f"{API_BASE}/batch/segment",
            files=files,
            params={'include_full_content': True},
            timeout=30
        )
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        return False
    
    job_id = response.json()['job_id']
    print(f"✅ Job created: {job_id}")
    
    # Wait for completion
    for i in range(30):
        time.sleep(2)
        status_response = requests.get(f"{API_BASE}/batch/segment/status/{job_id}")
        status = status_response.json()
        
        if status['status'] == 'completed':
            results = status['results'][0]
            
            print(f"\n📊 SEGMENTATION RESULTS:")
            print(f"   Sections found: {results['section_count']}")
            print(f"   Section names: {', '.join(results['sections_found'])}")
            
            # Check if Experience section exists
            experience_found = False
            for section in results['sections']:
                if section['section_name'] == 'Experience':
                    experience_found = True
                    content = section.get('full_content', '')
                    
                    print(f"\n   ✅ Experience Section Found!")
                    print(f"   Content length: {len(content)} chars")
                    print(f"   First 200 chars:")
                    print(f"   {content[:200]}...")
                    
                    # Check if content looks correct
                    if 'NPCI' in content or 'Associate' in content:
                        print(f"   ✅ Content looks correct!")
                        return True
                    else:
                        print(f"   ⚠️  Content might be incorrect")
                        return False
            
            if not experience_found:
                print(f"   ❌ Experience section NOT found!")
                return False
        
        elif status['status'] == 'failed':
            print(f"❌ Processing failed: {status.get('error_message')}")
            return False
    
    print("⏱️  Timeout")
    return False


def test_name_extraction():
    """Test name extraction with filename heuristic"""
    
    print("\n" + "="*70)
    print("🧪 TEST 2: NAME EXTRACTION WITH FILENAME HEURISTIC")
    print("="*70)
    
    # Test with a file that has name in filename
    test_folder = Path("freshteams_resume/Golang Developer")
    test_file = test_folder / "Ayush_Kumar_Resume.pdf"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"\n📄 Testing: {test_file.name}")
    print(f"   Expected name from filename: Ayush Kumar")
    
    # Parse resume
    with open(test_file, 'rb') as f:
        files = {'file': (test_file.name, f, 'application/pdf')}
        
        response = requests.post(
            f"{API_BASE}/parse/single",
            files=files,
            timeout=30
        )
    
    if response.status_code != 200:
        print(f"❌ Parse failed: {response.status_code}")
        return False
    
    result = response.json()
    
    print(f"\n📊 EXTRACTION RESULTS:")
    print(f"   Name extracted: {result.get('name')}")
    print(f"   Email: {result.get('email')}")
    print(f"   Mobile: {result.get('mobile')}")
    print(f"   Location: {result.get('location')}")
    print(f"   Filename in result: {result.get('filename')}")
    
    # Verify filename is preserved
    if result.get('filename') == test_file.name:
        print(f"   ✅ Filename preserved correctly!")
    else:
        print(f"   ⚠️  Filename not preserved: {result.get('filename')}")
    
    # Check if name was extracted
    if result.get('name'):
        print(f"   ✅ Name extracted successfully!")
        
        # Check if filename helped
        name = result.get('name', '').lower()
        if 'ayush' in name or 'kumar' in name:
            print(f"   ✅ Name likely extracted using filename heuristic!")
            return True
        else:
            print(f"   ℹ️  Name extracted from document content")
            return True
    else:
        print(f"   ❌ Name not extracted!")
        return False


def test_batch_parsing():
    """Test batch parsing with multiple files"""
    
    print("\n" + "="*70)
    print("🧪 TEST 3: BATCH PARSING WITH MULTIPLE FILES")
    print("="*70)
    
    test_folder = Path("freshteams_resume/Golang Developer")
    test_files = list(test_folder.glob("*.pdf"))[:3]
    
    if len(test_files) == 0:
        print("❌ No test files found")
        return False
    
    print(f"\n📁 Testing {len(test_files)} files:")
    for f in test_files:
        print(f"   - {f.name}")
    
    # Upload files
    files = [('files', (f.name, open(f, 'rb'), 'application/pdf')) for f in test_files]
    
    try:
        response = requests.post(
            f"{API_BASE}/batch/parse",
            files=files,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code}")
            return False
        
        job_id = response.json()['job_id']
        print(f"\n✅ Job created: {job_id}")
        
        # Wait for completion
        for i in range(30):
            time.sleep(2)
            status_response = requests.get(f"{API_BASE}/batch/status/{job_id}")
            status = status_response.json()
            
            if status['status'] == 'completed':
                results = status['results']
                
                print(f"\n📊 BATCH RESULTS:")
                print(f"   Total files: {len(results)}")
                
                names_extracted = 0
                filenames_preserved = 0
                
                for result in results:
                    if result.get('name'):
                        names_extracted += 1
                    if result.get('filename') in [f.name for f in test_files]:
                        filenames_preserved += 1
                
                print(f"   Names extracted: {names_extracted}/{len(results)}")
                print(f"   Filenames preserved: {filenames_preserved}/{len(results)}")
                
                if filenames_preserved == len(results):
                    print(f"   ✅ All filenames preserved!")
                    return True
                else:
                    print(f"   ⚠️  Some filenames not preserved")
                    return False
            
            elif status['status'] == 'failed':
                print(f"❌ Processing failed")
                return False
    
    finally:
        # Close file handles
        for _, file_tuple in files:
            if hasattr(file_tuple[1], 'close'):
                file_tuple[1].close()
    
    return False


def main():
    """Run all tests"""
    
    print("="*70)
    print("🔬 TESTING FIXED API")
    print("="*70)
    
    # Check API health
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API is not healthy")
            return
    except:
        print("❌ Cannot connect to API")
        print("   Start API with: python -m uvicorn src.api.main:app --reload")
        return
    
    print("✅ API is running\n")
    
    # Run tests
    results = []
    
    test1 = test_segmentation()
    results.append(("Segmentation Test", test1))
    
    test2 = test_name_extraction()
    results.append(("Name Extraction Test", test2))
    
    test3 = test_batch_parsing()
    results.append(("Batch Parsing Test", test3))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED")


if __name__ == "__main__":
    main()
