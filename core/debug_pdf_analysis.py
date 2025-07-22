#!/usr/bin/env python3
"""
PDF内容の詳細分析ツール
楽器ラベル検出失敗の原因を特定
"""

import fitz
import os

def analyze_pdf_text_structure(pdf_path: str):
    """PDFのテキスト構造を詳細分析"""
    print(f"🔍 PDF Text Structure Analysis")
    print(f"Input: {os.path.basename(pdf_path)}")
    print("="*60)
    
    try:
        pdf = fitz.open(pdf_path)
        
        # 最初の数ページを分析
        for page_num in range(min(3, len(pdf))):
            page = pdf[page_num]
            
            print(f"\n📄 PAGE {page_num + 1} ANALYSIS:")
            print(f"   Size: {page.rect.width:.1f} x {page.rect.height:.1f}")
            
            # 方法1: 基本テキスト取得
            basic_text = page.get_text()
            print(f"   Basic text length: {len(basic_text)}")
            
            # 楽器名らしきテキストを探す
            lines = basic_text.split('\n')
            instrument_candidates = []
            for line in lines:
                line = line.strip()
                if line and len(line) < 20:  # 短い行（楽器名の可能性）
                    if any(term in line.lower() for term in ['vo', 'key', 'gt', 'ba', 'dr', 'vocal', 'keyboard', 'guitar', 'bass', 'drum']):
                        instrument_candidates.append(line)
            
            if instrument_candidates:
                print(f"   🎵 Instrument candidates: {instrument_candidates}")
            else:
                print(f"   ⚠️  No instrument names found in basic text")
            
            # 方法2: テキストブロック詳細解析
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            print(f"   Text blocks: {len(blocks)}")
            
            instrument_blocks = []
            for i, block in enumerate(blocks):
                if "lines" in block:  # テキストブロック
                    bbox = block.get("bbox", [0, 0, 0, 0])
                    
                    # ブロック内のテキストを抽出
                    block_text = ""
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")
                    
                    block_text = block_text.strip()
                    
                    # 楽器名チェック
                    if block_text and len(block_text) < 30:
                        if any(term in block_text.lower() for term in ['vo', 'key', 'gt', 'ba', 'dr', 'vocal', 'keyboard', 'guitar', 'bass', 'drum']):
                            instrument_blocks.append({
                                'text': block_text,
                                'bbox': bbox,
                                'x': bbox[0],
                                'y': bbox[1]
                            })
            
            if instrument_blocks:
                print(f"   🏷️  Instrument blocks found: {len(instrument_blocks)}")
                for block in instrument_blocks[:5]:  # 最初の5つ
                    print(f"      '{block['text']}' at ({block['x']:.1f}, {block['y']:.1f})")
            else:
                print(f"   ❌ No instrument blocks found")
            
            # 方法3: 左端領域の詳細解析
            print(f"   🔍 Left margin analysis (0-200px):")
            
            left_rect = fitz.Rect(0, 0, 200, page.rect.height)
            left_text = page.get_textbox(left_rect)
            
            if left_text:
                left_lines = left_text.split('\n')
                left_candidates = []
                for line in left_lines:
                    line = line.strip()
                    if line and len(line) < 20:
                        left_candidates.append(line)
                
                print(f"      Left text lines: {len(left_candidates)}")
                for line in left_candidates[:10]:  # 最初の10行
                    print(f"        '{line}'")
            else:
                print(f"      ❌ No text found in left margin")
            
            # 方法4: 座標別テキスト取得
            print(f"   🎯 Coordinate-based text extraction:")
            
            # 左端をより細かく分析
            for x in [0, 50, 100, 150]:
                for y in range(0, int(page.rect.height), 100):
                    rect = fitz.Rect(x, y, x + 100, y + 50)
                    text = page.get_textbox(rect)
                    if text and text.strip():
                        text_clean = text.strip().replace('\n', ' ')
                        if len(text_clean) < 50:  # 短いテキストのみ
                            print(f"        ({x}, {y}): '{text_clean}'")
        
        pdf.close()
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file = "/Users/Yodai/Downloads/だから僕は音楽を辞めた.pdf"
    if os.path.exists(test_file):
        analyze_pdf_text_structure(test_file)
    else:
        print("❌ Test file not found")