"""
Step 5: Line & Section Grouping
================================
Groups words into lines and detects sections.

Process:
1. Group words into lines using tight y-overlap tolerance
2. Detect section headers using heuristics and semantic similarity
3. Define sections as content between headers
4. Ensure no lines are dropped

Section Header Detection:
- Bold + larger font
- All uppercase
- Semantic similarity to known sections
- Short length (1-5 words typically)
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import re

from .word_extractor import WordMetadata
from .column_segmenter import Column

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False


@dataclass
class Line:
    """Represents a line of text"""
    line_id: int
    page: int
    column_id: int
    y_position: float  # Top of line
    bbox: Tuple[float, float, float, float]  # Bounding box of entire line
    words: List[WordMetadata]
    text: str
    is_heading: bool = False
    heading_confidence: float = 0.0
    
    @property
    def word_count(self) -> int:
        return len(self.words)
    
    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'line_id': self.line_id,
            'page': self.page,
            'column_id': self.column_id,
            'y_position': self.y_position,
            'bbox': self.bbox,
            'text': self.text,
            'word_count': self.word_count,
            'is_heading': self.is_heading,
            'heading_confidence': self.heading_confidence,
            'words': [w.to_dict() for w in self.words]
        }


@dataclass
class Section:
    """Represents a section with header and content"""
    section_id: int
    page: int
    column_id: int
    section_name: str
    header_line: Optional[Line]
    content_lines: List[Line] = field(default_factory=list)
    
    @property
    def full_text(self) -> str:
        """Get full section text including header"""
        texts = []
        if self.header_line:
            texts.append(self.header_line.text)
        texts.extend(line.text for line in self.content_lines)
        return '\n'.join(texts)
    
    @property
    def content_text(self) -> str:
        """Get content text only (without header)"""
        return '\n'.join(line.text for line in self.content_lines)
    
    @property
    def line_count(self) -> int:
        return len(self.content_lines) + (1 if self.header_line else 0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'section_id': self.section_id,
            'page': self.page,
            'column_id': self.column_id,
            'section_name': self.section_name,
            'header': self.header_line.to_dict() if self.header_line else None,
            'content_lines': [line.to_dict() for line in self.content_lines],
            'line_count': self.line_count,
            'full_text': self.full_text
        }


# Load sections from database
import json
from pathlib import Path as PathLib

def load_sections_database(db_path: str = None) -> dict:
    """Load sections database from config"""
    if db_path is None:
        # Default path
        db_path = PathLib(__file__).parent.parent.parent / "config" / "sections_database.json"
    
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load sections database: {e}")
        # Return minimal default
        return {
            "sections": {
                "Experience": {"variants": ["experience", "work experience"]},
                "Education": {"variants": ["education", "academic background"]},
                "Skills": {"variants": ["skills", "technical skills"]},
                "Summary": {"variants": ["summary", "profile"]},
            }
        }

# Load database
_SECTIONS_DB = load_sections_database()

# Build flat list of all known section variants
KNOWN_SECTIONS = []
SECTION_MAPPING = {}  # variant -> canonical name

for canonical_name, section_data in _SECTIONS_DB.get("sections", {}).items():
    variants = section_data.get("variants", [])
    for variant in variants:
        KNOWN_SECTIONS.append(variant.lower())
        SECTION_MAPPING[variant.lower()] = canonical_name


class LineGrouper:
    """Groups words into lines"""
    
    def __init__(self, y_tolerance: float = 2.0, verbose: bool = False):
        """
        Initialize line grouper
        
        Args:
            y_tolerance: Tolerance for y-overlap (points)
            verbose: Print debug info
        """
        self.y_tolerance = y_tolerance
        self.verbose = verbose
    
    def group_column_into_lines(self, column: Column) -> List[Line]:
        """
        Group words in a column into lines
        
        Args:
            column: Column object with words
            
        Returns:
            List of Line objects
        """
        if not column.words:
            return []
        
        # Sort words by y-position (top to bottom), then x-position (left to right)
        sorted_words = sorted(column.words, key=lambda w: (w.bbox[1], w.bbox[0]))
        
        lines = []
        current_line_words = [sorted_words[0]]
        current_y = sorted_words[0].bbox[1]
        
        for word in sorted_words[1:]:
            word_y = word.bbox[1]
            
            # Check if word belongs to current line
            if abs(word_y - current_y) <= self.y_tolerance:
                current_line_words.append(word)
            else:
                # Create line from current words
                line = self._create_line(
                    current_line_words,
                    len(lines),
                    column.page,
                    column.column_id
                )
                lines.append(line)
                
                # Start new line
                current_line_words = [word]
                current_y = word_y
        
        # Add last line
        if current_line_words:
            line = self._create_line(
                current_line_words,
                len(lines),
                column.page,
                column.column_id
            )
            lines.append(line)
        
        if self.verbose:
            print(f"[LineGrouper] Column {column.column_id}: Grouped {len(column.words)} words into {len(lines)} lines")
        
        return lines
    
    def group_columns_into_lines(self, columns: List[Column]) -> List[Line]:
        """
        Group all columns into lines
        
        Args:
            columns: List of columns
            
        Returns:
            List of all lines from all columns
        """
        all_lines = []
        
        for column in columns:
            lines = self.group_column_into_lines(column)
            all_lines.extend(lines)
        
        return all_lines
    
    def _create_line(
        self,
        words: List[WordMetadata],
        line_id: int,
        page: int,
        column_id: int
    ) -> Line:
        """Create a Line object from words"""
        # Sort words left to right
        words_sorted = sorted(words, key=lambda w: w.bbox[0])
        
        # Calculate bounding box
        x0 = min(w.bbox[0] for w in words_sorted)
        y0 = min(w.bbox[1] for w in words_sorted)
        x1 = max(w.bbox[2] for w in words_sorted)
        y1 = max(w.bbox[3] for w in words_sorted)
        
        # Join text
        text = ' '.join(w.text for w in words_sorted)
        
        line = Line(
            line_id=line_id,
            page=page,
            column_id=column_id,
            y_position=y0,
            bbox=(x0, y0, x1, y1),
            words=words_sorted,
            text=text
        )
        
        return line


class SectionDetector:
    """Detects sections from lines"""
    
    def __init__(
        self,
        use_embeddings: bool = False,  # Disabled by default to avoid false positives
        embedding_threshold: float = 0.85,  # Higher threshold when enabled
        strict_matching: bool = True,  # Use strict keyword matching
        heading_confidence_threshold: float = 0.65,  # Minimum confidence for section headers
        verbose: bool = False
    ):
        """
        Initialize section detector
        
        Args:
            use_embeddings: Use semantic embeddings for matching (disabled by default)
            embedding_threshold: Minimum similarity for section match (0.85 for strict)
            strict_matching: Only match against known section variants
            heading_confidence_threshold: Minimum confidence for header detection
            verbose: Print debug info
        """
        self.use_embeddings = use_embeddings and HAS_EMBEDDINGS
        self.embedding_threshold = embedding_threshold
        self.strict_matching = strict_matching
        self.heading_confidence_threshold = heading_confidence_threshold
        self.verbose = verbose
        
        self.embedding_model = None
        self.section_embeddings = None
        
        if self.use_embeddings and HAS_EMBEDDINGS:
            self._init_embeddings()
    
    def _init_embeddings(self):
        """Initialize embedding model"""
        if self.verbose:
            print("[SectionDetector] Loading embedding model...")
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.section_embeddings = self.embedding_model.encode(KNOWN_SECTIONS)
        
        if self.verbose:
            print(f"  Loaded embeddings for {len(KNOWN_SECTIONS)} sections")
    
    def _clean_for_heading(self, text: str) -> str:
        """
        Clean text for heading matching (from old pipeline)
        
        Handles:
        - Letter-spaced text (e.g., "P R O F I L E" -> "PROFILE")
        - Spaced keywords (e.g., "E X P E R I E N C E" -> "EXPERIENCE")
        - Mixed spacing (e.g., "E Xperience" -> "EXPERIENCE")
        - Decorative separators
        - Special characters
        """
        t = text or ""
        
        # Handle letter-spaced text (e.g., "P R O F I L E")
        words = t.split()
        if len(words) > 1 and all(len(w) == 1 and w.isalpha() for w in words):
            t = ''.join(words)
        else:
            # Handle mixed spacing like "E Xperience" or "E X P E R I E N C E"
            # Check if words contain single letters mixed with multi-letter words
            has_single_letters = any(len(w) == 1 and w.isalpha() for w in words)
            if has_single_letters and len(words) > 1:
                # Try to reconstruct by removing spaces between single letters
                # and combining them with adjacent words
                reconstructed = []
                i = 0
                while i < len(words):
                    current = words[i]
                    # If single letter, keep collecting until we hit a multi-letter word
                    if len(current) == 1 and current.isalpha():
                        letters = [current]
                        i += 1
                        # Collect consecutive single letters
                        while i < len(words) and len(words[i]) == 1 and words[i].isalpha():
                            letters.append(words[i])
                            i += 1
                        # If next word exists and is multi-letter, append it
                        if i < len(words) and len(words[i]) > 1:
                            letters.append(words[i])
                            i += 1
                        reconstructed.append(''.join(letters))
                    else:
                        reconstructed.append(current)
                        i += 1
                
                # Use reconstructed if it's simpler (fewer words)
                if len(reconstructed) < len(words):
                    t = ' '.join(reconstructed)
        
        # Normalize decorators
        t = t.replace("•", " ").replace("·", " ").replace("|", " ")
        t = t.replace("&", " and ")
        t = t.replace("—", "-").replace("–", "-")
        t = re.sub(r'[^A-Za-z0-9\s:.-]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t
    
    def _despaced(self, text: str) -> str:
        """Remove all non-alphanumeric characters and lowercase"""
        if not text:
            return ""
        return re.sub(r"[^a-z0-9]+", "", text.lower())
    
    def _merge_duplicate_sections(self, sections: List[Section]) -> List[Section]:
        """
        Merge consecutive sections with the same canonical name.
        
        For example:
        - "Experience" (contact info) + "Experience" (work history) -> single "Experience"
        - "Skills" (languages) + "Skills" (technical) -> single "Skills"
        
        Args:
            sections: List of sections
            
        Returns:
            Merged list of sections with duplicates combined
        """
        if not sections:
            return sections
        
        merged = []
        current_merged = sections[0]
        
        for i in range(1, len(sections)):
            next_section = sections[i]
            
            # Check if section names match (case-insensitive)
            if current_merged.section_name.lower() == next_section.section_name.lower():
                # Merge: combine content lines
                # Keep the header from the first occurrence unless it doesn't have one
                if current_merged.header_line is None and next_section.header_line is not None:
                    current_merged.header_line = next_section.header_line
                
                # Add all content lines from next section
                current_merged.content_lines.extend(next_section.content_lines)
                
                # Also add the header of the duplicate as content if it exists
                if next_section.header_line is not None:
                    # Insert the duplicate header as a content line at the start of merged content
                    current_merged.content_lines.insert(
                        len(current_merged.content_lines) - len(next_section.content_lines),
                        next_section.header_line
                    )
                
                if self.verbose:
                    print(f"    ✓ Merged duplicate '{next_section.section_name}' section")
            else:
                # Different section - save current and start new
                merged.append(current_merged)
                current_merged = next_section
        
        # Add the last section
        merged.append(current_merged)
        
        # Re-number section IDs
        for i, section in enumerate(merged):
            section.section_id = i
        
        return merged
    
    def detect_sections(self, lines: List[Line]) -> List[Section]:
        """
        Detect sections from lines
        
        Args:
            lines: List of lines
            
        Returns:
            List of Section objects
        """
        if not lines:
            return []
        
        if self.verbose:
            print(f"[SectionDetector] Detecting sections from {len(lines)} lines")
        
        # Step 1: Identify potential headers with adjusted threshold
        header_candidates = []
        for i, line in enumerate(lines):
            is_heading, confidence = self._is_section_header(line)
            line.is_heading = is_heading
            line.heading_confidence = confidence
            
            if is_heading:
                header_candidates.append((i, line, confidence))
        
        if self.verbose:
            print(f"  Found {len(header_candidates)} potential headers")
        
        # Step 2: Create sections - ENSURE ALL LINES ARE INCLUDED
        sections = []
        current_section = None
        section_id = 0
        lines_processed = 0
        
        for i, line in enumerate(lines):
            if line.is_heading:
                # Save previous section (always save, even if empty)
                if current_section is not None:
                    sections.append(current_section)
                
                # Start new section
                section_name = self._match_section_name(line.text)
                
                current_section = Section(
                    section_id=section_id,
                    page=line.page,
                    column_id=line.column_id,
                    section_name=section_name,
                    header_line=line
                )                
                section_id += 1
                lines_processed += 1
            else:
                # Add to current section
                if current_section is None:
                    # Create default section for content before first header
                    # This is typically contact information at the top
                    current_section = Section(
                        section_id=section_id,
                        page=line.page,
                        column_id=line.column_id,
                        section_name="Contact Information",
                        header_line=None
                    )
                    section_id += 1
                
                current_section.content_lines.append(line)
                lines_processed += 1
        
        # Add last section (always add)
        if current_section is not None:
            sections.append(current_section)
        
        # Step 3: Merge duplicate sections
        sections = self._merge_duplicate_sections(sections)
        
        # Verification: Check all lines are accounted for
        total_lines_in_sections = sum(
            len(s.content_lines) + (1 if s.header_line else 0) 
            for s in sections
        )
        
        if total_lines_in_sections != len(lines):
            print(f"  ⚠️  WARNING: Line count mismatch!")
            print(f"     Input lines: {len(lines)}")
            print(f"     Lines in sections: {total_lines_in_sections}")
            print(f"     Missing: {len(lines) - total_lines_in_sections}")
        
        if self.verbose:
            print(f"  Detected {len(sections)} sections (after merging duplicates)")
            print(f"  Total lines processed: {total_lines_in_sections}/{len(lines)}")
            for section in sections:
                total = len(section.content_lines) + (1 if section.header_line else 0)
                print(f"    - {section.section_name}: {total} lines ({len(section.content_lines)} content + {1 if section.header_line else 0} header)")
        
        return sections
    
    def _is_section_header(self, line: Line) -> Tuple[bool, float]:
        """
        Check if line is a section header using STRICT keyword matching
        
        Strategy (like old pipeline):
        1. Check exact match against SECTION_MAPPING (known variants)
        2. Check "despaced" match (removes all non-alphanumeric)
        3. Use formatting only to boost confidence, not as primary signal
        4. Semantic matching only as last resort (very conservative)
        
        Args:
            line: Line to check
            
        Returns:
            Tuple of (is_header, confidence)
        """
        text = line.text.strip()
        
        if len(text) == 0:
            return False, 0.0
        
        # Clean text for matching
        text_clean = self._clean_for_heading(text)
        text_lower = text_clean.lower().rstrip(':')
        
        # STRICT MATCH 1: Exact variant match
        if text_lower in SECTION_MAPPING:
            base_confidence = 0.90  # High confidence for exact match
            reasons = ["exact_match"]
            
            # Boost with formatting signals
            if any(w.is_bold for w in line.words):
                base_confidence += 0.05
                reasons.append("bold")
            
            if text.isupper():
                base_confidence += 0.03
                reasons.append("UPPER")
            
            if line.words:
                avg_font_size = sum(w.font_size or 12 for w in line.words) / len(line.words)
                if avg_font_size > 14:
                    base_confidence += 0.02
                    reasons.append(f"font({avg_font_size:.1f})")
            
            confidence = min(base_confidence, 1.0)
            
            if self.verbose:
                print(f"    Header: '{text}' - conf={confidence:.2f} [{', '.join(reasons)}]")
            
            return True, confidence
        
        # STRICT MATCH 2: Despaced variant match (handles "E X P E R I E N C E")
        text_despaced = self._despaced(text_lower)
        
        # Build despaced lookup on-the-fly (could be cached)
        for variant, canonical in SECTION_MAPPING.items():
            despaced_variant = self._despaced(variant)
            if despaced_variant and despaced_variant == text_despaced:
                base_confidence = 0.85  # Slightly lower for despaced match
                reasons = ["despaced_match", canonical]
                
                # Boost with formatting
                if any(w.is_bold for w in line.words):
                    base_confidence += 0.05
                    reasons.append("bold")
                if text.isupper():
                    base_confidence += 0.03
                    reasons.append("UPPER")
                
                confidence = min(base_confidence, 1.0)
                
                if self.verbose:
                    print(f"    Header: '{text}' - conf={confidence:.2f} [{', '.join(reasons)}]")
                
                return True, confidence
        
        # NOT A HEADER using strict matching
        # Don't use heuristics-only to avoid false positives
        return False, 0.0
    
    def _calculate_semantic_similarity(self, text: str) -> float:
        """Calculate semantic similarity to known sections"""
        if not self.use_embeddings or self.embedding_model is None:
            return 0.0
        
        # Encode text
        text_embedding = self.embedding_model.encode([text.lower()])[0]
        
        # Calculate cosine similarity
        similarities = np.dot(self.section_embeddings, text_embedding) / (
            np.linalg.norm(self.section_embeddings, axis=1) * np.linalg.norm(text_embedding)
        )
        
        max_similarity = np.max(similarities)
        
        return max_similarity
      
    def _match_section_name(self, text: str) -> str:
        """
        Match header text to known section name
        
        Args:
            text: Header text
            
        Returns:
            Matched section name
        """
        text_clean = self._clean_for_heading(text)
        text_lower = text_clean.lower().strip().rstrip(':')
        
        # Exact match using database mapping
        if text_lower in SECTION_MAPPING:
            return SECTION_MAPPING[text_lower]
        
        # Despaced match (handles "E X P E R I E N C E")
        text_despaced = self._despaced(text_lower)
        for variant, canonical in SECTION_MAPPING.items():
            if self._despaced(variant) == text_despaced and text_despaced:
                return canonical
        
        # Partial match
        for variant, canonical in SECTION_MAPPING.items():
            if variant in text_lower or text_lower in variant:
                return canonical
        
        # Semantic match
        if self.use_embeddings:
            text_embedding = self.embedding_model.encode([text_lower])[0]
            similarities = np.dot(self.section_embeddings, text_embedding) / (
                np.linalg.norm(self.section_embeddings, axis=1) * np.linalg.norm(text_embedding)
            )
            
            max_idx = np.argmax(similarities)
            if similarities[max_idx] > self.embedding_threshold:
                matched_variant = KNOWN_SECTIONS[max_idx]
                # Return canonical name
                return SECTION_MAPPING.get(matched_variant, matched_variant.title())
        
        # Return original text (will be learned as new variant)
        return text.strip().title()


if __name__ == "__main__":
    import sys
    from .document_detector import DocumentDetector
    from .word_extractor import WordExtractor
    from .layout_detector_histogram import LayoutDetector
    from .column_segmenter import ColumnSegmenter
    
    if len(sys.argv) < 2:
        print("Usage: python line_section_grouper.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Full pipeline
    print("="*60)
    print("LINE & SECTION GROUPING PIPELINE")
    print("="*60)
    
    # Steps 1-4
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
    
    # Step 5: Line grouping
    print("\n5. Line Grouping")
    line_grouper = LineGrouper(verbose=True)
    all_lines = []
    for page_columns in all_columns:
        page_lines = line_grouper.group_columns_into_lines(page_columns)
        all_lines.extend(page_lines)
    
    print(f"   Total lines: {len(all_lines)}")
    
    # Step 6: Section detection
    print("\n6. Section Detection")
    section_detector = SectionDetector(use_embeddings=True, verbose=True)
    sections = section_detector.detect_sections(all_lines)
    
    print("\n" + "="*60)
    print("SECTIONS DETECTED")
    print("="*60)
    for section in sections:
        print(f"\n[{section.section_name}]")
        print(f"  Lines: {len(section.content_lines)}")
        if section.content_lines:
            preview = section.content_text[:200]
            print(f"  Preview: {preview}...")
