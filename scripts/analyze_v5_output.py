#!/usr/bin/env python3
"""
V5出力の問題を分析
"""

import fitz
import os

def analyze_v5_issues(pdf_path):
    """V5の出力を分析して問題を特定"""
    
    try:
        pdf = fitz.open(pdf_path)
        
        print(f"\n📊 Analyzing V5 output: {os.path.basename(pdf_path)}")
        print(f"  Total pages: {len(pdf)}")
        
        # 最初の数ページをチェック
        for page_num in range(min(3, len(pdf))):
            page = pdf[page_num]
            
            print(f"\n📄 Page {page_num + 1}:")
            
            # テキストを取得
            text = page.get_text()
            lines = text.split('\n')
            
            # 楽器名を探す
            found_instruments = []
            for line in lines:
                if any(inst in line for inst in ["Gt", "Ba", "Dr", "Guitar", "Bass", "Drums"]):
                    found_instruments.append(line.strip())
            
            if found_instruments:
                print(f"  ⚠️  Found unwanted instruments:")
                for inst in found_instruments[:5]:  # 最初の5個
                    print(f"     - {inst}")
            
            # セクションマーカーを探す
            section_markers = []
            for line in lines:
                if any(marker in line for marker in ["A", "B", "C", "Intro", "Verse", "Chorus"]):
                    if len(line) < 10:  # 短いテキストのみ（セクションマーカーの可能性）
                        section_markers.append(line.strip())
            
            if section_markers:
                print(f"  📍 Section markers found:")
                for marker in section_markers[:5]:
                    print(f"     - {marker}")
        
        # 視覚的な確認のためプレビューを生成
        page = pdf[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        preview_path = "/Users/Yodai/band_part_key_app/outputs/v5_issue_preview.png"
        pix.save(preview_path)
        print(f"\n✅ Preview saved: {preview_path}")
        
        pdf.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    pdf_path = "/Users/Yodai/Downloads/extracted_20250722_033420.pdf"
    
    if os.path.exists(pdf_path):
        analyze_v5_issues(pdf_path)
    else:
        print("PDF not found")
        
    # 元のPDFの構造も再確認
    print("\n" + "="*60)
    print("ORIGINAL PDF STRUCTURE CHECK")
    print("="*60)
    
    original_pdf = "/Users/Yodai/Downloads/Mela！.pdf"
    if os.path.exists(original_pdf):
        pdf = fitz.open(original_pdf)
        
        # 各ページの構造を確認
        for page_num in [2, 3, 4]:  # 3-5ページ目
            if page_num < len(pdf):
                page = pdf[page_num]
                
                # ページのプレビューを生成
                mat = fitz.Matrix(0.5, 0.5)
                pix = page.get_pixmap(matrix=mat)
                preview_path = f"/Users/Yodai/band_part_key_app/outputs/original_page_{page_num + 1}_structure.png"
                pix.save(preview_path)
                print(f"Page {page_num + 1} preview: {preview_path}")
        
        pdf.close()