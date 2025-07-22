#!/usr/bin/env python3
"""
Quick startup test for Band Part Key App
"""

import sys
import os

def test_imports():
    """Test critical imports"""
    print("Testing imports...")
    
    try:
        import flask
        print("✓ Flask")
    except ImportError as e:
        print(f"✗ Flask: {e}")
        return False
    
    try:
        import fitz
        print("✓ PyMuPDF")
    except ImportError as e:
        print(f"✗ PyMuPDF: {e}")
        return False
    
    try:
        from core.final_smart_extractor import FinalSmartExtractor
        print("✓ FinalSmartExtractor")
    except ImportError as e:
        print(f"✗ FinalSmartExtractor: {e}")
        return False
    
    try:
        from core.pdf_type_detector import PDFTypeDetector
        print("✓ PDFTypeDetector")
    except ImportError as e:
        print(f"✗ PDFTypeDetector: {e}")
        return False
    
    return True

def test_directories():
    """Test required directories exist"""
    print("\nChecking directories...")
    
    dirs = ['core', 'templates', 'static', 'uploads', 'temp', 'outputs']
    all_good = True
    
    for d in dirs:
        if os.path.exists(d):
            print(f"✓ {d}/")
        else:
            print(f"✗ {d}/ (creating...)")
            os.makedirs(d, exist_ok=True)
    
    return all_good

def main():
    """Run startup tests"""
    print("=" * 50)
    print("Band Part Key App - Startup Test")
    print("=" * 50)
    
    if not test_imports():
        print("\n❌ Import test failed!")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
    
    test_directories()
    
    print("\n✅ All tests passed!")
    print("\nTo start the app:")
    print("  python app.py")
    print("\nTo test extraction:")
    print("  python test_final_smart_extractor.py")

if __name__ == "__main__":
    main()