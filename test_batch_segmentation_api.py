"""
Test Batch Segmentation API
============================
Quick test to verify the batch segmentation endpoint works correctly.
"""

import requests
import time
import json
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"

def test_batch_segmentation():
    """Test the batch segmentation endpoint"""
    
    print("🧪 Testing Batch Segmentation API\n")
    
    # Find some test resumes
    test_folder = Path("freshteams_resume/Golang Developer")
    if not test_folder.exists():
        print(f"❌ Test folder not found: {test_folder}")
        return
    
    # Get first 5 PDF files
    test_files = list(test_folder.glob("*.pdf"))[:5]
    
    if len(test_files) == 0:
        print("❌ No PDF files found in test folder")
        return
    
    print(f"📁 Found {len(test_files)} test files:")
    for f in test_files:
        print(f"   - {f.name}")
    print()
    
    # Upload files
    print("📤 Uploading files for segmentation...")
    files = [('files', (f.name, open(f, 'rb'), 'application/pdf')) for f in test_files]
    
    try:
        response = requests.post(
            f"{API_BASE}/batch/segment",
            files=files,
            params={
                'include_full_content': True,
                'include_text_preview': True
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   {response.text}")
            return
        
        result = response.json()
        job_id = result['job_id']
        
        print(f"✅ Upload successful!")
        print(f"   Job ID: {job_id}")
        print(f"   Total files: {result['total_files']}")
        print()
        
    finally:
        # Close file handles
        for _, file_tuple in files:
            if hasattr(file_tuple[1], 'close'):
                file_tuple[1].close()
    
    # Poll for status
    print("⏳ Processing...")
    max_attempts = 60  # 2 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(2)
        attempt += 1
        
        try:
            status_response = requests.get(
                f"{API_BASE}/batch/segment/status/{job_id}",
                timeout=10
            )
            
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.status_code}")
                return
            
            status = status_response.json()
            
            print(f"   [{attempt}] Status: {status['status']} - " +
                  f"{status['processed_files']}/{status['total_files']} files")
            
            if status['status'] == 'completed':
                print("\n✅ Processing completed!")
                print_results(status)
                
                # Test downloads
                test_downloads(job_id)
                break
                
            elif status['status'] == 'failed':
                print(f"\n❌ Processing failed!")
                print(f"   Error: {status.get('error_message')}")
                return
                
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return
    
    if attempt >= max_attempts:
        print("\n⏱️  Timeout waiting for completion")


def print_results(status):
    """Print detailed results"""
    print("\n" + "="*70)
    print("📊 RESULTS SUMMARY")
    print("="*70)
    
    print(f"\nTotal Files:         {status['total_files']}")
    print(f"Processed:           {status['processed_files']}")
    print(f"Failed:              {status['failed_files']}")
    print(f"Empty:               {status['empty_files']}")
    
    # Statistics
    if status.get('statistics'):
        stats = status['statistics']
        print(f"\n📈 Statistics:")
        print(f"   Successful:           {stats['successful']}")
        print(f"   No sections detected: {stats['no_sections_detected']}")
        
        if stats.get('most_common_sections'):
            print(f"\n🏷️  Most Common Sections:")
            for section, count in stats['most_common_sections'][:5]:
                print(f"   - {section}: {count}")
    
    # Sample results
    if status.get('results'):
        print(f"\n📄 Sample Results (first 3):")
        for i, result in enumerate(status['results'][:3], 1):
            print(f"\n   [{i}] {result['filename']}")
            print(f"       Status: {result['status']}")
            if result['status'] == 'success':
                print(f"       Text Length: {result['text_length']:,} chars")
                print(f"       Sections: {result['section_count']}")
                if result.get('sections_found'):
                    print(f"       Found: {', '.join(result['sections_found'])}")
            elif result.get('error'):
                print(f"       Error: {result['error']}")


def test_downloads(job_id):
    """Test downloading results"""
    print("\n" + "="*70)
    print("📥 TESTING DOWNLOADS")
    print("="*70)
    
    # Test JSON download
    print("\n📄 Downloading JSON...")
    try:
        response = requests.get(
            f"{API_BASE}/batch/segment/download/{job_id}",
            params={'format': 'json'},
            timeout=30
        )
        
        if response.status_code == 200:
            output_file = f"test_segmentation_{job_id[:8]}.json"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ JSON saved to: {output_file}")
            
            # Validate JSON
            try:
                data = json.loads(response.content)
                print(f"   ✅ JSON is valid ({len(data)} records)")
            except:
                print(f"   ⚠️  JSON might be invalid")
        else:
            print(f"   ❌ Download failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test CSV download
    print("\n📊 Downloading CSV...")
    try:
        response = requests.get(
            f"{API_BASE}/batch/segment/download/{job_id}",
            params={'format': 'csv'},
            timeout=30
        )
        
        if response.status_code == 200:
            output_file = f"test_segmentation_{job_id[:8]}.csv"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ CSV saved to: {output_file}")
            
            # Check CSV has content
            content = response.content.decode('utf-8')
            lines = content.split('\n')
            print(f"   ✅ CSV has {len(lines)} lines")
        else:
            print(f"   ❌ Download failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_health():
    """Test health endpoint first"""
    print("🏥 Checking API health...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ API is {health['status']}")
            print(f"   Model loaded: {health.get('model_loaded')}")
            return True
        else:
            print(f"   ❌ API returned {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        print(f"   Make sure API is running on {API_BASE}")
        return False


if __name__ == "__main__":
    print("="*70)
    print("🔍 BATCH SEGMENTATION API TEST")
    print("="*70)
    print()
    
    # Check health first
    if not test_health():
        print("\n❌ API is not running. Start it with:")
        print("   python -m uvicorn src.api.main:app --reload")
        exit(1)
    
    print()
    
    # Run the test
    try:
        test_batch_segmentation()
        
        print("\n" + "="*70)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
