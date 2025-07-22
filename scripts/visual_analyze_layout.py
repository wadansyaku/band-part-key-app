#!/usr/bin/env python3
"""
視覚的に楽器の配置を分析
"""

import fitz
import os

def visual_analyze_layout(pdf_path):
    """PDFのレイアウトを視覚的に分析"""
    
    try:
        pdf = fitz.open(pdf_path)
        
        # ページ3（通常楽譜が始まるページ）を分析
        page_num = 2  # 0-indexed
        if page_num >= len(pdf):
            page_num = 0
            
        page = pdf[page_num]
        
        # プレビュー画像を生成（詳細分析用）
        mat = fitz.Matrix(1.5, 1.5)  # 1.5倍の解像度
        pix = page.get_pixmap(matrix=mat)
        
        output_path = f"/Users/Yodai/band_part_key_app/outputs/original_page_{page_num + 1}_analysis.png"
        pix.save(output_path)
        
        print(f"✅ Visual analysis saved: {output_path}")
        print(f"   Page dimensions: {page.rect.width:.0f} x {page.rect.height:.0f}")
        
        # バンドスコアの一般的なレイアウトを提案
        print("\n📊 Standard band score layout (top to bottom):")
        print("  1. Title/Headers: 0-5%")
        print("  2. Vocal: 5-20%")
        print("  3. Guitar I: 20-35%")
        print("  4. Guitar II: 35-50%")
        print("  5. Bass: 50-65%")
        print("  6. Keyboard: 65-80%")
        print("  7. Drums: 80-95%")
        print("  8. Footer: 95-100%")
        
        print("\n🎯 For Vocal + Keyboard extraction:")
        print("  - Vocal: Extract 5-20% of each system")
        print("  - Keyboard: Extract 65-80% of each system")
        
        pdf.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    pdf_path = "/Users/Yodai/Downloads/Mela！.pdf"
    if os.path.exists(pdf_path):
        visual_analyze_layout(pdf_path)