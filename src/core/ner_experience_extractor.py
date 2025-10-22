"""
NER-based Experience Extractor using fine-tuned BERT model
Extracts structured experience data from resume text
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dateutil import parser as date_parser
import calendar


class NERExperienceExtractor:
    """Extract experience details using NER model predictions"""
    
    def __init__(self, ner_pipeline, roles_map: Dict[str, str]):
        """
        Initialize the extractor
        
        Args:
            ner_pipeline: Transformers NER pipeline
            roles_map: Dictionary mapping role variants to canonical roles
        """
        self.ner_pipeline = ner_pipeline
        self.roles_map = roles_map
        
    def extract_entities(self, text: str, max_chunk_size: int = 512) -> List[Dict[str, Any]]:
        """
        Extract entities from text using NER model with chunking
        
        Args:
            text: Input text to process
            max_chunk_size: Maximum chunk size for processing
            
        Returns:
            List of unique entities with their types and scores
        """
        # Chunk the text
        chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        
        all_entities = []
        for chunk in chunks:
            try:
                chunk_results = self.ner_pipeline(chunk)
                all_entities.extend(chunk_results)
            except Exception as e:
                print(f"Error processing chunk: {e}")
                continue
        
        # Filter for unique entities and clean them
        unique_entities = self._deduplicate_entities(all_entities)
        cleaned_entities = self._clean_entities(unique_entities)
        
        return cleaned_entities
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on word and entity_group"""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity['word'].lower().strip(), entity['entity_group'])
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        return unique
    
    def _clean_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        Clean and filter entities:
        - Remove subword tokens (##)
        - Filter low confidence scores
        - Merge split entities
        - Remove noise tokens
        """
        cleaned = []
        min_confidence = 0.4  # Minimum confidence threshold
        
        # First pass: remove obvious noise
        for entity in entities:
            word = entity['word']
            score = entity['score']
            entity_type = entity['entity_group']
            
            # Skip subword tokens starting with ##
            if word.startswith('##'):
                continue
            
            # Skip very short tokens for certain types
            if entity_type in ['TECH', 'ROLE'] and len(word) <= 2 and score < 0.7:
                continue
            
            # Skip if confidence too low
            if score < min_confidence:
                continue
            
            cleaned.append(entity)
        
        # Second pass: merge adjacent entities of same type
        merged = self._merge_adjacent_entities(cleaned, entities)
        
        return merged
    
    def _merge_adjacent_entities(self, cleaned_entities: List[Dict], 
                                  original_entities: List[Dict]) -> List[Dict]:
        """Merge adjacent entities that were split"""
        # Group by entity type
        grouped = defaultdict(list)
        for entity in cleaned_entities:
            grouped[entity['entity_group']].append(entity)
        
        # For now, return cleaned entities
        # Advanced merging logic can be added based on position/index
        return cleaned_entities
    
    def group_entities_by_company(self, entities: List[Dict]) -> List[Dict]:
        """
        Group entities into company blocks based on proximity and patterns
        
        Returns:
            List of company experience dictionaries
        """
        companies = []
        current_company = None
        
        # Separate entities by type
        roles = [e for e in entities if e['entity_group'] == 'ROLE']
        company_names = [e for e in entities if e['entity_group'] == 'COMPANY']
        dates = [e for e in entities if e['entity_group'] == 'DATE']
        techs = [e for e in entities if e['entity_group'] == 'TECH']
        
        # Try to match: ROLE + COMPANY + DATE patterns
        for idx, company in enumerate(company_names):
            exp_entry = {
                'company_name': company['word'].strip(),
                'role': None,
                'from_date': None,
                'to_date': None,
                'skills': []
            }
            
            # Find closest role before this company
            closest_role = self._find_closest_entity(company, roles, direction='before')
            if closest_role:
                exp_entry['role'] = self._normalize_role(closest_role['word'])
            
            # Find dates around this company
            nearby_dates = self._find_nearby_dates(company, dates, window=5)
            if len(nearby_dates) >= 2:
                exp_entry['from_date'] = nearby_dates[0]['word']
                exp_entry['to_date'] = nearby_dates[1]['word']
            elif len(nearby_dates) == 1:
                exp_entry['from_date'] = nearby_dates[0]['word']
            
            companies.append(exp_entry)
        
        # Assign techs to companies based on proximity
        companies = self._assign_skills_to_companies(companies, techs)
        
        return companies
    
    def _find_closest_entity(self, target: Dict, entities: List[Dict], 
                             direction: str = 'before') -> Optional[Dict]:
        """Find the closest entity to target in given direction"""
        # Since we don't have position info, use order in list
        # This is a simplified version
        if not entities:
            return None
        
        # Return first match with high confidence
        for entity in entities:
            if entity['score'] > 0.6:
                return entity
        
        return entities[0] if entities else None
    
    def _find_nearby_dates(self, target: Dict, dates: List[Dict], 
                           window: int = 5) -> List[Dict]:
        """Find dates near the target entity"""
        # Simplified: return dates with good confidence
        return [d for d in dates if d['score'] > 0.6][:2]
    
    def _assign_skills_to_companies(self, companies: List[Dict], 
                                     techs: List[Dict]) -> List[Dict]:
        """Assign skills to companies based on proximity"""
        # Simplified: distribute skills evenly or assign all to each
        # In practice, would use text positions
        
        if not companies:
            return companies
        
        # Collect unique skills
        unique_skills = []
        seen_skills = set()
        
        for tech in techs:
            skill = tech['word'].strip()
            skill_lower = skill.lower()
            
            if skill_lower not in seen_skills and len(skill) > 1:
                seen_skills.add(skill_lower)
                unique_skills.append(skill)
        
        # If only one company, assign all skills
        if len(companies) == 1:
            companies[0]['skills'] = unique_skills
        else:
            # Distribute skills across companies
            skills_per_company = len(unique_skills) // len(companies)
            remainder = len(unique_skills) % len(companies)
            
            start_idx = 0
            for idx, company in enumerate(companies):
                count = skills_per_company + (1 if idx < remainder else 0)
                company['skills'] = unique_skills[start_idx:start_idx + count]
                start_idx += count
        
        return companies
    
    def _normalize_role(self, role: str) -> str:
        """Normalize role using the roles map"""
        role_clean = role.strip().lower()
        
        # Try exact match
        if role_clean in self.roles_map:
            return self.roles_map[role_clean]
        
        # Try partial match
        for variant, canonical in self.roles_map.items():
            if variant in role_clean or role_clean in variant:
                return canonical
        
        # Return cleaned original
        return ' '.join(word.capitalize() for word in role.split())
    
    def parse_date_range(self, from_date: str, to_date: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse date strings to standardized format
        
        Returns:
            Tuple of (from_date_iso, to_date_iso)
        """
        from_parsed = self._parse_single_date(from_date)
        to_parsed = self._parse_single_date(to_date)
        
        return from_parsed, to_parsed
    
    def _parse_single_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse a single date string"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Handle "Present", "Current", etc.
        if date_str.lower() in ['present', 'current', 'now', 'ongoing']:
            return datetime.now().strftime('%Y-%m')
        
        try:
            # Try to parse the date
            parsed = date_parser.parse(date_str, fuzzy=True)
            return parsed.strftime('%Y-%m')
        except:
            # Try manual patterns
            patterns = [
                r'(\w+)\s+(\d{4})',  # "Jan 2022"
                r'(\d{1,2})[/-](\d{4})',  # "01/2022"
                r'(\d{4})',  # "2022"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, date_str)
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        month_str, year = groups
                        try:
                            # Try to convert month name to number
                            month_num = self._month_to_number(month_str)
                            return f"{year}-{month_num:02d}"
                        except:
                            return f"{year}-01"
                    elif len(groups) == 1:
                        return f"{groups[0]}-01"
            
            return None
    
    def _month_to_number(self, month_str: str) -> int:
        """Convert month string to number"""
        month_str = month_str.strip()[:3].capitalize()
        
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
            'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
            'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
        
        return months.get(month_str, 1)
    
    def calculate_duration_months(self, from_date: str, to_date: str) -> int:
        """Calculate duration in months between two dates"""
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m')
            to_dt = datetime.strptime(to_date, '%Y-%m')
            
            months = (to_dt.year - from_dt.year) * 12 + (to_dt.month - from_dt.month)
            return max(0, months)
        except:
            return 0
