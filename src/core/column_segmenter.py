"""
Step 4: Column Segmentation
============================
Splits words into columns based on layout detection results.

Features:
- Uses histogram-based column boundaries
- Handles global column structure across pages
- Assigns each word to its appropriate column
- Preserves word order within columns
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

from .word_extractor import WordMetadata
from .layout_detector_histogram import LayoutType


@dataclass
class Column:
    """Represents a column with its words"""
    column_id: int
    page: int
    x_start: float
    x_end: float
    words: List[WordMetadata]
    
    @property
    def word_count(self) -> int:
        return len(self.words)
    
    @property
    def width(self) -> float:
        return self.x_end - self.x_start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'column_id': self.column_id,
            'page': self.page,
            'x_start': self.x_start,
            'x_end': self.x_end,
            'word_count': self.word_count,
            'width': self.width,
            'words': [w.to_dict() for w in self.words]
        }


class ColumnSegmenter:
    """Segments words into columns"""
    
    def __init__(
        self, 
        overlap_threshold: float = 0.5,
        min_words_per_column: int = 10,
        verbose: bool = False
    ):
        """
        Initialize column segmenter
        
        Args:
            overlap_threshold: Minimum overlap ratio to assign word to column
            min_words_per_column: Minimum words for a column to be valid
            verbose: Print debug information
        """
        self.overlap_threshold = overlap_threshold
        self.min_words_per_column = min_words_per_column
        self.verbose = verbose
    
    def segment_page(
        self,
        words: List[WordMetadata],
        layout: LayoutType,
        page_num: int = 0
    ) -> List[Column]:
        """
        Segment a single page into columns
        
        Args:
            words: List of words for the page
            layout: Layout detection result
            page_num: Page number
            
        Returns:
            List of Column objects
        """
        if self.verbose:
            print(f"[ColumnSegmenter] Segmenting page {page_num + 1} into {layout.num_columns} column(s)")
        
        # Create columns
        columns = []
        
        for col_idx, (x_start, x_end) in enumerate(layout.column_boundaries):
            column = Column(
                column_id=col_idx,
                page=page_num,
                x_start=x_start,
                x_end=x_end,
                words=[]
            )
            columns.append(column)
        
        # Assign words to columns
        unassigned_words = []
        
        for word in words:
            assigned = False
            
            # Calculate overlap with each column
            for column in columns:
                overlap = self._calculate_overlap(word, column.x_start, column.x_end)
                
                if overlap >= self.overlap_threshold:
                    column.words.append(word)
                    assigned = True
                    break
            
            if not assigned:
                unassigned_words.append(word)
        
        # Handle unassigned words (assign to closest column)
        for word in unassigned_words:
            closest_col = self._find_closest_column(word, columns)
            if closest_col:
                closest_col.words.append(word)
          # Sort words within each column by Y position (top to bottom)
        for column in columns:
            column.words.sort(key=lambda w: w.bbox[1])
        
        # Filter out columns with too few words (merge into nearest valid column)
        valid_columns = []
        invalid_columns = []
        
        for column in columns:
            if column.word_count >= self.min_words_per_column:
                valid_columns.append(column)
            else:
                invalid_columns.append(column)
        
        # If no valid columns, keep all (don't filter)
        if not valid_columns:
            valid_columns = columns
            invalid_columns = []
        # Merge invalid columns into nearest valid column
        elif invalid_columns:
            for invalid_col in invalid_columns:
                if invalid_col.words:
                    # Find nearest valid column
                    nearest_col = min(
                        valid_columns,
                        key=lambda c: abs((c.x_start + c.x_end) / 2 - (invalid_col.x_start + invalid_col.x_end) / 2)
                    )
                    nearest_col.words.extend(invalid_col.words)
            
            # Re-sort merged columns
            for column in valid_columns:
                column.words.sort(key=lambda w: w.bbox[1])
        
        # Re-number columns
        for idx, column in enumerate(valid_columns):
            column.column_id = idx
        
        if self.verbose:
            for column in valid_columns:
                print(f"  Column {column.column_id}: {column.word_count} words "
                      f"(x: {column.x_start:.1f}-{column.x_end:.1f})")
            if unassigned_words:
                print(f"  Unassigned words: {len(unassigned_words)} (redistributed)")
            if invalid_columns:
                print(f"  Filtered {len(invalid_columns)} columns with <{self.min_words_per_column} words")
        
        return valid_columns
    
    def segment_document(
        self,
        pages_words: List[List[WordMetadata]],
        layouts: List[LayoutType]
    ) -> List[List[Column]]:
        """
        Segment entire document into columns
        
        Args:
            pages_words: List of word lists (one per page)
            layouts: List of layout detections (one per page)
            
        Returns:
            List of column lists (one list per page)
        """
        if self.verbose:
            print(f"[ColumnSegmenter] Segmenting {len(pages_words)} pages")
        
        all_columns = []
        
        for page_num, (words, layout) in enumerate(zip(pages_words, layouts)):
            columns = self.segment_page(words, layout, page_num)
            all_columns.append(columns)
        
        if self.verbose:
            total_columns = sum(len(page_cols) for page_cols in all_columns)
            print(f"  Total columns across all pages: {total_columns}")
        
        return all_columns
    
    def detect_global_column_structure(
        self,
        layouts: List[LayoutType]
    ) -> Tuple[int, List[Tuple[float, float]]]:
        """
        Detect consistent column structure across pages
        
        Args:
            layouts: List of layout detections for all pages
            
        Returns:
            Tuple of (most_common_num_columns, average_column_boundaries)
        """
        if not layouts:
            return (1, [(0, 612)])
        
        # Count column configurations
        column_counts = defaultdict(int)
        column_boundaries_by_count = defaultdict(list)
        
        for layout in layouts:
            num_cols = layout.num_columns
            column_counts[num_cols] += 1
            column_boundaries_by_count[num_cols].append(layout.column_boundaries)
        
        # Most common number of columns
        most_common_num = max(column_counts.items(), key=lambda x: x[1])[0]
        
        # Average boundaries for that configuration
        boundaries_list = column_boundaries_by_count[most_common_num]
        
        if not boundaries_list:
            return (most_common_num, [(0, 612)])
        
        # Average the boundaries
        avg_boundaries = []
        num_columns = len(boundaries_list[0])
        
        for col_idx in range(num_columns):
            x_starts = [bounds[col_idx][0] for bounds in boundaries_list]
            x_ends = [bounds[col_idx][1] for bounds in boundaries_list]
            
            avg_x_start = sum(x_starts) / len(x_starts)
            avg_x_end = sum(x_ends) / len(x_ends)
            
            avg_boundaries.append((avg_x_start, avg_x_end))
        
        if self.verbose:
            print(f"[ColumnSegmenter] Global structure: {most_common_num} columns")
            print(f"  Detected in {column_counts[most_common_num]}/{len(layouts)} pages")
        
        return (most_common_num, avg_boundaries)
    
    def _calculate_overlap(
        self,
        word: WordMetadata,
        col_x_start: float,
        col_x_end: float
    ) -> float:
        """
        Calculate overlap ratio between word and column
        
        Args:
            word: Word metadata
            col_x_start: Column start x
            col_x_end: Column end x
            
        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        word_x_start = word.bbox[0]
        word_x_end = word.bbox[2]
        
        # Calculate intersection
        intersection_start = max(word_x_start, col_x_start)
        intersection_end = min(word_x_end, col_x_end)
        
        if intersection_start >= intersection_end:
            return 0.0
        
        intersection_width = intersection_end - intersection_start
        word_width = word_x_end - word_x_start
        
        if word_width == 0:
            return 0.0
        
        return intersection_width / word_width
    
    def _find_closest_column(
        self,
        word: WordMetadata,
        columns: List[Column]
    ) -> Column:
        """
        Find closest column to word
        
        Args:
            word: Word metadata
            columns: List of columns
            
        Returns:
            Closest column
        """
        if not columns:
            return None
        
        word_x_center = word.x_center
        
        min_distance = float('inf')
        closest_col = columns[0]
        
        for column in columns:
            col_x_center = (column.x_start + column.x_end) / 2
            distance = abs(word_x_center - col_x_center)
            
            if distance < min_distance:
                min_distance = distance
                closest_col = column
        
        return closest_col


