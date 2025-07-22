#!/usr/bin/env python3
"""
V8とV9の出力を比較
"""

import fitz
import os

def compare_outputs(v8_path, v9_path):
    """V8とV9の出力を比較"""
    
    print(f"\n📊 COMPARING OUTPUTS:")
    print("=" * 50)
    
    # V8出力を確認
    if os.path.exists(v8_path):
        print(f"\n📄 V8 OUTPUT: {os.path.basename(v8_path)}")
        v8_pdf = fitz.open(v8_path)
        print(f"  Pages: {len(v8_pdf)}")
        
        # 最初のページの内容をチェック
        if len(v8_pdf) > 0:
            page = v8_pdf[0]
            text = page.get_text()
            
            # 楽器名をチェック
            bad_instruments = ['Guitar', 'Gt.', 'Bass', 'Ba.', 'Drums', 'Dr.']
            found_bad = [inst for inst in bad_instruments if inst in text]
            
            if found_bad:
                print(f"  ❌ Contains unwanted: {found_bad}")
            else:
                print(f"  ✅ Clean output")
            
            # プレビュー生成
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            preview_path = f"/Users/Yodai/band_part_key_app/outputs/v8_comparison_preview.png"
            pix.save(preview_path)
            print(f"  Preview: {preview_path}")
        
        v8_pdf.close()
    else:
        print(f"❌ V8 output not found: {v8_path}")
    
    # V9出力を確認
    if os.path.exists(v9_path):
        print(f"\n📄 V9 OUTPUT: {os.path.basename(v9_path)}")
        v9_pdf = fitz.open(v9_path)
        print(f"  Pages: {len(v9_pdf)}")
        
        # 最初のページの内容をチェック
        if len(v9_pdf) > 0:
            page = v9_pdf[0]
            text = page.get_text()
            
            # 楽器名をチェック
            bad_instruments = ['Guitar', 'Gt.', 'Bass', 'Ba.', 'Drums', 'Dr.']
            found_bad = [inst for inst in bad_instruments if inst in text]
            
            if found_bad:
                print(f"  ❌ Contains unwanted: {found_bad}")
            else:
                print(f"  ✅ Clean output")
            
            # プレビュー生成
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            preview_path = f"/Users/Yodai/band_part_key_app/outputs/v9_comparison_preview.png"
            pix.save(preview_path)
            print(f"  Preview: {preview_path}")
        
        v9_pdf.close()
    else:
        print(f"❌ V9 output not found: {v9_path}")

if __name__ == "__main__":
    v8_path = "/Users/Yodai/Downloads/extracted_20250722_044212.pdf"
    v9_path = "/Users/Yodai/band_part_key_app/outputs/extracted_scores/Mela！_final_v9_adaptive_20250722_134602.pdf"
    
    compare_outputs(v8_path, v9_path)