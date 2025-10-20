"""
Quality Validator
=================

Validates the quality of parsed resume data.
"""

from typing import Dict, Any


class QualityValidator:
    """
    Validates quality and completeness of parsed resume data.
    """
    
    def __init__(self):
        """Initialize the quality validator."""
        pass
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parsed resume data quality.
        
        Args:
            data: Parsed resume data
            
        Returns:
            Dictionary with:
            - score: Quality score (0-1)
            - num_sections: Number of sections found
            - total_lines: Total lines of content
            - has_contact: Whether contact info found
            - issues: List of quality issues
        """
        result = {
            'score': 0.0,
            'num_sections': 0,
            'total_lines': 0,
            'has_contact': False,
            'issues': []
        }
        
        if not data:
            result['issues'].append("Empty data")
            return result
        
        # Count sections
        sections = data.get('sections', [])
        result['num_sections'] = len(sections)
        
        # Count total lines
        total_lines = 0
        for section in sections:
            lines = section.get('lines', [])
            total_lines += len(lines)
        
        result['total_lines'] = total_lines
        
        # Check for contact info
        contact = data.get('contact', {})
        has_contact = bool(
            contact.get('email') or 
            contact.get('phone') or 
            contact.get('name')
        )
        result['has_contact'] = has_contact
        
        # Calculate quality score
        score = 0.0
        
        # Sections (40%)
        if result['num_sections'] >= 5:
            score += 0.4
        elif result['num_sections'] >= 3:
            score += 0.25
        elif result['num_sections'] >= 1:
            score += 0.1
        
        # Content lines (40%)
        if result['total_lines'] >= 30:
            score += 0.4
        elif result['total_lines'] >= 15:
            score += 0.25
        elif result['total_lines'] >= 5:
            score += 0.1
        
        # Contact info (20%)
        if has_contact:
            score += 0.2
        
        result['score'] = min(score, 1.0)
        
        # Identify issues
        if result['num_sections'] == 0:
            result['issues'].append("No sections found")
        
        if result['total_lines'] < 5:
            result['issues'].append("Very little content extracted")
        
        if not has_contact:
            result['issues'].append("No contact information found")
        
        return result
