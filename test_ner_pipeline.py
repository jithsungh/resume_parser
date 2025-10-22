"""
Test script for NER-based resume parser pipeline
"""

import os
import sys
import json

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.core.ner_pipeline import create_pipeline


def test_ner_pipeline():
    """Test the NER pipeline with sample resume"""
    
    # Sample resume text (from your example)
    sample_text = """
    JITHSUNGH V
    Senior Software Engineer
    
    Contact: +91-9876543210 | Email: jithsungh.v@example.com
    Location: Bangalore, Karnataka, India
    
    Professional Experience: 6+ years in software development
    
    WORK EXPERIENCE
    
    Software Engineer - Ivy Comptech Apr 2023 - Present
    • Architected and developed large-scale, enterprise-grade React.js applications serving millions of active users.
    • Implemented advanced State Management solutions using Redux Toolkit and Context API for efficient, scalable data flow.
    • Optimized web application performance with SSR, Code Splitting, Lazy Loading, Memoization, and Service Workers improving Core Web Vitals scores by 40%.
    • Integrated complex RESTful APIs to deliver real-time, interactive dashboards.
    • Ensured 100% Responsive, and Cross-Browser Compatible UI using Material UI, and Media Queries.
    • Collaborated with Product Owners, UI/UX Teams, and DevOps Engineers to streamline development and deployment pipelines using GitHub Actions, Jenkins.
    • Performed regular Code Reviews, Technical Grooming Sessions, and Mentorship to uplift team productivity and code quality.
    
    Front-End React.js Developer - Infinx Services Pvt Ltd Jan 2022 - Dec 2022
    • Developed and delivered responsive, dynamic web portals and internal dashboards using React.js and Redux Toolkit.
    • Migrated legacy codebase from vanilla JavaScript to React.js improving maintainability by 60%.
    • Improved application performance by implementing Debouncing, Throttling and Caching Techniques reducing page load time by 35%.
    • Implemented Progressive Web App (PWA) features, enhancing offline accessibility and performance.
    • Mentored junior developers and conducted DSA sessions to uplift overall team skillset.
    
    Front-End React.js Developer - Aditya Trades Center June 2017 - Aug 2019
    • Designed and implemented fully responsive, SEO-optimized web applications using React.js, Bootstrap.
    • Built and maintained modular, reusable, and scalable UI components using React Hooks and Context API.
    • Integrated REST APIs to build data-driven dashboards, reports, and client portals.
    • Improved UI performance and load time using Lighthouse audits, Web Vitals analysis, and performance optimization techniques.
    • Implemented Form Validations, Error Handling, and Authentication to enhance user experience and security.
    • Collaborated with design teams to convert complex Figma/PSD designs into pixel-perfect, production-ready UI.
    • Worked closely with clients and stakeholders to gather requirements and deliver feature-rich, user-friendly applications within deadlines.
    """
    
    # Model path - UPDATE THIS to your model location
    model_path = "ml_model"  # or "/content/ner-bert-resume/checkpoint-250"
    
    print("=" * 80)
    print("Testing NER Resume Parser Pipeline")
    print("=" * 80)
    
    try:
        # Create pipeline
        print("\n1. Creating pipeline...")
        parser = create_pipeline(model_path)
        print("   ✓ Pipeline created successfully")
        
        # Parse resume
        print("\n2. Parsing resume...")
        result = parser.parse_resume(sample_text)
        print("   ✓ Resume parsed successfully")
        
        # Display results
        print("\n3. Extracted Information:")
        print("=" * 80)
        
        print(f"\n📝 Name: {result.get('name')}")
        print(f"📧 Email: {result.get('email')}")
        print(f"📱 Mobile: {result.get('mobile')}")
        print(f"📍 Location: {result.get('location')}")
        print(f"⏱️  Total Experience: {result.get('total_experience_years')} years")
        print(f"💼 Primary Role: {result.get('primary_role')}")
        
        print("\n🏢 Work Experience:")
        print("-" * 80)
        
        for idx, exp in enumerate(result.get('experiences', []), 1):
            print(f"\n{idx}. {exp.get('company_name', 'N/A')}")
            print(f"   Role: {exp.get('role', 'N/A')}")
            print(f"   Period: {exp.get('from', 'N/A')} to {exp.get('to', 'N/A')}")
            if exp.get('duration_months'):
                years = exp['duration_months'] // 12
                months = exp['duration_months'] % 12
                print(f"   Duration: {years}y {months}m")
            
            skills = exp.get('skills', [])
            if skills:
                print(f"   Skills: {', '.join(skills[:10])}")  # Show first 10
                if len(skills) > 10:
                    print(f"          ... and {len(skills) - 10} more")
        
        # Save to JSON
        output_file = os.path.join(project_root, 'outputs', 'ner_test_result.json')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_file}")
        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_ner_pipeline()
    sys.exit(0 if success else 1)
