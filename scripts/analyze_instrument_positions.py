#!/usr/bin/env python3
"""
楽器の位置を詳細に分析するスクリプト
"""

import fitz
import sys
import os

def analyze_instrument_positions(pdf_path):
    """PDFから楽器の位置を特定"""
    
    try:
        pdf = fitz.open(pdf_path)
        
        print(f"\n🎵 Analyzing instrument positions in: {os.path.basename(pdf_path)}")
        print(f"  Total pages: {len(pdf)}")
        
        # 最初のページから楽器名を探す
        for page_num in range(min(3, len(pdf))):
            page = pdf[page_num]
            page_rect = page.rect
            
            print(f"\n📄 Page {page_num + 1} Analysis:")
            print(f"  Page height: {page_rect.height:.0f}")
            
            # テキストを位置情報付きで取得
            text_instances = page.get_text("dict")
            
            # 楽器名とその位置を収集
            instruments = []
            
            for block in text_instances["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            y_pos = span["bbox"][1]  # Y座標
                            
                            # 楽器名のパターン
                            instrument_keywords = [
                                "Vocal", "Vo", "Voice",
                                "Guitar", "Gt", "G.",
                                "Bass", "Ba", "B.",
                                "Keyboard", "Key", "Piano", "Pf",
                                "Drums", "Dr", "Perc",
                                "Cho", "Chorus"
                            ]
                            
                            for keyword in instrument_keywords:
                                if keyword.lower() in text.lower():
                                    # 相対位置を計算
                                    relative_pos = y_pos / page_rect.height
                                    instruments.append({
                                        "text": text,
                                        "y_pos": y_pos,
                                        "relative_pos": relative_pos,
                                        "page": page_num + 1
                                    })
                                    break
            
            # ソートして表示
            instruments.sort(key=lambda x: x["y_pos"])
            
            if instruments:
                print("\n  Found instruments (top to bottom):")
                for inst in instruments:
                    print(f"    {inst['text']:20} at Y:{inst['y_pos']:6.1f} ({inst['relative_pos']*100:4.1f}% from top)")
            
            # システムごとの分析
            if page_num == 0:  # 最初のページを詳細分析
                print("\n  System analysis (assuming 2 systems per page):")
                
                # 上半分（最初のシステム）
                print("  System 1 (0-50% of page):")
                system1_instruments = [i for i in instruments if i['relative_pos'] < 0.5]
                for inst in system1_instruments:
                    print(f"    {inst['text']:20} at {inst['relative_pos']*100:4.1f}%")
                
                # 下半分（2番目のシステム）
                print("  System 2 (50-100% of page):")
                system2_instruments = [i for i in instruments if i['relative_pos'] >= 0.5]
                for inst in system2_instruments:
                    print(f"    {inst['text']:20} at {inst['relative_pos']*100:4.1f}%")
        
        # 楽譜の視覚的構造を分析
        print("\n📊 Visual structure analysis:")
        page = pdf[0]
        
        # 五線譜やタブ譜の特徴的なパターンを探す
        drawings = page.get_drawings()
        line_positions = []
        
        for item in drawings:
            if item["type"] == "l":  # line
                y1 = item["items"][0][1]
                y2 = item["items"][1][1]
                if abs(y1 - y2) < 1:  # 水平線
                    line_positions.append(y1)
        
        # 線の密度から楽器パートを推定
        if line_positions:
            line_positions.sort()
            print(f"  Found {len(line_positions)} horizontal lines")
            
            # 線のクラスターを検出
            clusters = []
            current_cluster = [line_positions[0]]
            
            for i in range(1, len(line_positions)):
                if line_positions[i] - line_positions[i-1] < 10:  # 近い線
                    current_cluster.append(line_positions[i])
                else:
                    if len(current_cluster) >= 3:  # 3本以上の線のクラスター
                        clusters.append({
                            "start": min(current_cluster),
                            "end": max(current_cluster),
                            "count": len(current_cluster),
                            "relative_start": min(current_cluster) / page_rect.height,
                            "relative_end": max(current_cluster) / page_rect.height
                        })
                    current_cluster = [line_positions[i]]
            
            print(f"\n  Detected {len(clusters)} staff/tab clusters:")
            for i, cluster in enumerate(clusters[:10]):  # 最初の10個
                print(f"    Cluster {i+1}: {cluster['count']} lines at {cluster['relative_start']*100:.1f}%-{cluster['relative_end']*100:.1f}%")
        
        pdf.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 元のPDFを分析
    original_pdf = "/Users/Yodai/Downloads/Mela！.pdf"
    if os.path.exists(original_pdf):
        print("=" * 60)
        print("ORIGINAL PDF ANALYSIS")
        print("=" * 60)
        analyze_instrument_positions(original_pdf)
    
    # 抽出されたPDFも分析
    extracted_pdf = "/Users/Yodai/Downloads/extracted_20250722_025320.pdf"
    if os.path.exists(extracted_pdf):
        print("\n" + "=" * 60)
        print("EXTRACTED PDF ANALYSIS")
        print("=" * 60)
        analyze_instrument_positions(extracted_pdf)