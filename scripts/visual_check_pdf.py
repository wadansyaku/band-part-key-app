#!/usr/bin/env python3
"""
PDFの視覚的確認とスクリーンショット生成
"""

import fitz
import sys
import os

def visual_check_pdf(pdf_path, page_num=0):
    """PDFの指定ページを画像として保存して視覚的に確認"""
    
    try:
        pdf = fitz.open(pdf_path)
        
        if page_num >= len(pdf):
            print(f"❌ Page {page_num} does not exist. Total pages: {len(pdf)}")
            return
        
        page = pdf[page_num]
        
        # 画像として保存
        mat = fitz.Matrix(2, 2)  # 2倍の解像度
        pix = page.get_pixmap(matrix=mat)
        
        output_path = f"/Users/Yodai/band_part_key_app/outputs/pdf_page_{page_num + 1}_preview.png"
        pix.save(output_path)
        
        print(f"✅ Preview saved: {output_path}")
        print(f"   Page size: {page.rect.width:.0f} x {page.rect.height:.0f}")
        
        # ページ内のテキストを簡易表示
        text = page.get_text()
        lines = text.split('\n')
        
        print(f"\n📄 Page {page_num + 1} content summary:")
        measure_lines = [line for line in lines if "Measure" in line]
        for line in measure_lines:
            print(f"   - {line}")
        
        pdf.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    pdf_path = "/Users/Yodai/Downloads/extracted_20250722_024446.pdf"
    
    # 最初の3ページをチェック
    for i in range(3):
        print(f"\n--- Checking page {i + 1} ---")
        visual_check_pdf(pdf_path, i)