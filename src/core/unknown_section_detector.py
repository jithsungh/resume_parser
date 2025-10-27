"""
Step 6: Unknown Section Detection
==================================
Identifies potential missing or unknown sections by analyzing:
- Layout patterns (spacing, font)
- Semantic similarity to known sections
- Structural consistency

Helps identify sections that may have been missed or are non-standard.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np

from .line_section_grouper import Section, Line

try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False


@dataclass
class UnknownSection:
    """Represents a potentially unknown/missing section"""
    section: Section
    reason: str
    confidence: float
    similar_to: Optional[str] = None
    metadata: Dict[str, Any] = None


class UnknownSectionDetector:
    """Detects unknown or potentially missing sections"""
    
    def __init__(
        self,
        similarity_threshold: float = 0.5,
        use_embeddings: bool = True,
        verbose: bool = False
    ):
        """
        Initialize unknown section detector
        
        Args:
            similarity_threshold: Threshold for "close but not quite" matches
            use_embeddings: Use semantic embeddings
            verbose: Print debug info
        """
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = use_embeddings and HAS_EMBEDDINGS
        self.verbose = verbose
        
        self.embedding_model = None
        
        if self.use_embeddings and HAS_EMBEDDINGS:
            self._init_embeddings()
    
    def _init_embeddings(self):
        """Initialize embedding model"""
        if self.verbose:
            print("[UnknownSectionDetector] Loading embedding model...")
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def detect_unknown_sections(self, sections: List[Section]) -> List[UnknownSection]:
        """
        Detect unknown or ambiguous sections
        
        Args:
            sections: List of detected sections
            
        Returns:
            List of UnknownSection objects
        """
        if not sections:
            return []
        
        if self.verbose:
            print(f"[UnknownSectionDetector] Analyzing {len(sections)} sections for unknowns")
        
        unknown_sections = []
        
        for section in sections:
            # Skip if header is None (pre-header content)
            if section.header_line is None:
                continue
            
            # Check if section name looks unusual
            is_unknown, reason, confidence, similar_to = self._check_if_unknown(section)
            
            if is_unknown:
                unknown_section = UnknownSection(
                    section=section,
                    reason=reason,
                    confidence=confidence,
                    similar_to=similar_to,
                    metadata={
                        'header_text': section.header_line.text if section.header_line else None,
                        'line_count': len(section.content_lines),
                        'word_count': sum(line.word_count for line in section.content_lines)
                    }
                )
                unknown_sections.append(unknown_section)
        
        if self.verbose:
            print(f"  Found {len(unknown_sections)} unknown/ambiguous sections")
            for unk in unknown_sections:
                print(f"    - '{unk.section.section_name}': {unk.reason} (confidence: {unk.confidence:.2f})")
        
        return unknown_sections
    def _check_if_unknown(self, section: Section) -> Tuple[bool, str, float, Optional[str]]:
        """
        Check if section is unknown or unusual
        
        Args:
            section: Section to check
            
        Returns:
            Tuple of (is_unknown, reason, confidence, similar_to)
        """
        section_name = section.section_name.lower()
        
        # Known section patterns (very common)
        very_common = [
            'experience', 'education', 'skills', 'summary',
            'work experience', 'professional experience',
            'technical skills', 'core competencies', 'projects',
            'certifications', 'achievements', 'employment'
        ]
        
        # If it's very common, not unknown
        for common in very_common:
            if common in section_name or section_name in common:
                return False, '', 0.0, None
        
        # Check for unusual patterns - be stricter
        
        # Pattern 1: Too short (single letter/number) - STRONG indicator
        if len(section_name) <= 2:
            return True, 'Section name too short', 0.9, None
        
        # Pattern 2: Contains dates/numbers (might be content, not header) - STRONG
        import re
        if re.search(r'\d{4}|\d{1,2}/\d{1,2}|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', section_name, re.I):
            return True, 'Contains dates/numbers', 0.8, None
        
        # Pattern 3: Very long section name (likely not a real section)
        if len(section_name.split()) > 8:
            return True, 'Section name too long', 0.8, None
        
        # Pattern 4: Very few lines AND no substantial content - likely a mis-detection
        if section.header_line:
            total_words = sum(line.word_count for line in section.content_lines)
            if len(section.content_lines) <= 2 and total_words <= 5:
                return True, 'Very few content lines', 0.7, None
        
        # Pattern 5: Semantic similarity check (close but not exact match)
        if self.use_embeddings and self.embedding_model:
            from .line_section_grouper import KNOWN_SECTIONS, SECTION_MAPPING
            
            section_embedding = self.embedding_model.encode([section_name])[0]
            known_embeddings = self.embedding_model.encode(KNOWN_SECTIONS)
            
            # Calculate similarities
            similarities = np.dot(known_embeddings, section_embedding) / (
                np.linalg.norm(known_embeddings, axis=1) * np.linalg.norm(section_embedding)
            )
            
            max_similarity = np.max(similarities)
            max_idx = np.argmax(similarities)
            
            # If similarity is in the "ambiguous" range (close but not confident)
            # Stricter threshold: only flag if 0.6 < sim < 0.80
            if 0.6 < max_similarity < 0.80:
                similar_section = KNOWN_SECTIONS[max_idx]
                # Get canonical name
                canonical = SECTION_MAPPING.get(similar_section, similar_section)
                return (
                    True,
                    f'Ambiguous match to "{canonical}"',
                    0.6,
                    canonical
                )
        
        # If none of the above, consider it valid
        return False, '', 0.0, None
    
    def suggest_corrections(self, unknown_sections: List[UnknownSection]) -> Dict[str, str]:
        """
        Suggest corrections for unknown sections
        
        Args:
            unknown_sections: List of unknown sections
            
        Returns:
            Dictionary mapping current name -> suggested name
        """
        corrections = {}
        
        for unk in unknown_sections:
            if unk.similar_to:
                corrections[unk.section.section_name] = unk.similar_to.title()
            elif 'too short' in unk.reason.lower():
                # Suggest merging with next section
                corrections[unk.section.section_name] = '[MERGE_WITH_NEXT]'
            elif 'too long' in unk.reason.lower():
                # Suggest treating as content
                corrections[unk.section.section_name] = '[TREAT_AS_CONTENT]'
        
        return corrections


if __name__ == "__main__":
    import sys
    from .document_detector import DocumentDetector
    from .word_extractor import WordExtractor
    from .layout_detector_histogram import LayoutDetector
    from .column_segmenter import ColumnSegmenter
    from .line_section_grouper import LineGrouper, SectionDetector
    
    if len(sys.argv) < 2:
        print("Usage: python unknown_section_detector.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Run full pipeline
    print("="*60)
    print("UNKNOWN SECTION DETECTION PIPELINE")
    print("="*60)
    
    # Steps 1-6
    doc_detector = DocumentDetector(verbose=False)
    doc_type = doc_detector.detect(file_path)
    
    word_extractor = WordExtractor(verbose=False)
    if doc_type.file_type == 'pdf':
        pages_words = word_extractor.extract_pdf_text_based(file_path)
    else:
        print("Only PDF supported for now")
        sys.exit(1)
    
    layout_detector = LayoutDetector(verbose=False)
    layouts = [layout_detector.detect_layout(words) for words in pages_words]
    
    column_segmenter = ColumnSegmenter(verbose=False)
    all_columns = column_segmenter.segment_document(pages_words, layouts)
    
    line_grouper = LineGrouper(verbose=False)
    all_lines = []
    for page_columns in all_columns:
        page_lines = line_grouper.group_columns_into_lines(page_columns)
        all_lines.extend(page_lines)
    
    section_detector = SectionDetector(use_embeddings=True, verbose=False)
    sections = section_detector.detect_sections(all_lines)
    
    print(f"\nDetected {len(sections)} sections")
    
    # Step 7: Unknown section detection
    print("\n" + "="*60)
    print("DETECTING UNKNOWN SECTIONS")
    print("="*60)
    
    unknown_detector = UnknownSectionDetector(verbose=True)
    unknown_sections = unknown_detector.detect_unknown_sections(sections)
    
    if unknown_sections:
        print("\n" + "="*60)
        print("UNKNOWN SECTIONS FOUND")
        print("="*60)
        for unk in unknown_sections:
            print(f"\nSection: {unk.section.section_name}")
            print(f"  Reason: {unk.reason}")
            print(f"  Confidence: {unk.confidence:.1%}")
            if unk.similar_to:
                print(f"  Similar to: {unk.similar_to}")
            print(f"  Metadata: {unk.metadata}")
        
        # Suggest corrections
        print("\n" + "="*60)
        print("SUGGESTED CORRECTIONS")
        print("="*60)
        corrections = unknown_detector.suggest_corrections(unknown_sections)
        for current, suggested in corrections.items():
            print(f"  '{current}' → '{suggested}'")
    else:
        print("\nNo unknown sections detected. All sections matched known patterns.")
