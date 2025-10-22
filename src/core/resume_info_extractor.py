"""
Complete Resume Information Extractor
Extracts name, contact info, experience, and structured work history
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class ResumeInfoExtractor:
    """Extract comprehensive resume information"""
    
    def __init__(self, ner_extractor):
        """
        Initialize extractor
        
        Args:
            ner_extractor: NERExperienceExtractor instance
        """
        self.ner_extractor = ner_extractor
        
    def extract_complete_info(self, resume_text: str, 
                              contact_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract all information from resume
        
        Args:
            resume_text: Full resume text
            contact_info: Pre-extracted contact info (email, mobile)
            
        Returns:
            Dictionary with structured resume data
        """
        # Extract contact info if not provided
        if not contact_info:
            contact_info = self.extract_contact_info(resume_text)
        
        # Extract name
        name = self.extract_name(resume_text)
        
        # Extract location
        location = self.extract_location(resume_text)
        
        # Extract experience section and process with NER
        experience_text = self.extract_experience_section(resume_text)
        
        if experience_text:
            # Use NER model to extract entities
            entities = self.ner_extractor.extract_entities(experience_text)
            
            # Group entities into company experiences
            experiences = self.ner_extractor.group_entities_by_company(entities)
            
            # Post-process experiences
            experiences = self.post_process_experiences(experiences)
        else:
            experiences = []
        
        # Calculate total experience
        total_experience_years = self.calculate_total_experience(resume_text, experiences)
        
        # Determine primary role
        primary_role = self.determine_primary_role(experiences)
        
        return {
            'name': name,
            'mobile': contact_info.get('mobile'),
            'email': contact_info.get('email'),
            'location': location,
            'total_experience_years': total_experience_years,
            'primary_role': primary_role,
            'experiences': experiences
        }
    
    def extract_name(self, text: str) -> Optional[str]:
        """
        Extract candidate name from resume
        Usually at the top of the resume
        """
        lines = text.split('\n')
        
        # Look in first 10 lines
        for line in lines[:10]:
            line = line.strip()
            
            # Skip empty lines
            if not line or len(line) < 3:
                continue
            
            # Skip lines with common headers
            skip_keywords = [
                'resume', 'cv', 'curriculum vitae', 'profile', 'objective',
                'summary', 'email', 'phone', 'mobile', 'address', 'location'
            ]
            
            if any(kw in line.lower() for kw in skip_keywords):
                continue
            
            # Check if line looks like a name (2-4 words, mostly alphabetic)
            words = line.split()
            if 2 <= len(words) <= 4:
                # Check if mostly alphabetic
                alpha_ratio = sum(c.isalpha() or c.isspace() for c in line) / len(line)
                if alpha_ratio > 0.8:
                    return line.strip()
        
        return None
    
    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
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
        # Indian mobile patterns
        patterns = [
            r'\+91[-\s]?\d{10}',
            r'\b\d{10}\b',
            r'\+91[-\s]?\d{5}[-\s]?\d{5}',
            r'\b\d{5}[-\s]?\d{5}\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Clean the number
                mobile = re.sub(r'[-\s]', '', matches[0])
                return mobile
        
        return None
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location/address"""
        # Look for common location patterns
        patterns = [
            r'(?:Location|Address|City)[\s:]+([A-Za-z\s,]+)',
            r'\b(Bangalore|Bengaluru|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|Ahmedabad|Jaipur)\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_experience_section(self, text: str) -> Optional[str]:
        """Extract the experience/work history section from resume"""
        # Common section headers
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
            # No explicit section found, return full text
            return text
        
        # Find next major section (education, skills, etc.)
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
    
    def calculate_total_experience(self, full_text: str, 
                                   experiences: List[Dict]) -> float:
        """
        Calculate total years of experience
        First try to find explicit mention, then calculate from dates
        """
        # Method 1: Look for explicit mentions
        explicit_exp = self._find_explicit_experience(full_text)
        if explicit_exp:
            return explicit_exp
        
        # Method 2: Calculate from experience dates
        if experiences:
            total_months = 0
            for exp in experiences:
                from_date = exp.get('from_date')
                to_date = exp.get('to_date')
                
                if from_date and to_date:
                    months = self.ner_extractor.calculate_duration_months(from_date, to_date)
                    total_months += months
            
            return round(total_months / 12, 1)
        
        return 0.0
    
    def _find_explicit_experience(self, text: str) -> Optional[float]:
        """Find explicit experience mentions like '5+ years of experience'"""
        patterns = [
            r'(\d+\.?\d*)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+professional)?(?:\s+experience)',
            r'experience[:\s]+(\d+\.?\d*)\+?\s*(?:years?|yrs?)',
            r'total\s+experience[:\s]+(\d+\.?\d*)\+?\s*(?:years?|yrs?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    years = float(match.group(1))
                    return years
                except:
                    continue
        
        return None
    
    def determine_primary_role(self, experiences: List[Dict]) -> Optional[str]:
        """
        Determine the primary/current role
        If all roles are same, return that. Otherwise return latest role.
        """
        if not experiences:
            return None
        
        roles = [exp.get('role') for exp in experiences if exp.get('role')]
        
        if not roles:
            return None
        
        # If all roles are the same
        unique_roles = list(set(roles))
        if len(unique_roles) == 1:
            return unique_roles[0]
        
        # Return the latest (first in list assuming chronological order)
        return roles[0]
    
    def post_process_experiences(self, experiences: List[Dict]) -> List[Dict]:
        """
        Post-process experience entries:
        - Parse and standardize dates
        - Clean company names
        - Deduplicate skills
        - Add duration
        """
        processed = []
        
        for exp in experiences:
            # Parse dates
            from_date = exp.get('from_date')
            to_date = exp.get('to_date')
            
            if from_date and to_date:
                from_parsed, to_parsed = self.ner_extractor.parse_date_range(from_date, to_date)
                exp['from_date'] = from_parsed
                exp['to_date'] = to_parsed
                
                # Calculate duration
                if from_parsed and to_parsed:
                    duration_months = self.ner_extractor.calculate_duration_months(
                        from_parsed, to_parsed
                    )
                    exp['duration_months'] = duration_months
            
            # Clean company name
            if exp.get('company_name'):
                exp['company_name'] = self._clean_company_name(exp['company_name'])
            
            # Deduplicate and clean skills
            if exp.get('skills'):
                exp['skills'] = self._clean_skills_list(exp['skills'])
            
            processed.append(exp)
        
        return processed
    
    def _clean_company_name(self, company: str) -> str:
        """Clean company name"""
        # Remove extra whitespace
        company = ' '.join(company.split())
        
        # Remove trailing punctuation
        company = company.rstrip('.,;:-')
        
        return company.strip()
    
    def _clean_skills_list(self, skills: List[str]) -> List[str]:
        """Clean and deduplicate skills list"""
        cleaned = []
        seen = set()
        
        for skill in skills:
            # Clean the skill
            skill_clean = ' '.join(skill.split()).strip()
            skill_lower = skill_clean.lower()
            
            # Skip very short or very long
            if len(skill_clean) < 2 or len(skill_clean) > 50:
                continue
            
            # Skip if already seen (case-insensitive)
            if skill_lower in seen:
                continue
            
            seen.add(skill_lower)
            cleaned.append(skill_clean)
        
        return cleaned
