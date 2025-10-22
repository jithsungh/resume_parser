"""
NER-Based Resume Parser Pipeline
Complete pipeline integrating NER model for resume parsing
"""

import os
import json
from typing import Dict, Any, Optional
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from transformers.utils import logging as transformers_logging

# Suppress transformers warnings
transformers_logging.set_verbosity_error()


class NERResumeParserPipeline:
    """Complete pipeline for NER-based resume parsing"""
    
    def __init__(self, model_path: str, roles_map: Dict[str, str]):
        """
        Initialize the pipeline
        
        Args:
            model_path: Path to the fine-tuned NER model
            roles_map: Dictionary mapping role variants to canonical roles
        """
        self.model_path = model_path
        self.roles_map = roles_map
        
        # Load model and tokenizer
        print(f"Loading NER model from: {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(model_path)
        
        # Create NER pipeline
        self.ner_pipeline = pipeline(
            "ner", 
            model=self.model, 
            tokenizer=self.tokenizer, 
            aggregation_strategy="simple"
        )
        
        print("NER model loaded successfully")
        
        # Import extractors
        from .ner_experience_extractor import NERExperienceExtractor
        from .resume_info_extractor import ResumeInfoExtractor
        
        # Initialize extractors
        self.ner_extractor = NERExperienceExtractor(self.ner_pipeline, self.roles_map)
        self.info_extractor = ResumeInfoExtractor(self.ner_extractor)
    
    def parse_resume(self, resume_text: str, 
                     contact_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Parse a complete resume
        
        Args:
            resume_text: Full resume text
            contact_info: Optional pre-extracted contact info
            
        Returns:
            Structured resume data
        """
        # Extract complete information
        result = self.info_extractor.extract_complete_info(resume_text, contact_info)
        
        # Format the output
        formatted_result = self._format_output(result)
        
        return formatted_result
    
    def _format_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format the output to match required structure"""
        experiences = []
        
        for exp in result.get('experiences', []):
            experience_entry = {
                'company_name': exp.get('company_name'),
                'role': exp.get('role'),
                'from': exp.get('from_date'),
                'to': exp.get('to_date'),
                'duration_months': exp.get('duration_months'),
                'skills': exp.get('skills', [])
            }
            experiences.append(experience_entry)
        
        return {
            'name': result.get('name'),
            'mobile': result.get('mobile'),
            'email': result.get('email'),
            'location': result.get('location'),
            'total_experience_years': result.get('total_experience_years'),
            'primary_role': result.get('primary_role'),
            'experiences': experiences
        }
    
    def parse_batch(self, resume_texts: list, 
                   contact_infos: Optional[list] = None) -> list:
        """
        Parse multiple resumes
        
        Args:
            resume_texts: List of resume texts
            contact_infos: Optional list of contact info dicts
            
        Returns:
            List of parsed resume data
        """
        if contact_infos is None:
            contact_infos = [None] * len(resume_texts)
        
        results = []
        for idx, (text, contact) in enumerate(zip(resume_texts, contact_infos)):
            print(f"Processing resume {idx + 1}/{len(resume_texts)}")
            try:
                result = self.parse_resume(text, contact)
                results.append(result)
            except Exception as e:
                print(f"Error processing resume {idx + 1}: {e}")
                results.append({
                    'error': str(e),
                    'name': None,
                    'mobile': None,
                    'email': None,
                    'experiences': []
                })
        
        return results


def load_roles_map(roles_config_path: str) -> Dict[str, str]:
    """Load roles mapping from config file"""
    import sys
    import importlib.util
    
    # Load the roles.py module
    spec = importlib.util.spec_from_file_location("roles_config", roles_config_path)
    roles_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(roles_module)
    
    # Get ROLES_MAP
    if hasattr(roles_module, 'ROLES_MAP'):
        return roles_module.ROLES_MAP
    elif hasattr(roles_module, 'CANONICAL_ROLES'):
        # Build ROLES_MAP from CANONICAL_ROLES
        roles_map = {}
        for canonical, variants in roles_module.CANONICAL_ROLES.items():
            for variant in variants:
                roles_map[variant.lower()] = canonical
        return roles_map
    else:
        raise ValueError("No ROLES_MAP or CANONICAL_ROLES found in config")


def create_pipeline(model_path: str, 
                   roles_config_path: str = None) -> NERResumeParserPipeline:
    """
    Create a NER resume parser pipeline
    
    Args:
        model_path: Path to the fine-tuned NER model
        roles_config_path: Path to roles.py config file
        
    Returns:
        Initialized pipeline
    """
    # Load roles map
    if roles_config_path is None:
        # Use default path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        roles_config_path = os.path.join(project_root, 'config', 'roles.py')
    
    roles_map = load_roles_map(roles_config_path)
    
    # Create pipeline
    pipeline = NERResumeParserPipeline(model_path, roles_map)
    
    return pipeline


# Example usage
if __name__ == "__main__":
    # Example: Create and use the pipeline
    
    # Path to your trained model
    MODEL_PATH = "ml_model"  # or "/content/ner-bert-resume/checkpoint-250"
    
    # Create pipeline
    parser = create_pipeline(MODEL_PATH)
    
    # Example resume text
    sample_text = """
    John Doe
    Software Engineer
    Email: john.doe@email.com | Mobile: +91-9876543210
    Location: Bangalore, India
    
    PROFESSIONAL EXPERIENCE
    
    Software Engineer - Ivy Comptech Apr 2023 - Present
    • Architected and developed large-scale, enterprise-grade React.js applications
    • Implemented advanced State Management solutions using Redux Toolkit
    
    Front-End React.js Developer - Infinx Services Pvt Ltd Jan 2022 - Dec 2022
    • Developed responsive web portals using React.js and Redux Toolkit
    • Migrated legacy codebase from vanilla JavaScript to React.js
    """
    
    # Parse resume
    result = parser.parse_resume(sample_text)
    
    # Print result
    print(json.dumps(result, indent=2))
