#!/bin/bash
# Setup script for enhanced name and location extraction

echo "🚀 Setting up Enhanced Name & Location Extraction..."
echo ""

# Install/upgrade spaCy
echo "📦 Installing spaCy..."
pip install -U spacy

# Download the English model
echo "📥 Downloading spaCy English model (en_core_web_sm)..."
python -m spacy download en_core_web_sm

echo ""
echo "✅ Setup complete!"
echo ""
echo "💡 Usage:"
echo "   from src.core.name_location_extractor import extract_name_and_location"
echo "   result = extract_name_and_location(resume_text, filename='john_doe.pdf', email='john.doe@email.com')"
echo ""
