"""
Self-Learning Section Discovery
================================
Uses embeddings to discover new section types and prevent false positives.
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from collections import Counter


class SectionLearner:
    """
    Self-learning system for section discovery.
    
    Features:
    - Embedding-based similarity detection
    - Automatic section vocabulary expansion
    - False positive prevention
    - Confidence scoring
    """
    def __init__(self, config_path: Optional[str] = None, auto_save: bool = False):
        """
        Initialize learner with config database.
        
        Args:
            config_path: Path to sections_database.json (optional, defaults to config/sections_database.json)
            auto_save: Whether to automatically save learned sections
        """
        if config_path is None:
            config_path = "config/sections_database.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.embeddings_cache = {}
        self._embedding_model = None
        self.auto_save = auto_save
        
        # Learning session tracking
        self.observed_sections = {}  # section_name -> frequency
        self.new_variants = []  # (section_name, variant) pairs
        self.potential_new_sections = []  # (heading, frequency) pairs

    def _load_config(self) -> Dict[str, Any]:
        """Load section database"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config not found at {self.config_path}, creating new one")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "version": "1.0.0",
            "sections": {},
            "learning": {
                "new_sections_discovered": [],
                "false_positives": []
            }
        }
    
    def _save_config(self):
        """Save updated configuration"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _get_embedding_model(self):
        """Lazy load embedding model"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")
                return None
        return self._embedding_model
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text (with caching)"""
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        model = self._get_embedding_model()
        if model is None:
            return None
        
        try:
            embedding = model.encode([text])[0]
            self.embeddings_cache[text] = embedding
            return embedding
        except Exception as e:
            print(f"Warning: Embedding generation failed: {e}")
            return None
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def find_matching_section(
        self,
        heading: str,
        confidence_threshold: float = 0.75
    ) -> Tuple[Optional[str], float]:
        """
        Find best matching section for a heading using embeddings.
        
        Args:
            heading: Heading text to classify
            confidence_threshold: Minimum similarity score
            
        Returns:
            (section_name, confidence) or (None, 0.0)
        """
        heading_lower = heading.lower().strip()
        
        # First: exact match in variants
        for section_name, section_data in self.config.get('sections', {}).items():
            variants = section_data.get('variants', [])
            if heading_lower in [v.lower() for v in variants]:
                return section_name, 1.0
        
        # Second: embedding-based similarity
        heading_emb = self.get_embedding(heading_lower)
        if heading_emb is None:
            return None, 0.0
        
        best_match = None
        best_score = 0.0
        
        for section_name, section_data in self.config.get('sections', {}).items():
            variants = section_data.get('variants', [])
            
            for variant in variants:
                variant_emb = self.get_embedding(variant.lower())
                if variant_emb is None:
                    continue
                
                similarity = self.cosine_similarity(heading_emb, variant_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = section_name
        
        if best_score >= confidence_threshold:
            return best_match, best_score
        
        return None, best_score
    
    def propose_new_section(
        self,
        heading: str,
        frequency: int,
        context_lines: List[str],
        min_frequency: int = 3,
        min_confidence: float = 0.80
    ) -> bool:
        """
        Propose a new section type based on frequency and confidence.
        
        Args:
            heading: Candidate section heading
            frequency: How many resumes have this heading
            context_lines: Sample lines from this section (for validation)
            min_frequency: Minimum occurrences needed
            min_confidence: Minimum confidence score
            
        Returns:
            True if proposal is strong enough to add
        """
        # Check if it's a false positive pattern
        false_positives = self.config.get('learning', {}).get('false_positives', [])
        if heading.lower() in [fp.lower() for fp in false_positives]:
            return False
        
        # Check frequency
        if frequency < min_frequency:
            return False
        
        # Check if it's too similar to existing sections (would be redundant)
        match, score = self.find_matching_section(heading, confidence_threshold=0.90)
        if match is not None:
            # Already covered by existing section
            return False
        
        # Analyze context to avoid false positives
        # (e.g., company names, job titles mistaken as sections)
        if self._looks_like_false_positive(heading, context_lines):
            self._mark_false_positive(heading)
            return False
        
        # Strong candidate!
        return True
    
    def _looks_like_false_positive(self, heading: str, context_lines: List[str]) -> bool:
        """
        Heuristics to detect false positive section headings.
        
        Examples of false positives:
        - Company names ("Google Inc.", "Microsoft Corporation")
        - Job titles ("Senior Software Engineer", "Product Manager")
        - Dates ("January 2020 - Present")
        - Single words that are too generic ("Details", "Information")
        """
        heading_lower = heading.lower()
        
        # Too short (1-2 chars)
        if len(heading_lower) <= 2:
            return True
        
        # Contains dates
        if any(char.isdigit() for char in heading):
            return True
        
        # Too generic single words
        generic_words = {'details', 'information', 'description', 'other', 'misc', 'miscellaneous'}
        if heading_lower in generic_words:
            return True
        
        # Looks like a company name (contains Inc, Corp, Ltd, LLC)
        company_suffixes = ['inc', 'corp', 'corporation', 'ltd', 'llc', 'pvt', 'limited']
        if any(suffix in heading_lower for suffix in company_suffixes):
            return True
        
        # Contextual check: if all lines are short (< 10 words), likely not a real section
        if context_lines:
            avg_words = sum(len(line.split()) for line in context_lines[:5]) / min(5, len(context_lines))
            if avg_words < 3:
                return True
        
        return False
    
    def _mark_false_positive(self, heading: str):
        """Add heading to false positive list"""
        false_positives = self.config.get('learning', {}).get('false_positives', [])
        if heading not in false_positives:
            false_positives.append(heading)
            self.config.setdefault('learning', {})['false_positives'] = false_positives
            self._save_config()
    
    def add_new_section(
        self,
        section_name: str,
        initial_variants: List[str],
        confidence_threshold: float = 0.85
    ):
        """
        Add a new discovered section to the database.
        
        Args:
            section_name: Canonical name for the section
            initial_variants: Initial list of heading variants
            confidence_threshold: Similarity threshold for matching
        """
        if section_name in self.config.get('sections', {}):
            print(f"Section '{section_name}' already exists")
            return
        
        self.config.setdefault('sections', {})[section_name] = {
            "variants": initial_variants,
            "confidence_threshold": confidence_threshold,
            "embedding_cluster_id": None,
            "discovered_on": Path.cwd().name  # track where it was found
        }
        
        # Log discovery
        self.config.setdefault('learning', {}).setdefault('new_sections_discovered', []).append({
            "name": section_name,
            "variants": initial_variants,
            "discovered_at": str(Path.cwd())
        })
        
        self._save_config()
        print(f"✓ New section added: {section_name}")
    
    def add_variant_to_existing(self, section_name: str, new_variant: str):
        """Add a new variant to an existing section"""
        if section_name not in self.config.get('sections', {}):
            print(f"Section '{section_name}' does not exist")
            return
        
        variants = self.config['sections'][section_name].get('variants', [])
        if new_variant.lower() not in [v.lower() for v in variants]:
            variants.append(new_variant)
            self.config['sections'][section_name]['variants'] = variants
            self._save_config()
            print(f"✓ Added variant '{new_variant}' to section '{section_name}'")
    
    def analyze_batch_headings(
        self,
        headings_with_frequency: List[Tuple[str, int, List[str]]],
        auto_add: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze a batch of headings from multiple resumes.
        
        Args:
            headings_with_frequency: List of (heading, frequency, context_lines) tuples
            auto_add: Automatically add strong candidates
            
        Returns:
            Analysis report with proposals
        """
        report = {
            "matched": [],
            "proposed_new": [],
            "false_positives": [],
            "uncertain": []
        }
        
        for heading, freq, context in headings_with_frequency:
            match, confidence = self.find_matching_section(heading, confidence_threshold=0.75)
            
            if match:
                report["matched"].append({
                    "heading": heading,
                    "matched_to": match,
                    "confidence": confidence,
                    "frequency": freq
                })
            else:
                # Check if it's a strong new candidate
                is_strong = self.propose_new_section(heading, freq, context)
                
                if is_strong:
                    report["proposed_new"].append({
                        "heading": heading,
                        "frequency": freq,
                        "confidence": confidence
                    })
                    
                    if auto_add:
                        self.add_new_section(
                            section_name=heading.title(),
                            initial_variants=[heading.lower()]
                        )
                elif self._looks_like_false_positive(heading, context):
                    report["false_positives"].append({
                        "heading": heading,
                        "frequency": freq
                    })
                else:
                    report["uncertain"].append({
                        "heading": heading,
                        "frequency": freq,
                        "confidence": confidence
                    })
        
        return report
    
    def classify_section(self, heading: str) -> Tuple[bool, Optional[str], float]:
        """
        Classify a section heading and return validity, matched section name, and confidence.
        
        Args:
            heading: Section heading to classify
            
        Returns:
            Tuple of (is_valid, section_name, confidence)
        """
        section_name, confidence = self.find_matching_section(heading, confidence_threshold=0.70)
        
        if section_name:
            return (True, section_name, confidence)
        else:
            return (False, None, confidence)
    
    def observe_section(self, section_name: str):
        """
        Observe a section heading during processing.
        
        Args:
            section_name: The section name/heading observed
        """
        # Track frequency
        if section_name not in self.observed_sections:
            self.observed_sections[section_name] = 0
        self.observed_sections[section_name] += 1
        
        # Try to match to known section
        match, confidence = self.find_matching_section(section_name, confidence_threshold=0.75)
        
        if match:
            # Check if this is a new variant
            variants = self.config.get('sections', {}).get(match, {}).get('variants', [])
            if section_name.lower() not in [v.lower() for v in variants]:
                self.new_variants.append((match, section_name))
        else:
            # Potential new section
            self.potential_new_sections.append((section_name, 1))
    
    def print_learning_report(self):
        """Print a report of observed sections and learning opportunities"""
        print("\n📊 Section Learning Report")
        print("=" * 60)
        
        # Most common sections
        if self.observed_sections:
            print("\n✅ Observed Sections:")
            sorted_sections = sorted(self.observed_sections.items(), key=lambda x: x[1], reverse=True)
            for section_name, count in sorted_sections[:10]:
                match, confidence = self.find_matching_section(section_name)
                status = f"✓ {match}" if match else "? Unknown"
                print(f"   {section_name:<30} ({count:2d}x) - {status}")
        
        # New variants discovered
        if self.new_variants:
            print(f"\n💡 New Variants Discovered ({len(self.new_variants)}):")
            # Group by canonical section
            variant_groups = {}
            for canonical, variant in self.new_variants:
                if canonical not in variant_groups:
                    variant_groups[canonical] = []
                if variant not in variant_groups[canonical]:
                    variant_groups[canonical].append(variant)
            
            for canonical, variants in variant_groups.items():
                print(f"   {canonical}:")
                for variant in variants:
                    print(f"     + {variant}")
        
        # Potential new sections
        if self.potential_new_sections:
            print(f"\n⚠️  Potential New Sections ({len(self.potential_new_sections)}):")
            for heading, freq in self.potential_new_sections[:5]:
                print(f"   - {heading} ({freq}x)")
        
        print("=" * 60)
    
    def get_learning_suggestions(self) -> Dict[str, Any]:
        """
        Get actionable learning suggestions.
        
        Returns:
            Dictionary with suggested actions
        """
        suggestions = {
            'add_variants': [],  # (canonical_name, new_variant)
            'add_new_sections': [],  # (new_section_name, initial_variants)
            'review_unknown': []  # (heading, frequency, similar_to)
        }
        
        # Suggest adding new variants
        variant_groups = {}
        for canonical, variant in self.new_variants:
            if canonical not in variant_groups:
                variant_groups[canonical] = []
            if variant not in variant_groups[canonical]:
                variant_groups[canonical].append(variant)
        
        for canonical, variants in variant_groups.items():
            for variant in variants:
                suggestions['add_variants'].append((canonical, variant))
        
        # Suggest new sections (if frequency >= 3)
        section_freq = {}
        for heading, freq in self.potential_new_sections:
            if heading not in section_freq:
                section_freq[heading] = 0
            section_freq[heading] += freq
        
        for heading, freq in section_freq.items():
            if freq >= 3:
                suggestions['add_new_sections'].append((heading.title(), [heading.lower()]))
            else:
                # Find similar section
                match, confidence = self.find_matching_section(heading, confidence_threshold=0.60)
                similar_to = match if match and confidence > 0.60 else None
                suggestions['review_unknown'].append((heading, freq, similar_to))
        
        return suggestions
    
    def apply_suggestions(self, suggestions: Dict[str, Any]):
        """
        Apply learning suggestions to the database.
        
        Args:
            suggestions: Dictionary from get_learning_suggestions()
        """
        applied_count = 0
        
        # Add variants
        for canonical, variant in suggestions.get('add_variants', []):
            if self._add_section_variant(canonical, variant):
                applied_count += 1
                print(f"✓ Added variant '{variant}' to '{canonical}'")
        
        # Add new sections
        for section_name, initial_variants in suggestions.get('add_new_sections', []):
            self.add_new_section(section_name, initial_variants)
            applied_count += 1
        
        print(f"\n✅ Applied {applied_count} learning suggestions")
        
        if self.auto_save:
            self._save_config()
            print("💾 Changes saved automatically")
    
    def learn_from_result(self, parsed_data: Dict[str, Any]) -> List[str]:
        """
        Learn new section variants from a parsed resume.
        
        Args:
            parsed_data: Parsed resume data with sections
            
        Returns:
            List of newly learned section variants
        """
        learned = []
        
        # Extract sections from parsed data
        sections = parsed_data.get('sections', [])
        
        for section_data in sections:
            section_heading = section_data.get('section', '')
            lines = section_data.get('lines', [])
              # Learn from Unknown Sections - look for potential headers
            if section_heading == 'Unknown Sections' and lines:
                for line in lines:
                    # Ensure line is a string
                    if not isinstance(line, str):
                        continue
                    
                    # Check if this line looks like a section header
                    if self._looks_like_section_header(line):
                        # Try to find which known section it's similar to
                        match, confidence = self.find_matching_section(line, confidence_threshold=0.65)
                        
                        if match and 0.65 <= confidence < 0.85:
                            # It's similar to a known section but not exact - add as variant
                            if self._add_section_variant(match, line):
                                learned.append(f"{line} -> {match}")
            
            # Also learn from known sections if they have new variants
            elif section_heading and section_heading != 'Unknown Sections':
                # Check if this is a new variant
                match, confidence = self.find_matching_section(section_heading, confidence_threshold=0.85)
                
                if match:
                    # It's a known section - check if this exact variant exists
                    variants = self.config.get('sections', {}).get(match, {}).get('variants', [])
                    
                    if section_heading.lower() not in [v.lower() for v in variants]:
                        # New variant of existing section
                        self.add_variant_to_existing(match, section_heading)
                        learned.append(f"{section_heading} -> {match}")
        
        return learned
    
    def _looks_like_section_header(self, text: str) -> bool:
        """
        Check if text looks like a section header.
        
        Section headers are typically:
        - Short (1-5 words)
        - Title case or all caps
        - Not a sentence (no ending punctuation)
        - No dates or numbers (usually)
        """
        # Ensure text is a string
        if not isinstance(text, str):
            return False
        
        if not text or len(text.strip()) < 3:
            return False
        
        text = text.strip()
        
        # Too long to be a header
        if len(text) > 100:
            return False
        
        # Check word count (headers are usually 1-5 words)
        words = text.split()
        if len(words) > 6:
            return False
        
        # Should not end with sentence punctuation
        if text.endswith(('.', '!', '?', ',')):
            return False
        
        # Should not contain typical content indicators
        content_indicators = ['•', '○', 'http', 'www', '@', '+91', 'gmail', '.com']
        if any(indicator in text.lower() for indicator in content_indicators):
            return False
        
        # Should not have too many numbers (likely a date or phone number)
        digit_count = sum(1 for c in text if c.isdigit())
        if digit_count > 4:
            return False
          # Likely a section header
        return True
    
    def _add_section_variant(self, section_name: str, variant: str) -> bool:
        """
        Add a new variant to an existing section.
        
        Args:
            section_name: The standard section name
            variant: The new variant to add
            
        Returns:
            True if variant was added, False if already exists
        """
        variant_lower = variant.lower().strip()
        
        # Check if section exists
        if section_name not in self.config['sections']:
            return False
        
        # Check if variant already exists
        existing_variants = [v.lower() for v in self.config['sections'][section_name]['variants']]
        if variant_lower in existing_variants:
            return False
        
        # Add the variant
        self.config['sections'][section_name]['variants'].append(variant_lower)
        
        # Save immediately so learning persists
        self._save_config()
        
        return True
    
    def learn_from_pattern(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Learn section from common patterns without embeddings.
        Useful for job titles, role descriptions, etc.
        
        Args:
            text: The text to analyze
            
        Returns:
            Tuple of (section_name, confidence) or None
        """
        text_lower = text.lower().strip()
        
        # Pattern 1: Job titles/roles → Experience
        job_patterns = [
            'developer', 'engineer', 'analyst', 'manager', 'architect',
            'consultant', 'specialist', 'lead', 'senior', 'junior',
            'intern', 'trainee', 'qa', 'tester', 'designer', 'programmer',
            'scientist', 'researcher', 'coordinator', 'administrator',
            'director', 'officer', 'assistant', 'associate'
        ]
        
        for pattern in job_patterns:
            if pattern in text_lower:
                # High confidence if it ends with the pattern
                if text_lower.endswith(pattern):
                    return ('Experience', 0.9)
                # Medium confidence if pattern is in the middle
                return ('Experience', 0.75)
        
        # Pattern 2: Project indicators → Projects
        project_patterns = ['project', 'portfolio', 'work sample', 'case study']
        for pattern in project_patterns:
            if pattern in text_lower:
                return ('Projects', 0.8)
        
        # Pattern 3: Education indicators → Education
        education_patterns = ['university', 'college', 'school', 'degree', 'bachelor', 'master', 'phd', 'diploma']
        for pattern in education_patterns:
            if pattern in text_lower:
                return ('Education', 0.8)
        
        # Pattern 4: Certification indicators → Certifications  
        cert_patterns = ['certification', 'certificate', 'certified', 'license', 'training']
        for pattern in cert_patterns:
            if pattern in text_lower:
                return ('Certifications', 0.8)
        
        # Pattern 5: Skills indicators → Skills
        skill_patterns = ['skill', 'expertise', 'proficiency', 'competenc', 'technical', 'knowledge']
        for pattern in skill_patterns:
            if pattern in text_lower:
                return ('Skills', 0.75)
        
        return None
    
    def add_variant(self, section_name: str, variant: str, auto_learn: bool = True) -> bool:
        """
        Public method to add a variant to a section.
        
        Args:
            section_name: The canonical section name
            variant: The variant text to add
            auto_learn: If True, try pattern-based learning if section doesn't exist
            
        Returns:
            True if variant was added successfully
        """
        # Try to add to existing section
        result = self._add_section_variant(section_name, variant)
        
        # If failed and auto_learn enabled, try pattern matching
        if not result and auto_learn:
            pattern_match = self.learn_from_pattern(variant)
            if pattern_match:
                learned_section, confidence = pattern_match
                if confidence >= 0.75:
                    result = self._add_section_variant(learned_section, variant)
                    if result and self.verbose:
                        print(f"[Learn] Pattern-matched '{variant}' -> {learned_section} ({confidence:.2f})")
        
        return result
    
    @property
    def verbose(self) -> bool:
        """Get verbose setting from config or default to False"""
        return getattr(self, '_verbose', False)
    
    @verbose.setter
    def verbose(self, value: bool):
        """Set verbose setting"""
        self._verbose = value


def test_section_learner():
    """Test the section learner"""
    config_path = Path(__file__).parent.parent.parent / "config" / "sections_database.json"
    learner = SectionLearner(str(config_path))
    
    # Test matching
    test_headings = [
        "Professional Experience",
        "Technical Skills",
        "Work History",
        "Certifications & Awards",
        "Random Company Inc.",
        "2020 - Present"
    ]
    
    print("Testing section matching:")
    for heading in test_headings:
        match, confidence = learner.find_matching_section(heading)
        print(f"  '{heading}' -> {match} ({confidence:.2f})")


if __name__ == "__main__":
    test_section_learner()