if __name__ == "__main__":
    import sys
    from .document_detector import DocumentDetector
    from .word_extractor import WordExtractor
    from .layout_detector_histogram import LayoutDetector
    
    if len(sys.argv) < 2:
        print("Usage: python column_segmenter.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Pipeline
    print("="*60)
    print("COLUMN SEGMENTATION PIPELINE")
    print("="*60)
    
    # Step 1: Detect document
    print("\n1. Document Detection")
    doc_detector = DocumentDetector(verbose=False)
    doc_type = doc_detector.detect(file_path)
    print(f"   File: {doc_type.file_type.upper()}, Scanned: {doc_type.is_scanned}")
    
    # Step 2: Extract words
    print("\n2. Word Extraction")
    word_extractor = WordExtractor(verbose=False)
    
    if doc_type.file_type == 'pdf':
        if doc_type.recommended_extraction == 'ocr':
            pages_words = word_extractor.extract_pdf_ocr(file_path)
        else:
            pages_words = word_extractor.extract_pdf_text_based(file_path)
    elif doc_type.file_type == 'docx':
        pages_words = word_extractor.extract_docx(file_path)
    else:
        print("   Unsupported file type")
        sys.exit(1)
    
    print(f"   Extracted {sum(len(p) for p in pages_words)} words from {len(pages_words)} pages")
    
    # Step 3: Detect layout
    print("\n3. Layout Detection")
    layout_detector = LayoutDetector(verbose=False)
    layouts = []
    
    for page_num, words in enumerate(pages_words):
        layout = layout_detector.detect_layout(words)
        layouts.append(layout)
        print(f"   Page {page_num + 1}: {layout.type_name}, {layout.num_columns} columns")
    
    # Step 4: Segment columns
    print("\n4. Column Segmentation")
    column_segmenter = ColumnSegmenter(verbose=True)
    all_columns = column_segmenter.segment_document(pages_words, layouts)
    
    # Step 5: Global structure
    print("\n5. Global Column Structure")
    num_cols, avg_bounds = column_segmenter.detect_global_column_structure(layouts)
    print(f"   Global: {num_cols} columns")
    for i, (x_start, x_end) in enumerate(avg_bounds, 1):
        print(f"   Column {i}: x={x_start:.1f} to {x_end:.1f}")
    
    print("\n" + "="*60)
    print("SEGMENTATION COMPLETE")
    print("="*60)
