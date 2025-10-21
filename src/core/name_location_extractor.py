"""
Enhanced Name and Location Extraction using spaCy NER
Uses multiple strategies: spaCy NER, heuristics, email parsing, filename analysis
"""

import re
import os
from typing import Optional, Dict, List, Tuple
import warnings

# Suppress spaCy warnings
warnings.filterwarnings('ignore')

try:
    import spacy
    SPACY_AVAILABLE = True
    
    # Try to load the model
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("⚠️  spaCy model 'en_core_web_sm' not found. Installing...")
        print("   Run: python -m spacy download en_core_web_sm")
        nlp = None
        SPACY_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None
    print("⚠️  spaCy not installed. Using fallback methods only.")


class NameLocationExtractor:
    """Extract name and location using multiple strategies"""
    
    def __init__(self):
        self.nlp = nlp
        self.spacy_available = SPACY_AVAILABLE and nlp is not None
        
        # Common cities in India (can be expanded)
        self.indian_cities = {
            'bangalore', 'bengaluru', 'mumbai', 'delhi', 'new delhi',
            'hyderabad', 'chennai', 'pune', 'kolkata', 'ahmedabad',
            'jaipur', 'surat', 'lucknow', 'kanpur', 'nagpur', 'indore',
            'thane', 'bhopal', 'visakhapatnam', 'pimpri-chinchwad',
            'patna', 'vadodara', 'ghaziabad', 'ludhiana', 'agra',
            'nashik', 'faridabad', 'meerut', 'rajkot', 'kalyan-dombivali',
            'vasai-virar', 'varanasi', 'srinagar', 'aurangabad', 'dhanbad',
            'amritsar', 'navi mumbai', 'allahabad', 'prayagraj', 'ranchi',
            'howrah', 'coimbatore', 'jabalpur', 'gwalior', 'vijayawada',
            'jodhpur', 'madurai', 'raipur', 'kota', 'chandigarh', 'guwahati',
            'noida', 'gurugram', 'gurgaon', 'kochi', 'cochin', 'trivandrum',
            'thiruvananthapuram', 'mysore', 'mysuru', 'bhubaneswar',
            'tiruchirappalli', 'tiruppur', 'salem', 'warangal', 'guntur',
            'mangalore', 'mangaluru', 'dehradun', 'shimla', 'gangtok'
        }
        
        # Common name prefixes/titles to skip
        self.name_prefixes = {
            'mr', 'mr.', 'mrs', 'mrs.', 'ms', 'ms.', 'dr', 'dr.',
            'prof', 'prof.', 'sir', 'madam'
        }
        
    def extract_name_and_location(self, resume_text: str, 
                                   filename: Optional[str] = None,
                                   email: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Extract name and location using multiple strategies
        
        Args:
            resume_text: Full resume text
            filename: Optional filename for name extraction
            email: Optional email for name extraction
            
        Returns:
            Dictionary with 'name' and 'location'
        """
        # Strategy 1: Try spaCy NER
        name_spacy, location_spacy = self._extract_with_spacy(resume_text)
        
        # Strategy 2: Heuristic extraction from top lines
        name_heuristic = self._extract_name_heuristic(resume_text)
        
        # Strategy 3: Extract from email
        name_email = self._extract_name_from_email(email) if email else None
        
        # Strategy 4: Extract from filename
        name_filename = self._extract_name_from_filename(filename) if filename else None
        
        # Strategy 5: Extract location with patterns
        location_pattern = self._extract_location_pattern(resume_text)
        
        # Combine results with confidence scoring
        final_name = self._choose_best_name([
            (name_spacy, 3.0),      # Highest confidence
            (name_heuristic, 2.5),
            (name_email, 2.0),
            (name_filename, 1.5)    # Lowest confidence
        ])
        
        final_location = location_spacy or location_pattern
        
        return {
            'name': final_name,
            'location': final_location
        }
    
    def _extract_with_spacy(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract name and location using spaCy NER"""
        if not self.spacy_available:
            return None, None
        
        # Process first 500 characters for name (usually at top)
        top_text = text[:500]
        doc = self.nlp(top_text)
        
        # Extract PERSON entities
        persons = [ent.text for ent in doc.ents if ent.label_ == 'PERSON']
        
        # Process full text for location (can appear anywhere)
        doc_full = self.nlp(text[:2000])  # First 2000 chars
        locations = [ent.text for ent in doc_full.ents if ent.label_ in ('GPE', 'LOC')]
        
        # Filter and select best name
        name = self._filter_person_entities(persons, top_text)
        
        # Filter and select best location
        location = self._filter_location_entities(locations)
        
        return name, location
    
    def _filter_person_entities(self, persons: List[str], context: str) -> Optional[str]:
        """Filter person entities to find the most likely candidate name"""
        if not persons:
            return None
        
        # Score each person entity
        scored_persons = []
        context_lines = context.split('\n')
        
        for person in persons:
            score = 0
            person_lower = person.lower()
            
            # Skip if it's a common keyword/label
            skip_keywords = [
                'email', 'phone', 'mobile', 'resume', 'cv', 'address', 'location',
                'objective', 'summary', 'experience', 'education', 'skills',
                'profile', 'contact', 'linkedin', 'github', 'portfolio'
            ]
            if person_lower in skip_keywords or any(kw == person_lower for kw in skip_keywords):
                continue
            
            # Skip if it's only one word (likely not a full name)
            words = person.split()
            if len(words) < 2:
                continue
            
            # Higher score if in first 3 lines (but not in header lines)
            for i, line in enumerate(context_lines[:5]):
                if person in line:
                    # Check if the line itself is not a header
                    line_lower = line.lower()
                    if not any(kw in line_lower for kw in skip_keywords):
                        score += (5 - i) * 2
                    break
            
            # Higher score for proper name format (2-4 words)
            if 2 <= len(words) <= 4:
                score += 3
            
            # Lower score if it contains common non-name words
            skip_words = ['engineer', 'developer', 'manager', 'analyst', 'consultant', 'specialist']
            if any(word in person_lower for word in skip_words):
                score -= 5
            
            # Higher score if mostly alphabetic
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in person) / len(person)
            score += alpha_ratio * 2
            
            # Higher score if starts with capital letters
            if all(word[0].isupper() for word in words if word):
                score += 2
            
            scored_persons.append((person, score))
        
        # Return highest scoring person
        scored_persons.sort(key=lambda x: x[1], reverse=True)
        return scored_persons[0][0] if scored_persons and scored_persons[0][1] > 0 else None
      
    def _filter_location_entities(self, locations: List[str]) -> Optional[str]:
        """Filter location entities to find the most likely location"""
        if not locations:
            return None
        
        # Filter out company-like names
        company_keywords = [
            'corporation', 'corp', 'company', 'inc', 'ltd', 'limited', 'pvt',
            'solutions', 'technologies', 'systems', 'services', 'group',
            'permanente', 'hospital', 'medical', 'health', 'institute'
        ]
        
        valid_locations = []
        for loc in locations:
            loc_lower = loc.lower()
            # Skip if it looks like a company name
            if any(keyword in loc_lower for keyword in company_keywords):
                continue
            valid_locations.append(loc)
        
        # Prefer Indian cities
        for loc in valid_locations:
            if loc.lower() in self.indian_cities:
                return loc
        
        # Return first valid location found, or None if all filtered out
        return valid_locations[0] if valid_locations else None
    
    def _extract_name_heuristic(self, text: str) -> Optional[str]:
        """
        Extract name using heuristics:
        - Top 5 lines
        - 2-4 words
        - Mostly alphabetic
        - Not common headers
        """
        lines = text.split('\n')
        
        for i, line in enumerate(lines[:8]):  # Check first 8 lines
            line = line.strip()
            
            # Skip empty or very short lines
            if not line or len(line) < 5:
                continue
            
            # Skip lines with common headers or contact info indicators
            skip_keywords = [
                'resume', 'cv', 'curriculum vitae', 'profile', 'objective',
                'summary', 'email', 'e-mail', 'phone', 'mobile', 'address', 'location',
                'linkedin', 'github', 'portfolio', 'website', 'contact', 'based in',
                'experience', 'education', 'skills', 'career'
            ]
            
            line_lower = line.lower()
            
            # Skip if line contains any skip keywords
            if any(kw in line_lower for kw in skip_keywords):
                continue
            
            # Skip if line contains email, phone, or URLs
            if re.search(r'@|www\.|https?://|\d{10}|\+91', line):
                continue
            
            # Check if line looks like a name
            words = line.split()
            
            # Remove titles/prefixes
            words = [w for w in words if w.lower().rstrip('.') not in self.name_prefixes]
            
            if 2 <= len(words) <= 4:
                # Check if mostly alphabetic (allow spaces and periods)
                alpha_ratio = sum(c.isalpha() or c.isspace() or c == '.' for c in line) / len(line)
                
                if alpha_ratio > 0.85:
                    # Check if it doesn't contain numbers or special chars (except periods)
                    if not re.search(r'[0-9@#$%^&*()_+=\[\]{};:<>?/\\|,]', line):
                        # If all caps, check if it looks like a name
                        if line.isupper():
                            # All caps is okay if it's in first 3 lines and has 2-4 words
                            if i < 3 and 2 <= len(words) <= 4:
                                return ' '.join(words)
                        else:
                            # Mixed case - likely a name
                            return ' '.join(words)
        
        return None
    
    def _extract_name_from_email(self, email: str) -> Optional[str]:
        """
        Extract name from email address
        e.g., john.doe@example.com -> John Doe
        """
        if not email:
            return None
        
        # Extract the part before @
        local_part = email.split('@')[0]
        
        # Split by common separators
        parts = re.split(r'[._\-+]', local_part)
        
        # Filter out numbers and short parts
        parts = [p for p in parts if len(p) > 1 and not p.isdigit()]
        
        # Take first 2-3 parts
        if 2 <= len(parts) <= 4:
            # Capitalize each part
            name = ' '.join(word.capitalize() for word in parts[:3])
            return name
        
        return None
      
    def _extract_name_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract name from filename
        e.g., john_doe_resume.pdf -> John Doe
        """
        if not filename:
            return None
        
        # Get basename without extension
        basename = os.path.splitext(os.path.basename(filename))[0]
        
        # Remove common resume-related words and job titles
        remove_words = [
            'resume', 'cv', 'curriculum', 'vitae', 'updated', 'latest', 'new', 'final',
            'software', 'engineer', 'developer', 'manager', 'analyst', 'consultant',
            'specialist', 'architect', 'lead', 'senior', 'junior', 'intern',
            'frontend', 'backend', 'fullstack', 'devops', 'data', 'web', 'mobile',
            'java', 'python', 'react', 'angular', 'node', 'js', 'full', 'stack'
        ]
        basename_lower = basename.lower()
        
        for word in remove_words:
            # Use word boundaries to avoid partial matches
            basename_lower = re.sub(r'\b' + word + r'\b', ' ', basename_lower)
        
        # Split by common separators
        parts = re.split(r'[._\-\s]+', basename_lower)
        
        # Filter out empty strings, numbers, years, and short parts
        parts = [p for p in parts if p and len(p) > 1 and not p.isdigit() and not re.match(r'^20\d{2}$', p)]
        
        # Take first 2-4 parts only (likely to be name)
        if 2 <= len(parts) <= 4:
            name = ' '.join(word.capitalize() for word in parts[:4])
            return name
        elif len(parts) > 4:
            # If more than 4 parts, take first 3 (conservative)
            name = ' '.join(word.capitalize() for word in parts[:3])
            return name
        return None
    
    def _extract_location_pattern(self, text: str) -> Optional[str]:
        """Extract location using regex patterns"""
        # Pattern 1: Look for explicit city names first (more reliable)
        lines = text.split('\n')[:20]
        for line in lines:
            line_clean = line.strip().lower()
            # Check for exact city matches in the line
            for city in self.indian_cities:
                # Use word boundaries to match whole city names
                if re.search(r'\b' + re.escape(city) + r'\b', line_clean):
                    # Return the city with proper capitalization
                    return city.title()
        
        # Pattern 2: "Location: City" or "Based in: City" 
        # Look for the line and extract city more carefully
        location_patterns = [
            r'(?:Location|Address|City|Based\s+in)[\s:]+([A-Za-z\s,]+)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location_text = match.group(1).strip()
                
                # Extract city name from the captured text
                # Split by comma and check each part
                parts = [p.strip() for p in location_text.split(',')]
                
                for part in parts:
                    part_lower = part.lower()
                    # Check if this part is a known city
                    if part_lower in self.indian_cities:
                        return part.title()
                    
                    # Check if part contains a known city
                    for city in self.indian_cities:
                        if city in part_lower:
                            return city.title()
        
        return None
      
      
    def _choose_best_name(self, name_candidates: List[Tuple[Optional[str], float]]) -> Optional[str]:
        """
        Choose the best name from multiple candidates
        
        Args:
            name_candidates: List of (name, confidence_score) tuples
            
        Returns:
            Best name or None
        """
        # Filter out None values and invalid names
        valid_candidates = []
        
        for name, score in name_candidates:
            if not name:
                continue
            
            # Additional validation: skip single words or obviously wrong names
            words = name.split()
            if len(words) < 2:
                continue
            
            # Skip if contains keywords
            name_lower = name.lower()
            skip_words = ['email', 'phone', 'mobile', 'resume', 'cv', 'based']
            if any(word in name_lower for word in skip_words):
                continue
            
            valid_candidates.append((name, score))
        
        if not valid_candidates:
            return None
        
        # If multiple candidates match, prefer the one with highest score
        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Additional validation: if top 2 candidates are very similar, confirm
        if len(valid_candidates) >= 2:
            top_name = valid_candidates[0][0].lower()
            second_name = valid_candidates[1][0].lower()
            
            # If they're similar (one is substring of other), use the longer one
            if top_name in second_name or second_name in top_name:
                return max([valid_candidates[0][0], valid_candidates[1][0]], key=len)
        
        return valid_candidates[0][0]


# Standalone functions for easy import
def extract_name_and_location(resume_text: str, 
                               filename: Optional[str] = None,
                               email: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Convenience function to extract name and location
    
    Args:
        resume_text: Full resume text
        filename: Optional filename
        email: Optional email address
        
    Returns:
        Dict with 'name' and 'location'
    """
    extractor = NameLocationExtractor()
    return extractor.extract_name_and_location(resume_text, filename, email)
