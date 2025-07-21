#!/usr/bin/env python3
"""
起動時の依存関係チェック
"""

import sys

def check_dependencies():
    """必要な依存関係をチェック"""
    errors = []
    
    # Flask関連
    try:
        import flask
        print("✓ Flask: OK")
    except ImportError as e:
        errors.append(f"Flask: {e}")
    
    # PDF処理
    try:
        import fitz
        print("✓ PyMuPDF: OK")
    except ImportError as e:
        errors.append(f"PyMuPDF: {e}")
    
    # 画像処理
    try:
        import cv2
        print("✓ OpenCV: OK")
    except ImportError as e:
        errors.append(f"OpenCV: {e}")
    
    # OCR
    try:
        import pytesseract
        print("✓ Pytesseract: OK")
    except ImportError as e:
        errors.append(f"Pytesseract: {e}")
    
    # Tesseractバイナリの確認
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Tesseract binary: OK")
        else:
            errors.append("Tesseract binary not found")
    except Exception as e:
        errors.append(f"Tesseract binary: {e}")
    
    if errors:
        print("\n❌ エラーが見つかりました:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ すべての依存関係が正常です")
        return True

if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)