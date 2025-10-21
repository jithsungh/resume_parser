"""
Test the complete resume parser pipeline
"""

import sys
import json
from src.core.complete_resume_parser import CompleteResumeParser

# Sample resume text
SAMPLE_RESUME = """
John Michael Smith
Software Engineer
Email: john.smith@email.com
Mobile: +91 9876543210
Location: Bangalore, Karnataka

PROFESSIONAL EXPERIENCE

Software Engineer - Ivy Comptech Apr 2023 - Present
• Architected and developed large-scale, enterprise-grade React.js applications serving millions of active users.
• Implemented advanced State Management solutions using Redux Toolkit and Context API for efficient, scalable data flow.
• Optimized web application performance with SSR, Code Splitting, Lazy Loading, Memoization, and Service Workers improving Core Web Vitals scores by 40%.
• Integrated complex RESTful APIs to deliver real-time, interactive dashboards.
• Ensured 100% Responsive, and Cross-Browser Compatible UI using Material UI, and Media Queries.
• Collaborated with Product Owners, UI/UX Teams, and DevOps Engineers to streamline development and deployment pipelines using GitHub Actions, Jenkins.

Front-End React.js Developer - Infinx Services Pvt Ltd Jan 2022 - Dec 2022
• Developed and delivered responsive, dynamic web portals and internal dashboards using React.js and Redux Toolkit.
• Migrated legacy codebase from vanilla JavaScript to React.js improving maintainability by 60%.
• Improved application performance by implementing Debouncing, Throttling and Caching Techniques reducing page load time by 35%.
• Implemented Progressive Web App (PWA) features, enhancing offline accessibility and performance.
• Mentored junior developers and conducted DSA sessions to uplift overall team skillset.

Front-End React.js Developer - Aditya Trades Center June 2017 - Aug 2019
• Designed and implemented fully responsive, SEO-optimized web applications using React.js, Bootstrap.
• Built and maintained modular, reusable, and scalable UI components using React Hooks and Context API.
• Integrated REST API's to build data-driven dashboards, reports, and client portals.
• Improved UI performance and load time using Lighthouse audits, Web Vitals analysis, and performance optimization techniques.
• Implemented Form Validations, Error Handling, and Authentication to enhance user experience and security.

EDUCATION
Bachelor of Technology in Computer Science - ABC University, 2017

SKILLS
React.js, JavaScript, TypeScript, Node.js, Redux, HTML5, CSS3, Git
"""


def main():
    print("=" * 80)
    print("🧪 TESTING COMPLETE RESUME PARSER")
    print("=" * 80)
    print()
    
    # Initialize parser
    model_path = "ml_model"  # Adjust path as needed
    
    try:
        parser = CompleteResumeParser(model_path)
    except Exception as e:
        print(f"❌ Error loading parser: {e}")
        print("\n💡 Make sure:")
        print("   1. The ml_model folder exists")
        print("   2. spaCy model is installed: python -m spacy download en_core_web_sm")
        return
    
    print("\n" + "=" * 80)
    print("📄 PARSING SAMPLE RESUME")
    print("=" * 80)
    print()
    
    # Parse resume
    result = parser.parse_resume(SAMPLE_RESUME, filename="john_smith_resume.pdf")
    
    # Display results
    print("✨ EXTRACTION RESULTS")
    print("-" * 80)
    print()
    
    print(f"👤 Name:              {result['name']}")
    print(f"📧 Email:             {result['email']}")
    print(f"📱 Mobile:            {result['mobile']}")
    print(f"📍 Location:          {result['location']}")
    print(f"💼 Primary Role:      {result['primary_role']}")
    print(f"⏱️  Total Experience:  {result['total_experience_years']} years")
    print()
    
    print(f"🏢 WORK EXPERIENCE ({len(result['experiences'])} companies)")
    print("-" * 80)
    
    for i, exp in enumerate(result['experiences'], 1):
        print(f"\n{i}. {exp['company_name']}")
        print(f"   Role:     {exp['role']}")
        print(f"   Period:   {exp['from_date']} - {exp['to_date']}")
        
        if exp.get('duration_months'):
            print(f"   Duration: {exp['duration_months']} months")
        
        if exp['skills']:
            skills_str = ', '.join(exp['skills'][:10])  # Show first 10 skills
            if len(exp['skills']) > 10:
                skills_str += f" ... (+{len(exp['skills']) - 10} more)"
            print(f"   Skills:   {skills_str}")
    
    print()
    print("=" * 80)
    print("📊 JSON OUTPUT")
    print("=" * 80)
    print()
    print(json.dumps(result, indent=2))
    
    print()
    print("=" * 80)
    print("✅ TEST COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
