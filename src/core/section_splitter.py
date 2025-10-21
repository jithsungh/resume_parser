"""
Section Header Splitter
========================

Handles cases where multiple section headers appear on the same line
(e.g., "EXPERIENCE SKILLS" in multi-column layouts).
"""

import re
from typing import List, Tuple, Optional
from pathlib import Path
import json


class SectionSplitter:
    """
    Detects and splits multi-section headers that appear on the same line.
    Common in multi-column resumes where column headers are side-by-side.
    """
    
    def __init__(self, sections_database_path: Optional[str] = None):
        """
        Initialize with section database.
        
        Args:
            sections_database_path: Path to sections_database.json
        """
        if sections_database_path is None:
            sections_database_path = "config/sections_database.json"
        
        self.database_path = Path(sections_database_path)
        self.known_sections = self._load_known_sections()
    
    def _load_known_sections(self) -> dict:
        """Load all known section variants from database"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Build map of variant -> canonical
            variant_map = {}
            for canonical, info in data.get('sections', {}).items():
                variants = info.get('variants', [])
                for variant in variants:
                    variant_lower = variant.lower().strip()
                    variant_map[variant_lower] = canonical
            
            return variant_map
        except Exception as e:
            print(f"Warning: Could not load sections database: {e}")
            return {}
    
    def _normalize(self, text: str) -> str:
        """Normalize text for matching"""
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        return text.lower().strip()
    
    def detect_multi_section_header(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Detect if a line contains multiple section headers.
        
        Args:
            text: The line text to analyze
            
        Returns:
            List of (canonical_name, start_pos, end_pos) tuples
            Empty list if no multi-section header detected
        """
        if not text or len(text.strip()) < 10:
            return []
        
        normalized = self._normalize(text)
        words = normalized.split()
        
        if len(words) < 2:
            return []
        
        # Try to find multiple known sections in the text
        matched_sections = []
        
        # Strategy 1: Check if consecutive words match known sections
        for i, word in enumerate(words):
            if word in self.known_sections:
                # Found a match
                canonical = self.known_sections[word]
                # Estimate position in original text
                start_pos = text.lower().find(word)
                end_pos = start_pos + len(word)
                matched_sections.append((canonical, start_pos, end_pos))
        
        # Strategy 2: Check multi-word combinations (up to 3 words)
        for length in [2, 3]:
            for i in range(len(words) - length + 1):
                phrase = ' '.join(words[i:i+length])
                if phrase in self.known_sections:
                    canonical = self.known_sections[phrase]
                    # Estimate position
                    start_pos = text.lower().find(phrase.replace(' ', ''))
                    if start_pos == -1:
                        start_pos = text.lower().find(phrase)
                    end_pos = start_pos + len(phrase) if start_pos != -1 else 0
                    
                    # Avoid duplicates
                    if not any(s[0] == canonical for s in matched_sections):
                        matched_sections.append((canonical, start_pos, end_pos))
        
        # Only return if we found 2+ distinct sections
        unique_sections = list(set([s[0] for s in matched_sections]))
        if len(unique_sections) >= 2:
            return matched_sections
        
        return []
    
    def is_multi_section_header(self, text: str) -> bool:
        """
        Quick check if text contains multiple section headers.
        
        Args:
            text: The line text to check
            
        Returns:
            True if multiple sections detected
        """
        return len(self.detect_multi_section_header(text)) >= 2
    
    def split_by_position(self, text: str, line_width: float, positions: List[Tuple[str, int, int]]) -> List[Tuple[str, str]]:
        """
        Split text into sections based on detected positions.
        
        Args:
            text: The full line text
            line_width: The width of the line in PDF coordinates
            positions: List of (canonical_name, start_pos, end_pos) from detect_multi_section_header
            
        Returns:
            List of (canonical_name, text_fragment) tuples
        """
        if not positions:
            return []
        
        # Sort by position
        sorted_positions = sorted(positions, key=lambda x: x[1])
        
        result = []
        for i, (canonical, start, end) in enumerate(sorted_positions):
            # Extract the section name part
            section_text = text[start:end] if start != -1 else canonical
            result.append((canonical, section_text))
        
        return result


# Singleton instance
_splitter_instance = None


def get_section_splitter() -> SectionSplitter:
    """Get singleton instance of SectionSplitter"""
    global _splitter_instance
    if _splitter_instance is None:
        _splitter_instance = SectionSplitter()
    return _splitter_instance
