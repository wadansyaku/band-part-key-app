#!/usr/bin/env python3
"""
元のPDFの構造を詳細に分析
"""

import fitz
import os

def analyze_original_structure(pdf_path):
    """元のPDFの楽器配置を詳細分析"""
    
    try:
        pdf = fitz.open(pdf_path)
        
        print(f"\n📋 Analyzing original PDF structure: {os.path.basename(pdf_path)}")
        
        # 複数ページを分析して平均的な構造を把握
        page_num = 2  # 3ページ目（楽譜が始まるページ）
        
        if page_num < len(pdf):
            page = pdf[page_num]
            page_rect = page.rect
            
            print(f"\n🎵 Page {page_num + 1} (Main score page):")
            print(f"  Dimensions: {page_rect.width:.0f} x {page_rect.height:.0f}")
            
            # テキストを位置情報付きで取得
            text_instances = page.get_text("dict")
            
            # 楽器名を収集
            instruments = []
            all_texts = []
            
            for block in text_instances["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                bbox = span["bbox"]
                                y_pos = bbox[1]
                                x_pos = bbox[0]
                                
                                # すべてのテキストを記録
                                all_texts.append({
                                    "text": text[:30],  # 最初の30文字
                                    "x": x_pos,
                                    "y": y_pos,
                                    "relative_y": y_pos / page_rect.height
                                })
                                
                                # 楽器名を探す
                                instrument_patterns = [
                                    ("Vocal", ["Vocal", "Vo."]),
                                    ("Guitar I", ["Guitar I", "Gt. I"]),
                                    ("Guitar II", ["Guitar II", "Gt. II"]),
                                    ("Bass", ["Bass", "Ba."]),
                                    ("Keyboard", ["Keyboard I", "Keyb. I"]),
                                    ("Drums", ["Drums", "Dr."])
                                ]
                                
                                for inst_name, patterns in instrument_patterns:
                                    if any(p in text for p in patterns):
                                        instruments.append({
                                            "name": inst_name,
                                            "text": text,
                                            "x": x_pos,
                                            "y": y_pos,
                                            "relative_y": y_pos / page_rect.height
                                        })
                                        break
            
            # システムごとに楽器を分類
            system_height = page_rect.height / 2  # 2システム/ページ
            
            print("\n📊 Instrument layout by system:")
            
            for sys_idx in range(2):
                print(f"\n  System {sys_idx + 1} ({sys_idx * 50}%-{(sys_idx + 1) * 50}%):")
                
                system_start = sys_idx * system_height
                system_end = (sys_idx + 1) * system_height
                
                system_instruments = [
                    i for i in instruments 
                    if system_start <= i["y"] < system_end
                ]
                
                # Y座標でソート
                system_instruments.sort(key=lambda x: x["y"])
                
                if system_instruments:
                    # 相対位置を計算（システム内での位置）
                    for inst in system_instruments:
                        relative_in_system = (inst["y"] - system_start) / system_height
                        print(f"    {inst['name']:15} at {relative_in_system*100:4.1f}% of system (absolute: {inst['relative_y']*100:4.1f}%)")
                    
                    # 推奨される抽出範囲
                    print(f"\n    Recommended extraction ranges:")
                    
                    # ボーカルを探す
                    vocals = [i for i in system_instruments if i["name"] == "Vocal"]
                    if vocals:
                        vocal_start = (vocals[0]["y"] - system_start) / system_height
                        vocal_end = vocal_start + 0.15  # 15%の高さ
                        print(f"      Vocal: {vocal_start*100:.1f}% - {vocal_end*100:.1f}%")
                    
                    # キーボードを探す
                    keyboards = [i for i in system_instruments if i["name"] == "Keyboard"]
                    if keyboards:
                        kbd_start = (keyboards[0]["y"] - system_start) / system_height
                        kbd_end = kbd_start + 0.15
                        print(f"      Keyboard: {kbd_start*100:.1f}% - {kbd_end*100:.1f}%")
            
            # 最初の数行のテキストを表示（タイトル部分の確認）
            print("\n📝 First texts on page (to check for title):")
            all_texts.sort(key=lambda x: x["y"])
            for i, text_info in enumerate(all_texts[:10]):
                print(f"  {i+1}: Y={text_info['y']:6.1f} ({text_info['relative_y']*100:4.1f}%) - {text_info['text']}")
        
        pdf.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    original_pdf = "/Users/Yodai/Downloads/Mela！.pdf"
    
    if os.path.exists(original_pdf):
        analyze_original_structure(original_pdf)
    else:
        print("Original PDF not found")