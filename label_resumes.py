"""
Resume Labeling Interface - Streamlit App
Interactive PDF viewer with automatic feature extraction and manual labeling.
"""

import streamlit as st
import fitz  # PyMuPDF
from pathlib import Path
import pandas as pd
import json
from PIL import Image
import io
from typing import List, Dict, Any
import sys

from resume_feature_extractor import ResumeFeatureExtractor, ResumeFeatures


# Page config
st.set_page_config(
    page_title="Resume Layout Labeler",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)


class ResumeLabelingApp:
    """Main application class for resume labeling"""
    
    def __init__(self, pdf_directory: str, dataset_path: str = "dataset.csv"):
        self.pdf_directory = Path(pdf_directory)
        self.dataset_path = Path(dataset_path)
        self.feature_extractor = ResumeFeatureExtractor(verbose=False)
        
        # Initialize session state
        if 'current_index' not in st.session_state:
            st.session_state.current_index = 0
        if 'pdf_files' not in st.session_state:
            st.session_state.pdf_files = self._load_pdf_files()
        if 'labeled_files' not in st.session_state:
            st.session_state.labeled_files = self._load_labeled_files()
        if 'current_features' not in st.session_state:
            st.session_state.current_features = None
    
    def _load_pdf_files(self) -> List[Path]:
        """Load all PDF files from directory"""
        if not self.pdf_directory.exists():
            st.error(f"Directory not found: {self.pdf_directory}")
            return []
        
        pdf_files = sorted(self.pdf_directory.glob("**/*.pdf"))
        return pdf_files
    
    def _load_labeled_files(self) -> set:
        """Load set of already labeled filenames"""
        if not self.dataset_path.exists():
            return set()
        
        try:
            df = pd.read_csv(self.dataset_path)
            return set(df['filename'].values)
        except Exception as e:
            st.warning(f"Could not load existing dataset: {e}")
            return set()
    
    def _get_unlabeled_files(self) -> List[Path]:
        """Get list of unlabeled PDF files"""
        return [
            pdf for pdf in st.session_state.pdf_files
            if pdf.name not in st.session_state.labeled_files
        ]
    
    def _render_pdf_page(self, pdf_path: Path, page_num: int = 0, zoom: float = 2.0) -> Image.Image:
        """Render PDF page as PIL Image"""
        doc = fitz.open(str(pdf_path))
        page = doc[page_num]
        
        # Render at higher resolution for clarity
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        
        return img
    
    def _extract_features(self, pdf_path: Path) -> ResumeFeatures:
        """Extract features from PDF"""
        words, page_width, page_height = self.feature_extractor.extract_words_and_bbox(str(pdf_path))
        features = self.feature_extractor.compute_features(words, page_width, page_height)
        return features
    
    def _save_label(self, pdf_path: Path, features: ResumeFeatures, label: int):
        """Save label and features to dataset"""
        # Prepare row data
        row_data = {
            'filename': pdf_path.name,
            **features.to_dict(),
            'label': label
        }
        
        # Create or append to CSV
        df_new = pd.DataFrame([row_data])
        
        if self.dataset_path.exists():
            df_existing = pd.read_csv(self.dataset_path)
            df = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df = df_new
        
        df.to_csv(self.dataset_path, index=False)
        
        # Update labeled files
        st.session_state.labeled_files.add(pdf_path.name)
        
        # Also save JSON version for easier inspection
        json_path = self.dataset_path.with_suffix('.json')
        df.to_json(json_path, orient='records', indent=2)
    
    def _move_to_next_unlabeled(self):
        """Move to next unlabeled PDF"""
        unlabeled = self._get_unlabeled_files()
        if unlabeled:
            # Find the next unlabeled file
            current_files = st.session_state.pdf_files
            current_pdf = current_files[st.session_state.current_index] if st.session_state.current_index < len(current_files) else None
            
            # If current is labeled, find next unlabeled
            if current_pdf and current_pdf.name in st.session_state.labeled_files:
                for idx, pdf in enumerate(current_files[st.session_state.current_index + 1:], start=st.session_state.current_index + 1):
                    if pdf.name not in st.session_state.labeled_files:
                        st.session_state.current_index = idx
                        st.session_state.current_features = None
                        return
                
                # If no unlabeled found after current, wrap around
                for idx, pdf in enumerate(current_files):
                    if pdf.name not in st.session_state.labeled_files:
                        st.session_state.current_index = idx
                        st.session_state.current_features = None
                        return
    
    def run(self):
        """Main application loop"""
        st.title("📄 Resume Layout Labeler")
        st.markdown("---")
        
        # Check if we have PDFs
        if not st.session_state.pdf_files:
            st.error(f"No PDF files found in: {self.pdf_directory}")
            st.info("Please update the PDF directory path in the sidebar.")
            return
        
        # Sidebar controls
        with st.sidebar:
            st.header("📊 Progress")
            total_pdfs = len(st.session_state.pdf_files)
            labeled_count = len(st.session_state.labeled_files)
            unlabeled = self._get_unlabeled_files()
            
            st.metric("Total PDFs", total_pdfs)
            st.metric("Labeled", labeled_count)
            st.metric("Remaining", len(unlabeled))
            
            progress = labeled_count / total_pdfs if total_pdfs > 0 else 0
            st.progress(progress)
            
            st.markdown("---")
            st.header("⚙️ Settings")
            
            show_features = st.checkbox("Show Computed Features", value=True)
            zoom_level = st.slider("PDF Zoom", 1.0, 3.0, 2.0, 0.1)
            
            st.markdown("---")
            st.header("📁 Dataset")
            st.text(f"Path: {self.dataset_path}")
            
            if st.button("🔄 Reload Dataset"):
                st.session_state.labeled_files = self._load_labeled_files()
                st.rerun()
            
            if st.button("⏭️ Skip to Next Unlabeled"):
                self._move_to_next_unlabeled()
                st.rerun()
        
        # Main content area
        if not unlabeled:
            st.success("🎉 All PDFs have been labeled!")
            st.balloons()
            
            # Show dataset summary
            if self.dataset_path.exists():
                df = pd.read_csv(self.dataset_path)
                st.header("Dataset Summary")
                st.dataframe(df)
                
                st.subheader("Label Distribution")
                label_counts = df['label'].value_counts().sort_index()
                st.bar_chart(label_counts)
            return
        
        # Get current PDF
        current_pdf = st.session_state.pdf_files[st.session_state.current_index]
        
        # Auto-skip to next unlabeled
        if current_pdf.name in st.session_state.labeled_files:
            self._move_to_next_unlabeled()
            st.rerun()
        
        # Display PDF info
        st.header(f"📄 {current_pdf.name}")
        st.caption(f"File {st.session_state.current_index + 1} of {total_pdfs} | {len(unlabeled)} unlabeled remaining")
        
        # Two-column layout
        col_pdf, col_controls = st.columns([2, 1])
        
        with col_pdf:
            st.subheader("PDF Preview")
            
            try:
                # Render PDF
                with st.spinner("Rendering PDF..."):
                    img = self._render_pdf_page(current_pdf, zoom=zoom_level)
                    st.image(img, use_container_width=True)
            
            except Exception as e:
                st.error(f"Error rendering PDF: {e}")
                return
        
        with col_controls:
            st.subheader("Labeling Controls")
            
            # Extract features if not already done
            if st.session_state.current_features is None:
                with st.spinner("Extracting features..."):
                    try:
                        st.session_state.current_features = self._extract_features(current_pdf)
                    except Exception as e:
                        st.error(f"Error extracting features: {e}")
                        st.session_state.current_features = None
                        return
            
            features = st.session_state.current_features
            
            # Show features if enabled
            if show_features and features:
                st.markdown("#### 🔍 Computed Features")
                features_dict = features.to_dict()
                
                # Display in expandable sections
                with st.expander("Column Detection", expanded=True):
                    st.metric("Number of Columns", features_dict['num_columns'])
                    st.metric("Gutter Coverage", f"{features_dict['coverage_gutter']:.3f}")
                    st.metric("Valley Depth", f"{features_dict['valley_depth_ratio']:.3f}")
                
                with st.expander("Layout Structure"):
                    st.metric("Full-Width Line Ratio", f"{features_dict['full_width_line_ratio']:.3f}")
                    st.metric("Horizontal Lines Count", features_dict['horizontal_lines_count'])
                    st.metric("Header Fraction", f"{features_dict['header_fraction']:.3f}")
                
                with st.expander("Text Distribution"):
                    st.metric("Mean Y-Overlap", f"{features_dict['mean_y_overlap']:.3f}")
                    st.metric("Avg Word Width Ratio", f"{features_dict['avg_word_width_ratio']:.3f}")
                    st.metric("Line Density Variance", f"{features_dict['line_density_variance']:.2f}")
            
            st.markdown("---")
            st.markdown("#### 🏷️ Assign Label")
            
            # Layout type descriptions
            with st.expander("ℹ️ Layout Type Guide"):
                st.markdown("""
                **Type 1: Single Column**
                - Traditional single-column layout
                - Text flows top to bottom
                - No side-by-side sections
                
                **Type 2: Multi-Column**
                - Clean 2-column layout throughout
                - Consistent gutter between columns
                - Minimal full-width sections
                
                **Type 3: Hybrid/Complex**
                - Mixed layout with both single and multi-column
                - Full-width headers/sections
                - Complex structure with varying layouts
                """)
            
            # Label buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📋 Type 1", use_container_width=True, type="primary"):
                    self._save_label(current_pdf, features, 1)
                    st.success("✅ Labeled as Type 1")
                    self._move_to_next_unlabeled()
                    st.rerun()
            
            with col2:
                if st.button("📰 Type 2", use_container_width=True, type="primary"):
                    self._save_label(current_pdf, features, 2)
                    st.success("✅ Labeled as Type 2")
                    self._move_to_next_unlabeled()
                    st.rerun()
            
            with col3:
                if st.button("🔀 Type 3", use_container_width=True, type="primary"):
                    self._save_label(current_pdf, features, 3)
                    st.success("✅ Labeled as Type 3")
                    self._move_to_next_unlabeled()
                    st.rerun()
            
            # Navigation buttons
            st.markdown("---")
            nav_col1, nav_col2 = st.columns(2)
            
            with nav_col1:
                if st.button("⬅️ Previous", use_container_width=True):
                    if st.session_state.current_index > 0:
                        st.session_state.current_index -= 1
                        st.session_state.current_features = None
                        st.rerun()
            
            with nav_col2:
                if st.button("➡️ Next", use_container_width=True):
                    if st.session_state.current_index < total_pdfs - 1:
                        st.session_state.current_index += 1
                        st.session_state.current_features = None
                        st.rerun()


def main():
    """Entry point for Streamlit app"""
    
    # Configuration
    st.sidebar.header("📁 Configuration")
    
    # PDF directory input
    default_dir = st.sidebar.text_input(
        "PDF Directory",
        value="Resumes",
        help="Path to directory containing PDF resumes"
    )
    
    # Dataset path
    dataset_path = st.sidebar.text_input(
        "Dataset Output Path",
        value="./dataset.csv",
        help="Path where labeled dataset will be saved"
    )
    
    st.sidebar.markdown("---")
    
    # Initialize and run app
    try:
        app = ResumeLabelingApp(default_dir, dataset_path)
        app.run()
    except Exception as e:
        st.error(f"Application error: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()
