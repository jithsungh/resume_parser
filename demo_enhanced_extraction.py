"""
Demo: Complete Resume Information Extraction with Enhanced Name/Location
Shows the full pipeline with NER + enhanced name/location extraction
"""

import os
from pathlib import Path

# Sample resume text
SAMPLE_RESUME = """
Priya Sharma
Email: priya.sharma@techmail.com | Mobile: +91-9876543210
Location: Bangalore, Karnataka, India
LinkedIn: linkedin.com/in/priyasharma | GitHub: github.com/priyasharma

PROFESSIONAL SUMMARY
Senior React.js Developer with 5+ years of professional experience in building scalable 
web applications. Expertise in modern JavaScript frameworks and cloud technologies.

WORK EXPERIENCE

Senior Frontend Developer - TechSolutions Pvt Ltd
April 2023 - Present, Bangalore
• Architected and developed large-scale React.js applications serving 2M+ active users
• Implemented state management using Redux Toolkit and Context API
• Optimized performance with code splitting, lazy loading, and memoization
• Technologies: React.js, Redux, TypeScript, Material UI, Node.js, AWS

Frontend Developer - InnovateLabs
January 2021 - March 2023, Mumbai  
• Built responsive web applications using React.js and Bootstrap
• Integrated RESTful APIs for real-time dashboards
• Migrated legacy JavaScript code to React.js improving maintainability by 60%
• Technologies: React.js, JavaScript, Bootstrap, REST API, Jenkins, Git

Junior Developer - WebCraft Solutions
June 2019 - December 2020, Pune
• Developed UI components using HTML, CSS, and JavaScript
• Collaborated with design team to implement pixel-perfect interfaces
• Technologies: HTML5, CSS3, JavaScript, jQuery, Figma

EDUCATION
Bachelor of Technology in Computer Science - VIT University, Vellore (2015-2019)

SKILLS
Frontend: React.js, Redux, JavaScript, TypeScript, HTML5, CSS3, Bootstrap, Material UI
Backend: Node.js, Express.js, REST API
Tools: Git, GitHub, Jenkins, AWS, Docker
"""


def demo_enhanced_extraction():
    """Demonstrate the enhanced extraction with all features"""
    
    print("=" * 80)
    print("🎯 ENHANCED RESUME INFORMATION EXTRACTION DEMO")
    print("=" * 80)
    print()
    
    # Check if model exists
    model_path = Path("ml_model")
    if not model_path.exists():
        print("❌ Error: NER model not found at 'ml_model/'")
        print("   Please ensure the fine-tuned BERT model is available")
        print()
        return
    
    try:
        from src.core.ner_experience_extractor import NERExperienceExtractor
        from src.core.resume_info_extractor import ResumeInfoExtractor
        
        print("📦 Loading NER model...")
        ner_extractor = NERExperienceExtractor(model_path=str(model_path))
        
        print("📦 Initializing extractors...")
        info_extractor = ResumeInfoExtractor(ner_extractor)
        
        print("✅ Models loaded successfully!")
        print()
        
        # Extract complete information
        print("🔍 Extracting resume information...")
        print()
        
        result = info_extractor.extract_complete_info(
            resume_text=SAMPLE_RESUME,
            filename="priya_sharma_resume.pdf"  # Providing filename for better extraction
        )
        
        # Display results
        print("=" * 80)
        print("📋 EXTRACTION RESULTS")
        print("=" * 80)
        print()
        
        # Basic Information
        print("👤 BASIC INFORMATION")
        print("-" * 80)
        print(f"Name:              {result['name'] or 'Not found'}")
        print(f"Email:             {result['email'] or 'Not found'}")
        print(f"Mobile:            {result['mobile'] or 'Not found'}")
        print(f"Location:          {result['location'] or 'Not found'}")
        print(f"Total Experience:  {result['total_experience_years']} years")
        print(f"Primary Role:      {result['primary_role'] or 'Not determined'}")
        print()
        
        # Experience Details
        print("💼 WORK EXPERIENCE")
        print("-" * 80)
        
        if result['experiences']:
            for i, exp in enumerate(result['experiences'], 1):
                print(f"\n{i}. {exp.get('company_name', 'Unknown Company')}")
                print(f"   Role:          {exp.get('role', 'Not specified')}")
                print(f"   Period:        {exp.get('from_date', '?')} to {exp.get('to_date', '?')}")
                
                if exp.get('duration_months'):
                    years = exp['duration_months'] // 12
                    months = exp['duration_months'] % 12
                    duration_str = f"{years}y {months}m" if years else f"{months}m"
                    print(f"   Duration:      {duration_str}")
                
                if exp.get('skills'):
                    skills_str = ', '.join(exp['skills'][:10])  # Show first 10
                    if len(exp['skills']) > 10:
                        skills_str += f" ... (+{len(exp['skills']) - 10} more)"
                    print(f"   Technologies:  {skills_str}")
        else:
            print("   No experience entries found")
        
        print()
        print("=" * 80)
        
        # Show extraction method sources
        print()
        print("ℹ️  EXTRACTION METHODS USED")
        print("-" * 80)
        print("✓ Name:       spaCy NER + Heuristics + Email + Filename")
        print("✓ Location:   spaCy NER + Pattern Matching + City Database")
        print("✓ Contact:    Regex Pattern Matching")
        print("✓ Experience: Fine-tuned BERT NER Model")
        print()
        
        # Check spaCy availability
        try:
            from src.core.name_location_extractor import NameLocationExtractor
            extractor = NameLocationExtractor()
            if extractor.spacy_available:
                print("✅ spaCy NER is enabled for enhanced extraction")
            else:
                print("⚠️  spaCy NER not available - using fallback methods")
                print("   Install with: python -m spacy download en_core_web_sm")
        except Exception as e:
            print(f"⚠️  Could not check spaCy status: {e}")
        
        print()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print()
        print("Make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        print("  python -m spacy download en_core_web_sm")
        print()
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        print()
        import traceback
        traceback.print_exc()


def demo_name_location_only():
    """Quick demo of just name and location extraction"""
    
    print("=" * 80)
    print("🎯 QUICK NAME & LOCATION EXTRACTION DEMO")
    print("=" * 80)
    print()
    
    try:
        from src.core.name_location_extractor import extract_name_and_location
        
        result = extract_name_and_location(
            resume_text=SAMPLE_RESUME,
            filename="priya_sharma_resume.pdf",
            email="priya.sharma@techmail.com"
        )
        
        print(f"✓ Name:     {result['name']}")
        print(f"✓ Location: {result['location']}")
        print()
        
    except ImportError:
        print("❌ Could not import name_location_extractor")
        print("   Make sure the module exists in src/core/")
        print()


if __name__ == "__main__":
    print("\n")
    
    # Run quick demo first
    demo_name_location_only()
    
    print("\n" + "="*80 + "\n")
    
    # Run full demo
    demo_enhanced_extraction()
    
    print("\n✨ Demo completed!")
    print()
    print("📚 For more information, see:")
    print("   - NAME_LOCATION_EXTRACTION.md (Enhanced extraction guide)")
    print("   - NER_PIPELINE_README.md (Full pipeline documentation)")
    print()
