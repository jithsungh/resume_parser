#!/bin/bash
# Quick setup for enhanced name and location extraction

echo "🚀 Enhanced Name & Location Extraction - Quick Setup"
echo "========================================================"
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

echo "✓ Python found: $(python --version)"
echo ""

# Install spaCy
echo "📦 Step 1: Installing spaCy..."
pip install -U spacy

if [ $? -eq 0 ]; then
    echo "   ✅ spaCy installed"
else
    echo "   ❌ Failed to install spaCy"
    exit 1
fi

echo ""

# Download English model
echo "📥 Step 2: Downloading English model (en_core_web_sm)..."
python -m spacy download en_core_web_sm

if [ $? -eq 0 ]; then
    echo "   ✅ Model downloaded"
else
    echo "   ❌ Failed to download model"
    exit 1
fi

echo ""
echo "=========================================================="
echo "✨ Setup Complete!"
echo "=========================================================="
echo ""
echo "🧪 Run tests:"
echo "   python test_name_extraction.py"
echo ""
echo "🎯 Run demo:"
echo "   python demo_enhanced_extraction.py"
echo ""
echo "📚 Documentation:"
echo "   See NAME_LOCATION_EXTRACTION.md"
echo ""
