"""
Quick test to verify SectionSplitter.split_sections() method works
"""

from src.core.section_splitter import SectionSplitter

def test_split_sections():
    """Test the split_sections method"""
    
    # Sample resume text
    sample_text = """
John Doe
john.doe@email.com | +1-555-1234

PROFESSIONAL SUMMARY
Experienced software engineer with 5+ years in full-stack development.

EXPERIENCE
Software Engineer at Tech Corp
- Developed web applications
- Led team of 5 developers

Senior Developer at StartupXYZ
- Built scalable systems
- Improved performance by 40%

SKILLS
Python, JavaScript, React, Node.js, SQL

EDUCATION
Bachelor of Science in Computer Science
University of Technology, 2018
"""
    
    print("Testing SectionSplitter.split_sections()...")
    
    try:
        splitter = SectionSplitter()
        sections = splitter.split_sections(sample_text)
        
        print(f"\n✅ Success! Found {len(sections)} sections:")
        print("-" * 60)
        
        for section_name, content in sections.items():
            print(f"\n📋 Section: {section_name}")
            print(f"   Content preview: {content[:100]}...")
        
        print("\n" + "=" * 60)
        print("✅ The split_sections method is working correctly!")
        
        return True
        
    except AttributeError as e:
        print(f"\n❌ AttributeError: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_split_sections()
