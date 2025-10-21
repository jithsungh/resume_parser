"""
Test script for enhanced name and location extraction
Tests multiple strategies: spaCy, heuristics, email, filename
"""

from src.core.name_location_extractor import NameLocationExtractor

# Test data
test_resume = """John Michael Smith
Email: john.smith@techcorp.com | Mobile: +91-9876543210
Location: Bangalore, Karnataka

PROFESSIONAL SUMMARY
Software Engineer with 5+ years of experience in full-stack development...

WORK EXPERIENCE
Senior Software Engineer - Tech Solutions Pvt Ltd
Jan 2020 - Present
• Developed and maintained web applications using React.js and Node.js
• Led a team of 5 developers

Software Developer - Innovation Labs
June 2018 - Dec 2019
• Built RESTful APIs using Python and Flask
"""

test_resume_2 = """SARAH JOHNSON
sarah.j@email.com | 9876543210
Hyderabad

OBJECTIVE
Seeking a challenging position in data science...

EXPERIENCE
Data Scientist - DataTech Corp, Mumbai
Mar 2021 - Present
"""

test_resume_3 = """RESUME

RAJESH KUMAR SHARMA
Mobile: 8765432109 | Email: rajesh.sharma123@gmail.com
Based in: Pune, Maharashtra

CAREER OBJECTIVE
To secure a position as a DevOps Engineer...
"""


def test_extraction():
    """Test name and location extraction with different scenarios"""
    
    extractor = NameLocationExtractor()
    
    print("=" * 80)
    print("🧪 Testing Enhanced Name & Location Extraction")
    print("=" * 80)
    print()
    
    # Test 1: Full resume with all info
    print("📄 Test 1: Complete Resume")
    print("-" * 80)
    result = extractor.extract_name_and_location(
        test_resume,
        filename="john_smith_resume.pdf",
        email="john.smith@techcorp.com"
    )
    print(f"✓ Name: {result['name']}")
    print(f"✓ Location: {result['location']}")
    print()
    
    # Test 2: Resume with different format
    print("📄 Test 2: All Caps Format")
    print("-" * 80)
    result = extractor.extract_name_and_location(
        test_resume_2,
        filename="sarah_johnson_cv.docx",
        email="sarah.j@email.com"
    )
    print(f"✓ Name: {result['name']}")
    print(f"✓ Location: {result['location']}")
    print()
    
    # Test 3: Resume with "Based in" format
    print("📄 Test 3: 'Based in' Format")
    print("-" * 80)
    result = extractor.extract_name_and_location(
        test_resume_3,
        filename="rajesh_kumar_resume_2024.pdf",
        email="rajesh.sharma123@gmail.com"
    )
    print(f"✓ Name: {result['name']}")
    print(f"✓ Location: {result['location']}")
    print()
    
    # Test 4: Name from email only
    print("📄 Test 4: Name Extraction from Email")
    print("-" * 80)
    result = extractor.extract_name_and_location(
        "Some resume text without clear name...",
        email="priya.patel@company.com"
    )
    print(f"✓ Name (from email): {result['name']}")
    print()
    
    # Test 5: Name from filename only
    print("📄 Test 5: Name Extraction from Filename")
    print("-" * 80)
    result = extractor.extract_name_and_location(
        "Some resume text...",
        filename="amit_verma_software_engineer_resume.pdf"
    )
    print(f"✓ Name (from filename): {result['name']}")
    print()
    
    # Test spaCy availability
    print("=" * 80)
    if extractor.spacy_available:
        print("✅ spaCy NER is AVAILABLE - Using advanced extraction")
    else:
        print("⚠️  spaCy NER is NOT AVAILABLE - Using fallback methods only")
        print("   Install with: python -m spacy download en_core_web_sm")
    print("=" * 80)


def test_individual_methods():
    """Test individual extraction methods"""
    
    extractor = NameLocationExtractor()
    
    print("\n" + "=" * 80)
    print("🔬 Testing Individual Extraction Methods")
    print("=" * 80)
    print()
    
    # Test heuristic extraction
    print("1️⃣  Heuristic Name Extraction")
    print("-" * 80)
    name = extractor._extract_name_heuristic(test_resume)
    print(f"Result: {name}")
    print()
    
    # Test email extraction
    print("2️⃣  Email-based Name Extraction")
    print("-" * 80)
    name = extractor._extract_name_from_email("john.doe.smith@company.com")
    print(f"Result: {name}")
    print()
    
    # Test filename extraction
    print("3️⃣  Filename-based Name Extraction")
    print("-" * 80)
    name = extractor._extract_name_from_filename("mary_jane_watson_resume_2024.pdf")
    print(f"Result: {name}")
    print()
    
    # Test location pattern extraction
    print("4️⃣  Pattern-based Location Extraction")
    print("-" * 80)
    location = extractor._extract_location_pattern(test_resume)
    print(f"Result: {location}")
    print()


if __name__ == "__main__":
    test_extraction()
    test_individual_methods()
    
    print("\n✨ All tests completed!")
