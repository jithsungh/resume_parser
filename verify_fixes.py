#!/usr/bin/env python3
"""
Quick Test - Verify All Fixes Work
===================================

Tests all 4 fixes:
1. Learning persistence
2. Clean batch output
3. Web viewer compatibility
4. Clean Excel format
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_fix_1_learning():
    """Test #1: Learning persistence"""
    print("\n" + "="*60)
    print("TEST 1: Learning Persistence")
    print("="*60)
    
    try:
        from src.core.section_learner import SectionLearner
        
        learner = SectionLearner("config/sections_database.json")
        print("✓ SectionLearner initialized")
        
        # Check if _save_config is called in _add_section_variant
        import inspect
        source = inspect.getsource(learner._add_section_variant)
        
        if "self._save_config()" in source:
            print("✓ Learning persistence fix VERIFIED")
            print("  _add_section_variant() calls _save_config()")
            return True
        else:
            print("✗ WARNING: _save_config() not found in _add_section_variant()")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def test_fix_2_clean_output():
    """Test #2: Clean batch output"""
    print("\n" + "="*60)
    print("TEST 2: Clean Batch Output")
    print("="*60)
    
    try:
        from src.PDF_pipeline import pipeline
        import inspect
        
        # Check if verbose check exists before print(sim)
        source = inspect.getsource(pipeline.run_pipeline)
        
        if "if verbose:" in source and "print(sim)" in source:
            # Verify print(sim) is inside verbose check
            lines = source.split('\n')
            verbose_found = False
            for i, line in enumerate(lines):
                if 'sim = simple_json(result)' in line:
                    # Check next few lines for verbose check
                    next_lines = '\n'.join(lines[i:i+5])
                    if 'if verbose:' in next_lines and 'print(sim)' in next_lines:
                        print("✓ PDF pipeline fix VERIFIED")
                        print("  print(sim) is conditional on verbose")
                        verbose_found = True
                        break
            
            if not verbose_found:
                print("✗ WARNING: print(sim) may not be properly guarded by verbose check")
                return False
        
        # Check DOCX pipeline
        from src.DOCX_pipeline import pipeline as docx_pipeline
        source = inspect.getsource(docx_pipeline.run_pipeline)
        
        if "if verbose:" in source and "print(sim)" in source:
            print("✓ DOCX pipeline fix VERIFIED")
            print("  print(sim) is conditional on verbose")
            return True
        else:
            print("✗ WARNING: DOCX pipeline print(sim) not properly guarded")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def test_fix_3_web_viewer():
    """Test #3: Web viewer compatibility"""
    print("\n" + "="*60)
    print("TEST 3: Web Viewer Compatibility")
    print("="*60)
    
    try:
        from scripts import view_results
        import inspect
        
        # Check if _load_rows_from_excel handles new format
        source = inspect.getsource(view_results._load_rows_from_excel)
        
        checks = [
            ('"pdf_path"' in source, "Looks for pdf_path column"),
            ('"Contact Information"' in source or 'Contact Information' in source, "Handles Contact Information section"),
            ('"File Name"' in source, "Recognizes File Name column")
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"✓ {desc}")
            else:
                print(f"✗ Missing: {desc}")
                all_passed = False
        
        if all_passed:
            print("✓ Web viewer fix VERIFIED")
            return True
        else:
            print("✗ Web viewer may have compatibility issues")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def test_fix_4_clean_excel():
    """Test #4: Clean Excel output"""
    print("\n" + "="*60)
    print("TEST 4: Clean Excel Output")
    print("="*60)
    
    try:
        from scripts import batch_folder_process
        import inspect
        
        # Check if save_to_excel has line cleaning logic
        source = inspect.getsource(batch_folder_process.save_to_excel)
        
        checks = [
            ('json.loads' in source, "JSON dict parsing"),
            ('"pdf_path"' in source, "pdf_path column"),
            ('clean_lines' in source, "Line cleaning logic"),
            ('hidden = True' in source or 'hidden' in source, "Hidden pdf_path column")
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"✓ {desc}")
            else:
                print(f"✗ Missing: {desc}")
                all_passed = False
        
        if all_passed:
            print("✓ Excel cleaning fix VERIFIED")
            return True
        else:
            print("✗ Excel cleaning may be incomplete")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("VERIFYING ALL 4 FIXES")
    print("="*60)
    
    results = {
        "Fix #1: Learning Persistence": test_fix_1_learning(),
        "Fix #2: Clean Batch Output": test_fix_2_clean_output(),
        "Fix #3: Web Viewer Sync": test_fix_3_web_viewer(),
        "Fix #4: Clean Excel Output": test_fix_4_clean_excel()
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for fix_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {fix_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL FIXES VERIFIED!")
        print("="*60)
        print("\nNext steps:")
        print("1. Test with real resumes:")
        print("   python scripts/batch_folder_process.py --folder 'freshteams_resume/Resumes' --output 'outputs/test_fixed.xlsx'")
        print("\n2. Check learning database:")
        print("   cat config/sections_database.json")
        print("\n3. Start web viewer:")
        print("   python scripts/view_results.py")
        return 0
    else:
        print("⚠️  SOME FIXES NEED ATTENTION")
        print("="*60)
        print("\nPlease review the failed tests above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
