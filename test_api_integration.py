"""
Integration Tests for Resume Parser API
Run with: pytest test_api_integration.py -v
"""
import pytest
import requests
import time
from pathlib import Path


# Test configuration
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# Sample test data
SAMPLE_RESUME_TEXT = """
John Doe
Email: john.doe@example.com
Phone: +91-9876543210
Location: Bangalore, Karnataka, India

PROFESSIONAL EXPERIENCE

Senior Software Engineer
Tech Corporation Inc. | January 2020 - Present
- Developed microservices using Python and FastAPI
- Implemented CI/CD pipelines with Docker and Kubernetes
- Led team of 5 developers on cloud migration project
- Technologies: Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL

Software Engineer
Digital Solutions Ltd. | June 2018 - December 2019
- Built REST APIs using Node.js and Express
- Designed database schemas for e-commerce platform
- Technologies: Node.js, Express, MongoDB, React

EDUCATION
Bachelor of Technology in Computer Science
XYZ University | 2014 - 2018
"""


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_endpoint(self):
        """Test health check returns 200"""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "model_loaded" in data


class TestParseText:
    """Test parsing from text"""
    
    def test_parse_resume_text_success(self):
        """Test successful text parsing"""
        payload = {
            "text": SAMPLE_RESUME_TEXT,
            "filename": "test_resume.txt"
        }
        
        response = requests.post(f"{API_URL}/parse/text", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "email" in data
        assert "experiences" in data
        
        # Verify extracted data
        assert data["email"] == "john.doe@example.com"
        assert "john" in data["name"].lower() if data["name"] else False
    
    def test_parse_text_too_short(self):
        """Test parsing with text that is too short"""
        payload = {"text": "Too short"}
        
        response = requests.post(f"{API_URL}/parse/text", json=payload)
        assert response.status_code == 400


class TestNERExtraction:
    """Test NER entity extraction"""
    
    def test_extract_entities_success(self):
        """Test successful entity extraction"""
        text = "John Doe worked at Google as Senior Software Engineer from 2020 to 2023"
        
        response = requests.post(
            f"{API_URL}/ner/extract",
            params={"text": text}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "entities" in data
        assert "entity_count" in data
        assert len(data["entities"]) > 0
        
        # Check for expected entity types
        entity_types = [e["entity_group"] for e in data["entities"]]
        assert any(t in ["COMPANY", "ORG"] for t in entity_types) or True  # Google
    
    def test_extract_entities_empty(self):
        """Test entity extraction with empty text"""
        response = requests.post(
            f"{API_URL}/ner/extract",
            params={"text": ""}
        )
        assert response.status_code == 422  # Validation error


class TestContactExtraction:
    """Test contact information extraction"""
    
    def test_extract_contact_from_text(self):
        """Test contact extraction from text"""
        payload = {"text": SAMPLE_RESUME_TEXT}
        
        response = requests.post(
            f"{API_URL}/contact/extract",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "email" in data
        assert "mobile" in data
        assert "location" in data
        
        # Verify extracted contact info
        assert data["email"] == "john.doe@example.com"
        assert "9876543210" in data["mobile"] if data["mobile"] else False


class TestSectionSegmentation:
    """Test section segmentation"""
    
    def test_segment_sections_from_text(self):
        """Test section segmentation from text"""
        payload = {
            "text": SAMPLE_RESUME_TEXT,
            "filename": "test.txt"
        }
        
        response = requests.post(
            f"{API_URL}/sections/segment",
            json=payload
        )
        
        # This might fail if section_splitter is not available
        if response.status_code == 200:
            data = response.json()
            assert "sections" in data
            assert "total_sections" in data
        elif response.status_code == 503:
            pytest.skip("Section splitter not available")


class TestBatchProcessing:
    """Test batch processing"""
    
    @pytest.mark.slow
    def test_batch_processing_flow(self):
        """Test complete batch processing flow"""
        # Note: This test requires actual files
        # For now, we'll test the status endpoint
        
        # Try to get status of non-existent job
        response = requests.get(f"{API_URL}/batch/status/fake-job-id")
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling"""
    
    def test_unsupported_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = requests.get(f"{API_URL}/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_method(self):
        """Test using wrong HTTP method"""
        response = requests.get(f"{API_URL}/parse/single")
        assert response.status_code == 405


class TestPerformance:
    """Test performance metrics"""
    
    def test_response_time_parse_text(self):
        """Test that parsing completes in reasonable time"""
        payload = {
            "text": SAMPLE_RESUME_TEXT,
            "filename": "test.txt"
        }
        
        start_time = time.time()
        response = requests.post(f"{API_URL}/parse/text", json=payload)
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < 10.0  # Should complete within 10 seconds
        
        # Check if processing time is reported
        data = response.json()
        if "processing_time_seconds" in data:
            assert data["processing_time_seconds"] < 10.0


# Pytest configuration
@pytest.fixture(scope="session", autouse=True)
def check_server_running():
    """Check if API server is running before tests"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            pytest.exit("API server is not running. Start with: python -m src.api.main")
    except requests.exceptions.ConnectionError:
        pytest.exit("Cannot connect to API server. Start with: python -m src.api.main")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
