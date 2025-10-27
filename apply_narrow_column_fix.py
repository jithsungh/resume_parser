"""
Quick fix script for narrow column detection in layout_detector_histogram.py
This modifies the _detect_columns_by_gaps method to add aggressive fallback logic
"""

import re

def apply_fix():
    file_path = "c:/Users/jithsungh.v/projects/resume_parser/src/core/layout_detector_histogram.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the _detect_columns_by_gaps method and replace the fallback section
    old_fallback = '''        # Step 3.5: FALLBACK - If no columns detected but there are large gaps, retry with reduced threshold
        if not column_separators and max_gap > self.min_gap_width * 0.5:
            # Use a more aggressive threshold for narrow-column layouts
            fallback_threshold = max(self.min_gap_width * 0.5, percentile_60)
            if self.verbose:
                print(f"    No columns found, trying fallback threshold: {fallback_threshold:.1f}")
            
            for i in range(len(x_positions) - 1):
                right_edge = x_positions[i][1]
                next_left_edge = x_positions[i + 1][0]
                gap = next_left_edge - right_edge
                
                if gap >= fallback_threshold:
                    separator_x = (right_edge + next_left_edge) / 2
                    column_separators.append(separator_x)
        
        if not column_separators:
            return [(0, page_width)]'''
    
    new_fallback = '''        # Step 3.5: AGGRESSIVE FALLBACK - Use progressively lower thresholds
        if not column_separators:
            if self.verbose:
                print(f"    No columns found with primary threshold, trying fallback strategies...")
            
            # Collect gap information for fallback
            gap_positions = []
            for i in range(len(x_positions) - 1):
                right_edge = x_positions[i][1]
                next_left_edge = x_positions[i + 1][0]
                gap = next_left_edge - right_edge
                if gap > 0:
                    gap_positions.append((gap, right_edge, next_left_edge))
            
            # Try progressively more aggressive thresholds
            fallback_thresholds = [
                percentile_90,
                percentile_75,
                percentile_60,
                percentile_50,
                max(2.0, percentile_60 * 0.5),  # Very aggressive - 50% of p60 or 2pt minimum
                max(1.5, max_gap * 0.3)  # Ultra aggressive - 30% of max gap
            ]
            
            for idx, fallback_threshold in enumerate(fallback_thresholds):
                if fallback_threshold <= 0:
                    continue
                
                temp_separators = []
                for gap, right_edge, next_left_edge in gap_positions:
                    if gap >= fallback_threshold:
                        separator_x = (right_edge + next_left_edge) / 2
                        temp_separators.append(separator_x)
                
                # Check if we found valid columns
                if temp_separators:
                    # Merge close separators
                    merged = []
                    for sep in sorted(temp_separators):
                        if not merged or (sep - merged[-1]) >= self.min_column_width * 0.6:  # Relaxed
                            merged.append(sep)
                    
                    # Validate column widths
                    if merged:
                        valid = True
                        prev_x = 0
                        for sep in merged:
                            if sep - prev_x < self.min_column_width * 0.5:  # Allow 50% of min width
                                valid = False
                                break
                            prev_x = sep
                        
                        # Check last column
                        if valid and page_width - prev_x >= self.min_column_width * 0.5:
                            column_separators = merged
                            if self.verbose:
                                print(f"    ✓ Found columns with fallback threshold #{idx+1}: {fallback_threshold:.1f}")
                            break
        
        if not column_separators:
            return [(0, page_width)]'''
    
    # Replace
    if old_fallback in content:
        content = content.replace(old_fallback, new_fallback)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ Successfully applied narrow column detection fix!")
        print("  - Added progressive fallback thresholds")
        print("  - Relaxed column width requirements for narrow layouts")
        print("  - Added ultra-aggressive detection for type 3 resumes")
        return True
    else:
        print("✗ Could not find the fallback section to replace")
        print("  The file may have been modified already")
        return False

if __name__ == "__main__":
    apply_fix()
