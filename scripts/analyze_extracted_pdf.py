#!/usr/bin/env python3
"""
抽出されたPDFの批判的分析
"""

import fitz
import sys

def analyze_extracted_pdf(pdf_path):
    """抽出されたPDFを分析して問題点を確認"""
    
    try:
        pdf = fitz.open(pdf_path)
        print(f"\n📊 PDF Analysis: {pdf_path}")
        print(f"  Total pages: {len(pdf)}")
        
        # ページごとの分析
        issues_found = []
        
        for page_num in range(min(3, len(pdf))):  # 最初の3ページを詳細分析
            page = pdf[page_num]
            page_rect = page.rect
            
            print(f"\n  Page {page_num + 1}:")
            print(f"    - Size: {page_rect.width:.0f} x {page_rect.height:.0f}")
            
            # テキストオブジェクトの分析
            text_instances = page.get_text("dict")
            text_count = 0
            measure_labels = []
            part_labels = []
            
            for block in text_instances["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                text_count += 1
                                if "Measure" in text:
                                    measure_labels.append(text)
                                elif text in ["Vo", "Key"]:
                                    part_labels.append(text)
            
            print(f"    - Text objects: {text_count}")
            print(f"    - Measure labels: {measure_labels}")
            print(f"    - Part labels: {part_labels}")
            
            # 画像の分析
            image_list = page.get_images()
            print(f"    - Images: {len(image_list)}")
            
            # 描画オブジェクトの分析（四角形など）
            drawings = page.get_drawings()
            rect_count = 0
            for item in drawings:
                if item["type"] == "r":  # rectangle
                    rect_count += 1
            print(f"    - Rectangles: {rect_count}")
            
            # 問題点のチェック
            if page_num < 10:  # 最初の10ページで小節番号をチェック
                if measure_labels:
                    for label in measure_labels:
                        # "Measures X-Y" の形式をチェック
                        if "-" in label:
                            parts = label.split("-")
                            if len(parts) == 2:
                                try:
                                    start = int(parts[0].replace("Measures", "").strip())
                                    end = int(parts[1].strip())
                                    measures_per_line = end - start + 1
                                    if measures_per_line != 4:
                                        issues_found.append(f"Page {page_num + 1}: {measures_per_line} measures per line (should be 4)")
                                except:
                                    pass
        
        # 全ページの簡易チェック
        total_measure_instances = 0
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text()
            total_measure_instances += text.count("Measures")
        
        print(f"\n📈 Summary:")
        print(f"  - Total 'Measures' instances: {total_measure_instances}")
        print(f"  - Average per page: {total_measure_instances / len(pdf):.1f}")
        
        if issues_found:
            print(f"\n⚠️  Issues found:")
            for issue in issues_found:
                print(f"  - {issue}")
        else:
            print(f"\n✅ No major issues detected in measure counting")
        
        # PDFの実際の内容を表示（最初のページ）
        print(f"\n📄 First page text content:")
        first_page_text = pdf[0].get_text()
        lines = first_page_text.split('\n')
        for i, line in enumerate(lines[:20]):  # 最初の20行
            if line.strip():
                print(f"  {i+1}: {line.strip()}")
        
        pdf.close()
        
    except Exception as e:
        print(f"❌ Error analyzing PDF: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/Yodai/Downloads/extracted_20250722_024446.pdf"
    analyze_extracted_pdf(pdf_path)