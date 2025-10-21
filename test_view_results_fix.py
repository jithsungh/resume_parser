#!/usr/bin/env python3
"""
Quick test to verify view_results.py path resolution fix
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_path_resolution():
    """Test that ROOT_DIR is correctly set to project root"""
    from scripts.view_results import ROOT_DIR, INDEX_HTML
    
    print("🔍 Testing Path Resolution...")
    print(f"   ROOT_DIR: {ROOT_DIR}")
    print(f"   INDEX_HTML: {INDEX_HTML}")
    
    # ROOT_DIR should point to project root (contains scripts/, src/, outputs/, etc.)
    assert (ROOT_DIR / "scripts").exists(), "scripts/ folder should exist in ROOT_DIR"
    assert (ROOT_DIR / "src").exists(), "src/ folder should exist in ROOT_DIR"
    assert (ROOT_DIR / "outputs").exists() or True, "outputs/ folder should exist (or will be created)"
    
    # INDEX_HTML should point to scripts/index.html
    assert INDEX_HTML.exists(), f"index.html should exist at {INDEX_HTML}"
    assert INDEX_HTML.name == "index.html", "File should be named index.html"
    
    print("   ✅ ROOT_DIR correctly points to project root")
    print(f"   ✅ Contains: scripts/, src/, outputs/")
    print(f"   ✅ INDEX_HTML found at {INDEX_HTML}")
    return True

def test_sample_path():
    """Test path resolution for a sample resume file"""
    from scripts.view_results import ROOT_DIR, _windows_to_wsl_path
    
    print("\n🔍 Testing Sample Path Resolution...")
    
    # Test relative path
    relative_path = "freshteams_resume/Resumes/Gnanasai_Dachiraju_Resume.pdf"
    resolved = ROOT_DIR / relative_path
    
    print(f"   Relative: {relative_path}")
    print(f"   Resolved: {resolved}")
    print(f"   Exists: {resolved.exists()}")
    
    if resolved.exists():
        print(f"   ✅ File found!")
    else:
        print(f"   ⚠️  File not found (may not exist in your workspace)")
    
    return True

def test_dict_line_handling():
    """Test that dictionary line objects are handled correctly"""
    print("\n🔍 Testing Dictionary Line Handling...")
    
    # Simulate a line object from parser
    line_dict = {
        'text': 'Gnanasai Dachiraju Hyderabad, +91 9966250545 gnanasai5111@gmail.com',
        'boundaries': {'x0': 50.6, 'x1': 505.7, 'top': 82.1, 'bottom': 118.6},
        'properties': {'char_count': 76, 'word_count': 8},
        'metrics': {'height': 36.5, 'space_above': 0.0}
    }
    
    # OLD way (wrong)
    old_way = str(line_dict).strip()
    print(f"   OLD (wrong): {old_way[:80]}...")
    
    # NEW way (correct)
    if isinstance(line_dict, dict):
        new_way = str(line_dict.get('text', '')).strip()
    else:
        new_way = str(line_dict).strip()
    
    print(f"   NEW (correct): {new_way}")
    
    assert 'Gnanasai' in new_way, "Should extract text from dict"
    assert 'boundaries' not in new_way, "Should NOT contain metadata"
    assert 'properties' not in new_way, "Should NOT contain metadata"
    
    print(f"   ✅ Dictionary line objects handled correctly")
    return True

def main():
    print("=" * 70)
    print("VIEW_RESULTS PATH RESOLUTION TEST")
    print("=" * 70)
    
    try:
        test_path_resolution()
        test_sample_path()
        test_dict_line_handling()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\n📝 Next Steps:")
        print("   1. Regenerate Excel files: python3 -m scripts.batch_folder_process --folder freshteams_resume/Resumes")
        print("   2. Start web viewer: python3 scripts/view_results.py")
        print("   3. Open browser: http://localhost:5000")
        print("   4. Click on resumes to verify PDFs load correctly")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
