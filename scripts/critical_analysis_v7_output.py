#!/usr/bin/env python3
"""
V7出力の厳密な分析
問題点を徹底的に洗い出す
"""

import fitz
import os
import numpy as np
import cv2

def critical_analysis(pdf_path):
    """PDFを厳しく分析して問題点を特定"""
    
    try:
        pdf = fitz.open(pdf_path)
        
        print(f"\n🔍 CRITICAL ANALYSIS OF: {os.path.basename(pdf_path)}")
        print("=" * 60)
        
        problems = []
        
        # 1. ページ数とレイアウトの分析
        print(f"\n📊 BASIC METRICS:")
        print(f"  Total pages: {len(pdf)}")
        
        # 2. 各ページの詳細分析
        for page_num in range(min(5, len(pdf))):
            page = pdf[page_num]
            
            print(f"\n📄 PAGE {page_num + 1} ANALYSIS:")
            
            # テキスト分析
            text = page.get_text()
            lines = text.split('\n')
            
            # 問題1: 楽器名の混入チェック
            unwanted_instruments = []
            for line in lines:
                line_lower = line.lower()
                if any(inst in line_lower for inst in ['gt.', 'guitar', 'ba.', 'bass', 'dr.', 'drums']):
                    unwanted_instruments.append(line.strip())
            
            if unwanted_instruments:
                problem = f"Page {page_num + 1}: Unwanted instruments detected: {unwanted_instruments}"
                problems.append(problem)
                print(f"  ❌ {problem}")
            
            # 問題2: 空白領域の分析
            mat = fitz.Matrix(1, 1)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.samples
            img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
            else:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # 各行の内容量を分析
            row_means = np.mean(gray, axis=1)
            empty_rows = np.sum(row_means > 250)  # 白い行
            empty_ratio = empty_rows / len(row_means)
            
            if empty_ratio > 0.4:
                problem = f"Page {page_num + 1}: Too much empty space ({empty_ratio*100:.1f}%)"
                problems.append(problem)
                print(f"  ⚠️  {problem}")
            
            # 問題3: コンテンツの位置分析
            non_white_pixels = np.where(gray < 200)
            if len(non_white_pixels[0]) > 0:
                min_y = np.min(non_white_pixels[0])
                max_y = np.max(non_white_pixels[0])
                content_height = max_y - min_y
                
                if content_height < pix.height * 0.5:
                    problem = f"Page {page_num + 1}: Content uses only {content_height/pix.height*100:.1f}% of page height"
                    problems.append(problem)
                    print(f"  ⚠️  {problem}")
            
            # 問題4: システムごとの分析
            # 画像を上下に分割して分析
            half_height = pix.height // 2
            
            for half_idx, half_name in enumerate(['Top', 'Bottom']):
                y_start = half_idx * half_height
                y_end = (half_idx + 1) * half_height
                
                half_img = gray[y_start:y_end, :]
                half_mean = np.mean(half_img)
                
                if half_mean > 240:  # ほぼ白
                    problem = f"Page {page_num + 1}: {half_name} half is mostly empty"
                    problems.append(problem)
                    print(f"  ⚠️  {problem}")
        
        # 3. ページ間の一貫性チェック
        print(f"\n🔄 CONSISTENCY CHECK:")
        
        page_contents = []
        for page_num in range(min(10, len(pdf))):
            page = pdf[page_num]
            mat = fitz.Matrix(0.5, 0.5)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.samples
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            
            # ページの特徴量
            content_ratio = np.sum(img_array < 200) / len(img_array)
            page_contents.append(content_ratio)
        
        # 標準偏差で一貫性をチェック
        if len(page_contents) > 1:
            std_dev = np.std(page_contents)
            if std_dev > 0.1:
                problem = f"Inconsistent page layouts (std dev: {std_dev:.3f})"
                problems.append(problem)
                print(f"  ❌ {problem}")
        
        # 4. 小節の連続性チェック
        print(f"\n🎵 MEASURE CONTINUITY CHECK:")
        
        # ページごとの楽譜内容を視覚的に分析
        missing_sections = []
        
        # 最初のページが適切に始まっているか
        first_page = pdf[0]
        first_text = first_page.get_text()
        
        if 'A' not in first_text and 'Intro' not in first_text:
            # 視覚的にも確認
            mat = fitz.Matrix(0.5, 0.5)
            pix = first_page.get_pixmap(matrix=mat)
            
            # 最初のページの上部が空でないかチェック
            img_data = pix.samples
            img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
            else:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            top_quarter = gray[:pix.height//4, :]
            if np.mean(top_quarter) > 240:
                problem = "First page might be missing the beginning (A section)"
                problems.append(problem)
                print(f"  ❌ {problem}")
        
        # 5. 総合評価
        print(f"\n📊 CRITICAL ISSUES FOUND: {len(problems)}")
        
        if problems:
            print(f"\n❌ MAJOR PROBLEMS:")
            for i, problem in enumerate(problems, 1):
                print(f"  {i}. {problem}")
        else:
            print(f"\n✅ No critical issues found")
        
        # 6. 視覚的サンプル生成
        for i in range(min(3, len(pdf))):
            page = pdf[i]
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            output_path = f"/Users/Yodai/band_part_key_app/outputs/v7_analysis_page_{i+1}.png"
            pix.save(output_path)
            print(f"\n📸 Visual sample saved: {output_path}")
        
        pdf.close()
        
        return problems
        
    except Exception as e:
        print(f"❌ Analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    pdf_path = "/Users/Yodai/Downloads/extracted_20250722_042932.pdf"
    
    if os.path.exists(pdf_path):
        problems = critical_analysis(pdf_path)
        
        # 改善提案
        print("\n" + "=" * 60)
        print("💡 IMPROVEMENT SUGGESTIONS:")
        
        if len(problems) > 5:
            print("\n1. MAJOR OVERHAUL NEEDED:")
            print("   - Too many issues detected")
            print("   - Consider complete redesign of extraction logic")
            
        print("\n2. SPECIFIC FIXES:")
        print("   - Ensure A section is included from the start")
        print("   - Remove ALL guitar/bass references")
        print("   - Optimize page space usage")
        print("   - Maintain consistent layout across pages")
        print("   - Verify measure continuity")
        
    else:
        print(f"PDF not found: {pdf_path}")