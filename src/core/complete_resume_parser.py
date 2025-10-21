"""
Complete Resume Parser Pipeline
Integrates NER model, name/location extraction, and experience parsing
"""

import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from transformers.utils import logging as transformers_logging

# Suppress transformers logging
transformers_logging.set_verbosity_error()


class CompleteResumeParser:
    """
    Complete resume parsing pipeline that extracts:
    - Name, email, mobile, location
    - Total experience
    - Primary role
    - Detailed work history with companies, roles, dates, and skills
    """
    
    def __init__(self, model_path: str):
        """
        Initialize the parser
        
        Args:
            model_path: Path to the fine-tuned NER model
        """
        print("🚀 Initializing Complete Resume Parser...")
        
        # Load NER model
        print("   Loading NER model...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(model_path)
        self.ner_pipeline = pipeline(
            "ner", 
            model=self.model, 
            tokenizer=self.tokenizer, 
            aggregation_strategy="simple"
        )
        
        # Load name/location extractor
        print("   Loading name/location extractor...")
        from .name_location_extractor import NameLocationExtractor
        self.name_location_extractor = NameLocationExtractor()
        
        print("✅ Parser initialized successfully!\n")
    
    def parse_resume(self, resume_text: str, 
                     filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse complete resume and extract all information
        
        Args:
            resume_text: Full resume text
            filename: Optional filename for name extraction
            
        Returns:
            Dictionary with structured resume data
        """
        # Step 1: Extract contact info
        contact_info = self._extract_contact_info(resume_text)
        
        # Step 2: Extract name and location
        name_location = self.name_location_extractor.extract_name_and_location(
            resume_text, 
            filename=filename,
            email=contact_info.get('email')
        )
        
        # Step 3: Extract experience section
        experience_text = self._extract_experience_section(resume_text)
        
        # Step 4: Run NER on experience section
        experiences = []
        if experience_text:
            experiences = self._extract_experiences(experience_text)
        
        # Step 5: Calculate total experience
        total_experience = self._calculate_total_experience(resume_text, experiences)
        
        # Step 6: Determine primary role
        primary_role = self._determine_primary_role(experiences)
        
        # Compile final result
        result = {
            'name': name_location.get('name'),
            'mobile': contact_info.get('mobile'),
            'email': contact_info.get('email'),
            'location': name_location.get('location'),
            'total_experience_years': total_experience,
            'primary_role': primary_role,
            'experiences': experiences
        }
        
        return result
    
    def _extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract email and mobile number"""
        email = self._extract_email(text)
        mobile = self._extract_mobile(text)
        
        return {
            'email': email,
            'mobile': mobile
        }
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None
    
    def _extract_mobile(self, text: str) -> Optional[str]:
        """Extract mobile number"""
        patterns = [
            r'\+91[-\s]?\d{10}',
            r'\b\d{10}\b',
            r'\+91[-\s]?\d{5}[-\s]?\d{5}',
            r'\b\d{5}[-\s]?\d{5}\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                mobile = re.sub(r'[-\s]', '', matches[0])
                return mobile
        
        return None
    
    def _extract_experience_section(self, text: str) -> Optional[str]:
        """Extract the experience/work history section"""
        headers = [
            r'(?:professional\s+)?(?:work\s+)?experience',
            r'employment\s+history',
            r'work\s+history',
            r'professional\s+background',
            r'career\s+history'
        ]
        
        text_lower = text.lower()
        
        # Find experience section start
        start_idx = -1
        for header in headers:
            match = re.search(header, text_lower)
            if match:
                start_idx = match.start()
                break
        
        if start_idx == -1:
            return text
        
        # Find next major section
        end_headers = [
            r'education',
            r'academic',
            r'qualifications',
            r'skills',
            r'technical\s+skills',
            r'certifications',
            r'projects',
            r'achievements'
        ]
        
        end_idx = len(text)
        for end_header in end_headers:
            match = re.search(end_header, text_lower[start_idx + 50:])
            if match:
                potential_end = start_idx + 50 + match.start()
                end_idx = min(end_idx, potential_end)
        
        return text[start_idx:end_idx]
    
    def _extract_experiences(self, experience_text: str) -> List[Dict[str, Any]]:
        """Extract work experiences using NER model"""
        # Chunk the text for processing
        max_chunk_size = 512
        chunks = [experience_text[i:i+max_chunk_size] 
                  for i in range(0, len(experience_text), max_chunk_size)]
        
        # Run NER on all chunks
        all_entities = []
        for chunk in chunks:
            try:
                chunk_results = self.ner_pipeline(chunk)
                all_entities.extend(chunk_results)
            except Exception as e:
                print(f"⚠️  Warning: Error processing chunk: {e}")
                continue
        
        # Deduplicate entities
        entities = self._deduplicate_entities(all_entities)
        
        # Group entities by company
        experiences = self._group_entities_by_company(entities)
        
        # Post-process experiences
        experiences = self._post_process_experiences(experiences)
        
        return experiences
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        Remove duplicate entities and merge subword tokens
        Handles BERT tokenization artifacts like ##per, ##ing, etc.
        """
        # First, merge subword tokens
        merged_entities = []
        i = 0
        
        while i < len(entities):
            current = entities[i]
            merged_word = current['word']
            total_score = current['score']
            count = 1
            
            # Look ahead for subword tokens (starting with ##)
            j = i + 1
            while j < len(entities):
                next_entity = entities[j]
                next_word = next_entity['word']
                
                # Check if next token is a subword (starts with ##)
                if next_word.startswith('##'):
                    # Merge it with current token
                    merged_word += next_word.replace('##', '')
                    total_score += next_entity['score']
                    count += 1
                    j += 1
                elif next_entity['entity_group'] == current['entity_group'] and \
                     j == i + 1 and len(next_word) <= 3:
                    # Also merge very short tokens of same type immediately following
                    merged_word += next_word
                    total_score += next_entity['score']
                    count += 1
                    j += 1
                else:
                    break
            
            # Create merged entity
            merged_entity = {
                'word': merged_word.strip(),
                'entity_group': current['entity_group'],
                'score': total_score / count  # Average score
            }
            
            merged_entities.append(merged_entity)
            i = j if j > i + 1 else i + 1
        
        # Now deduplicate
        unique_entities_set = set()
        unique_entities_list = []
        
        for entity in merged_entities:
            # Skip very short or low-confidence entities
            if len(entity['word'].strip()) <= 1:
                continue
            
            # Skip low confidence single-letter or short tech terms
            if entity['entity_group'] == 'TECH' and len(entity['word']) <= 2 and entity['score'] < 0.7:
                continue
            
            # Skip obvious noise
            noise_words = ['the', 'and', 'or', 'in', 'at', 'to', 'for', 'of', 'a', 'an']
            if entity['word'].lower() in noise_words:
                continue
            
            entity_key = (entity['word'].lower(), entity['entity_group'])
            if entity_key not in unique_entities_set:
                unique_entities_set.add(entity_key)
                unique_entities_list.append(entity)
        
        return unique_entities_list
      
    def _group_entities_by_company(self, entities: List[Dict]) -> List[Dict[str, Any]]:
        """
        Group entities by company using pattern: look for ROLE-COMPANY-DATE clusters
        """
        experiences = []
        current_experience = None
        dates_seen_for_current = 0
        
        for i, entity in enumerate(entities):
            entity_type = entity['entity_group']
            entity_text = entity['word']
            confidence = entity.get('score', 0)
            
            # Clean entity text
            entity_text = self._clean_entity_text(entity_text)
            
            # Skip if too short and low confidence
            if len(entity_text) <= 2 and confidence < 0.6:
                continue
            
            if entity_type == 'COMPANY':
                # New company detected
                # Only start new experience if company name is reasonable
                if len(entity_text) > 3 or confidence > 0.75:
                    # If we have 2 dates already, save current and start new
                    if current_experience and dates_seen_for_current >= 2:
                        if self._is_valid_experience(current_experience):
                            experiences.append(current_experience)
                        current_experience = None
                        dates_seen_for_current = 0
                    
                    if not current_experience:
                        current_experience = {
                            'company_name': entity_text,
                            'role': None,
                            'from_date': None,
                            'to_date': None,
                            'skills': []
                        }
                    elif not current_experience['company_name']:
                        # Add company to existing experience started with role
                        current_experience['company_name'] = entity_text
            
            elif entity_type == 'ROLE':
                if len(entity_text) > 4:  # Valid role length
                    if not current_experience:
                        # Start new experience with role
                        current_experience = {
                            'company_name': None,
                            'role': entity_text,
                            'from_date': None,
                            'to_date': None,
                            'skills': []
                        }
                    elif not current_experience['role']:
                        # Add role to current experience
                        current_experience['role'] = entity_text
                    elif dates_seen_for_current >= 2:
                        # New role after seeing 2 dates = new experience
                        if self._is_valid_experience(current_experience):
                            experiences.append(current_experience)
                        current_experience = {
                            'company_name': None,
                            'role': entity_text,
                            'from_date': None,
                            'to_date': None,
                            'skills': []
                        }
                        dates_seen_for_current = 0
            
            elif entity_type == 'DATE':
                if current_experience:
                    if not current_experience['from_date']:
                        current_experience['from_date'] = entity_text
                        dates_seen_for_current += 1
                    elif not current_experience['to_date']:
                        current_experience['to_date'] = entity_text
                        dates_seen_for_current += 1
            
            elif entity_type == 'TECH':
                if current_experience and len(entity_text) > 1:
                    current_experience['skills'].append(entity_text)
        
        # Add last experience if valid
        if current_experience and self._is_valid_experience(current_experience):
            experiences.append(current_experience)
        
        # Filter out invalid experiences
        experiences = [exp for exp in experiences if self._is_valid_experience(exp)]
        
        return experiences
    
    def _is_valid_experience(self, exp: Dict) -> bool:
        """Check if experience entry has minimum required information"""
        # Must have at least company OR role
        has_company = exp.get('company_name') and len(exp['company_name']) > 3
        has_role = exp.get('role') and len(exp['role']) > 5
        
        if not (has_company or has_role):
            return False
        
        # Prefer entries with dates
        has_dates = exp.get('from_date') or exp.get('to_date')
        
        # If it has company/role but no dates, only accept if high confidence
        if not has_dates:
            confidence = exp.get('_confidence', 0)
            return confidence > 0.75
        
        return True
    
    def _clean_entity_text(self, text: str) -> str:
        """Clean entity text - remove tokenization artifacts"""
        # Remove BERT subword tokens (##)
        text = text.replace('##', '')
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove leading/trailing punctuation except for necessary ones
        text = text.strip('.,;:!?-_*~`')
        
        return text.strip()
    
    def _post_process_experiences(self, experiences: List[Dict]) -> List[Dict]:
        """Post-process experience entries"""
        processed = []
        
        for exp in experiences:
            # Parse dates
            from_date = exp.get('from_date')
            to_date = exp.get('to_date')
            
            if from_date and to_date:
                from_parsed = self._parse_date(from_date)
                to_parsed = self._parse_date(to_date)
                
                exp['from_date'] = from_parsed
                exp['to_date'] = to_parsed
                
                # Calculate duration
                if from_parsed and to_parsed:
                    duration_months = self._calculate_duration_months(from_parsed, to_parsed)
                    exp['duration_months'] = duration_months
            
            # Clean company name
            if exp.get('company_name'):
                exp['company_name'] = self._clean_company_name(exp['company_name'])
            
            # Deduplicate and clean skills
            if exp.get('skills'):
                exp['skills'] = self._clean_skills_list(exp['skills'])
            
            processed.append(exp)
        
        return processed
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to standardized format"""
        if not date_str:
            return None
        
        date_str = date_str.strip().lower()
        
        # Handle "Present", "Current", etc.
        if any(word in date_str for word in ['present', 'current', 'now', 'till date']):
            return 'Present'
        
        # Try various date formats
        formats = [
            r'(\w+)\s+(\d{4})',  # "Jan 2020"
            r'(\d{1,2})/(\d{4})',  # "01/2020"
            r'(\d{4})',  # "2020"
        ]
        
        for fmt in formats:
            match = re.search(fmt, date_str)
            if match:
                return match.group(0)
        
        return date_str
    
    def _calculate_duration_months(self, from_date: str, to_date: str) -> int:
        """Calculate duration in months between two dates"""
        # Simplified calculation
        # In production, you'd want proper date parsing
        return 12  # Placeholder
    
    def _clean_company_name(self, company: str) -> str:
        """Clean company name"""
        company = ' '.join(company.split())
        company = company.rstrip('.,;:-')
        return company.strip()
     
    def _clean_skills_list(self, skills: List[str]) -> List[str]:
        """Clean and deduplicate skills list"""
        cleaned = []
        seen = set()
        
        # Common words that are NOT skills
        non_skill_words = {
            'the', 'and', 'or', 'in', 'at', 'to', 'for', 'of', 'a', 'an',
            'with', 'from', 'by', 'on', 'as', 'is', 'are', 'was', 'were',
            'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did'
        }
        
        for skill in skills:
            skill_clean = ' '.join(skill.split()).strip()
            skill_lower = skill_clean.lower()
            
            # Skip very short or very long
            if len(skill_clean) < 2 or len(skill_clean) > 40:
                continue
            
            # Skip common non-skill words
            if skill_lower in non_skill_words:
                continue
            
            # Skip if already seen
            if skill_lower in seen:
                continue
            
            # Skip incomplete tokens
            if skill_clean.startswith('##') or len(skill_clean) == 1:
                continue
            
            # Skip just numbers
            if skill_clean.isdigit():
                continue
            
            seen.add(skill_lower)
            cleaned.append(skill_clean)
        
        return cleaned
    
    def _calculate_total_experience(self, full_text: str, 
                                    experiences: List[Dict]) -> float:
        """Calculate total years of experience"""
        # Method 1: Look for explicit mentions
        explicit_exp = self._find_explicit_experience(full_text)
        if explicit_exp:
            return explicit_exp
        
        # Method 2: Calculate from experience dates
        if experiences:
            total_months = sum(exp.get('duration_months', 0) for exp in experiences)
            return round(total_months / 12, 1) if total_months > 0 else 0.0
        
        return 0.0
    
    def _find_explicit_experience(self, text: str) -> Optional[float]:
        """Find explicit experience mentions"""
        patterns = [
            r'(\d+\.?\d*)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+professional)?(?:\s+experience)',
            r'experience[:\s]+(\d+\.?\d*)\+?\s*(?:years?|yrs?)',
            r'total\s+experience[:\s]+(\d+\.?\d*)\+?\s*(?:years?|yrs?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        
        return None
    
    def _determine_primary_role(self, experiences: List[Dict]) -> Optional[str]:
        """Determine primary/current role"""
        if not experiences:
            return None
        
        roles = [exp.get('role') for exp in experiences if exp.get('role')]
        
        if not roles:
            return None
        
        # If all roles are the same
        unique_roles = list(set(roles))
        if len(unique_roles) == 1:
            return unique_roles[0]
        
        # Return latest role
        return roles[0]


def parse_resume_file(model_path: str, resume_text: str, 
                     filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to parse a resume
    
    Args:
        model_path: Path to NER model
        resume_text: Resume text content
        filename: Optional filename
        
    Returns:
        Parsed resume data
    """
    parser = CompleteResumeParser(model_path)
    return parser.parse_resume(resume_text, filename)
