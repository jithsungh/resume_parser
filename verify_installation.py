"""
Installation Verification Script
Checks if all components are properly installed and configured
"""
import sys
import os
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_python_version():
    """Check Python version"""
    print("\n🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro}")
        print(f"   Required: Python 3.8 or higher")
        return False


def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"   ✅ {package_name}")
        return True
    except ImportError:
        print(f"   ❌ {package_name} - Not installed")
        return False


def check_dependencies():
    """Check if all required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("transformers", "transformers"),
        ("torch", "torch"),
        ("spacy", "spacy"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("PyPDF2", "PyPDF2"),
        ("python-docx", "docx"),
        ("sentence-transformers", "sentence_transformers"),
    ]
    
    results = []
    for pkg_name, import_name in packages:
        results.append(check_package(pkg_name, import_name))
    
    return all(results)


def check_spacy_model():
    """Check if spaCy model is installed"""
    print("\n🔍 Checking spaCy model...")
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("   ✅ en_core_web_sm model installed")
        return True
    except OSError:
        print("   ❌ en_core_web_sm model not found")
        print("   Run: python -m spacy download en_core_web_sm")
        return False
    except Exception as e:
        print(f"   ❌ Error loading spaCy: {e}")
        return False


def check_model_directory():
    """Check if ML model directory exists"""
    print("\n🤖 Checking ML model...")
    model_path = Path("ml_model")
    
    if not model_path.exists():
        print("   ❌ ml_model directory not found")
        print("   Please ensure your trained model is in ./ml_model")
        return False
    
    required_files = ["config.json", "vocab.txt"]
    missing_files = []
    
    for file in required_files:
        if not (model_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"   ⚠️  Model directory exists but missing files: {', '.join(missing_files)}")
        return False
    
    print("   ✅ Model directory found with required files")
    return True


def check_project_structure():
    """Check if project structure is correct"""
    print("\n📁 Checking project structure...")
    
    required_dirs = [
        "src",
        "src/api",
        "src/core",
        "src/PDF_pipeline"
    ]
    
    required_files = [
        "src/api/main.py",
        "src/api/routes.py",
        "src/api/service.py",
        "src/api/models.py",
        "src/core/complete_resume_parser.py",
        "requirements.txt"
    ]
    
    all_good = True
    
    for directory in required_dirs:
        if Path(directory).exists():
            print(f"   ✅ {directory}/")
        else:
            print(f"   ❌ {directory}/ - Not found")
            all_good = False
    
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - Not found")
            all_good = False
    
    return all_good


def check_imports():
    """Check if API modules can be imported"""
    print("\n🔌 Checking API imports...")
    
    try:
        from src.api import models
        print("   ✅ src.api.models")
    except Exception as e:
        print(f"   ❌ src.api.models - {e}")
        return False
    
    try:
        from src.api import config
        print("   ✅ src.api.config")
    except Exception as e:
        print(f"   ❌ src.api.config - {e}")
        return False
    
    try:
        from src.core import complete_resume_parser
        print("   ✅ src.core.complete_resume_parser")
    except Exception as e:
        print(f"   ❌ src.core.complete_resume_parser - {e}")
        return False
    
    return True


def check_configuration():
    """Check if configuration files exist"""
    print("\n⚙️  Checking configuration...")
    
    if Path(".env").exists():
        print("   ✅ .env file found")
        env_good = True
    else:
        print("   ⚠️  .env file not found (optional)")
        print("   Copy .env.example to .env and configure if needed")
        env_good = False
    
    if Path("config/sections_database.json").exists():
        print("   ✅ sections_database.json found")
    else:
        print("   ⚠️  sections_database.json not found (optional)")
    
    return True  # Config is optional


def main():
    """Run all checks"""
    print_header("Resume Parser API - Installation Verification")
    
    results = {
        "Python Version": check_python_version(),
        "Dependencies": check_dependencies(),
        "spaCy Model": check_spacy_model(),
        "ML Model": check_model_directory(),
        "Project Structure": check_project_structure(),
        "API Imports": check_imports(),
        "Configuration": check_configuration()
    }
    
    print_header("Summary")
    
    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:12} {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to start the API server.")
        print("\n   Start the server with:")
        print("   python -m uvicorn src.api.main:app --reload")
        print("\n   Or use the startup script:")
        print("   start_api.bat (Windows) or bash start_api.sh (Linux/Mac)")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\n   Install missing packages:")
        print("   pip install -r requirements.txt")
        print("\n   Download spaCy model:")
        print("   python -m spacy download en_core_web_sm")
    
    print("\n" + "=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
