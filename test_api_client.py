"""
Test Client for Resume Parser API
Demonstrates how to use all API endpoints
"""
import requests
import json
import time
from pathlib import Path
from typing import Optional


class ResumeParserClient:
    """Client for Resume Parser API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client with API base URL"""
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
    
    def health_check(self) -> dict:
        """Check API health status"""
        response = requests.get(f"{self.api_url}/health")
        response.raise_for_status()
        return response.json()
    
    def parse_single_resume(self, file_path: str) -> dict:
        """
        Parse a single resume file
        
        Args:
            file_path: Path to resume file
            
        Returns:
            Parsed resume data
        """
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            response = requests.post(
                f"{self.api_url}/parse/single",
                files=files
            )
            response.raise_for_status()
            return response.json()
    
    def parse_text(self, text: str, filename: Optional[str] = None) -> dict:
        """
        Parse resume from text
        
        Args:
            text: Resume text content
            filename: Optional filename
            
        Returns:
            Parsed resume data
        """
        payload = {"text": text}
        if filename:
            payload["filename"] = filename
        
        response = requests.post(
            f"{self.api_url}/parse/text",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def extract_entities(self, text: str) -> dict:
        """
        Extract named entities from text
        
        Args:
            text: Text to analyze
            
        Returns:
            Extracted entities with scores
        """
        response = requests.post(
            f"{self.api_url}/ner/extract",
            params={"text": text}
        )
        response.raise_for_status()
        return response.json()
    
    def segment_sections_file(self, file_path: str) -> dict:
        """
        Segment resume sections from file
        
        Args:
            file_path: Path to resume file
            
        Returns:
            Identified sections
        """
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            response = requests.post(
                f"{self.api_url}/sections/segment",
                files=files
            )
            response.raise_for_status()
            return response.json()
    
    def segment_sections_text(self, text: str, filename: Optional[str] = None) -> dict:
        """
        Segment resume sections from text
        
        Args:
            text: Resume text
            filename: Optional filename
            
        Returns:
            Identified sections
        """
        payload = {"text": text}
        if filename:
            payload["filename"] = filename
        
        response = requests.post(
            f"{self.api_url}/sections/segment",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def extract_contact_info_file(self, file_path: str) -> dict:
        """
        Extract contact information from file
        
        Args:
            file_path: Path to resume file
            
        Returns:
            Contact information
        """
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            response = requests.post(
                f"{self.api_url}/contact/extract",
                files=files
            )
            response.raise_for_status()
            return response.json()
    
    def extract_contact_info_text(self, text: str) -> dict:
        """
        Extract contact information from text
        
        Args:
            text: Resume text
            
        Returns:
            Contact information
        """
        response = requests.post(
            f"{self.api_url}/contact/extract",
            json={"text": text}
        )
        response.raise_for_status()
        return response.json()
    
    def batch_parse(self, file_paths: list) -> str:
        """
        Submit batch processing job
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            Job ID for tracking
        """
        files = []
        for file_path in file_paths:
            files.append(
                ('files', (Path(file_path).name, open(file_path, 'rb')))
            )
        
        try:
            response = requests.post(
                f"{self.api_url}/batch/parse",
                files=files
            )
            response.raise_for_status()
            result = response.json()
            return result['job_id']
        finally:
            # Close all file handles
            for _, (_, f) in files:
                f.close()
    
    def get_batch_status(self, job_id: str) -> dict:
        """
        Get batch job status
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status and results
        """
        response = requests.get(
            f"{self.api_url}/batch/status/{job_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_batch(self, job_id: str, poll_interval: int = 2, timeout: int = 300) -> dict:
        """
        Wait for batch job to complete
        
        Args:
            job_id: Job identifier
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Returns:
            Final job status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_batch_status(job_id)
            
            if status['status'] in ['completed', 'failed']:
                return status
            
            print(f"⏳ Progress: {status['processed_files']}/{status['total_files']} files...")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Batch job {job_id} did not complete within {timeout} seconds")


def main():
    """Demo usage of the client"""
    
    print("=" * 60)
    print("Resume Parser API - Test Client")
    print("=" * 60)
    
    # Initialize client
    client = ResumeParserClient()
    
    # 1. Health Check
    print("\n1️⃣ Health Check")
    print("-" * 60)
    try:
        health = client.health_check()
        print(f"✅ Status: {health['status']}")
        print(f"   Model Loaded: {health['model_loaded']}")
        print(f"   spaCy Available: {health['spacy_available']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 2. Parse Single Resume
    print("\n2️⃣ Parse Single Resume")
    print("-" * 60)
    resume_file = input("Enter path to resume file (or 'skip'): ").strip()
    
    if resume_file != 'skip' and Path(resume_file).exists():
        try:
            result = client.parse_single_resume(resume_file)
            print(f"✅ Parsed: {result['filename']}")
            print(f"   Name: {result['name']}")
            print(f"   Email: {result['email']}")
            print(f"   Experience: {result['total_experience_years']} years")
            print(f"   Role: {result['primary_role']}")
            print(f"   Companies: {len(result['experiences'])}")
            print(f"   Processing Time: {result['processing_time_seconds']}s")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # 3. Extract Entities
    print("\n3️⃣ Extract Named Entities")
    print("-" * 60)
    sample_text = "John Doe worked at Google as Senior Software Engineer from 2020 to 2023, specializing in Python and AWS."
    
    try:
        entities = client.extract_entities(sample_text)
        print(f"✅ Extracted {entities['entity_count']} entities:")
        for entity in entities['entities'][:5]:  # Show first 5
            print(f"   - {entity['word']} ({entity['entity_group']}) - confidence: {entity['score']:.2f}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 4. Extract Contact Info
    print("\n4️⃣ Extract Contact Information")
    print("-" * 60)
    contact_text = """
    John Doe
    Email: john.doe@email.com
    Phone: +91-9876543210
    Location: Bangalore, Karnataka
    """
    
    try:
        contact = client.extract_contact_info_text(contact_text)
        print(f"✅ Contact Information:")
        print(f"   Name: {contact.get('name')}")
        print(f"   Email: {contact.get('email')}")
        print(f"   Mobile: {contact.get('mobile')}")
        print(f"   Location: {contact.get('location')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 5. Batch Processing
    print("\n5️⃣ Batch Processing")
    print("-" * 60)
    batch_files = input("Enter comma-separated file paths for batch (or 'skip'): ").strip()
    
    if batch_files != 'skip':
        file_list = [f.strip() for f in batch_files.split(',') if Path(f.strip()).exists()]
        
        if file_list:
            try:
                job_id = client.batch_parse(file_list)
                print(f"✅ Batch job submitted: {job_id}")
                print(f"   Processing {len(file_list)} files...")
                
                # Wait for completion
                final_status = client.wait_for_batch(job_id)
                
                print(f"\n✅ Batch completed!")
                print(f"   Total: {final_status['total_files']}")
                print(f"   Processed: {final_status['processed_files']}")
                print(f"   Failed: {final_status['failed_files']}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
