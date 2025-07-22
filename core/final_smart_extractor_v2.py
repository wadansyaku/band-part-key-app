#!/usr/bin/env python3
"""
改良版最終スマート抽出器
- 1行に4小節を確実に表示
- ギター・ベースを除外してボーカルとキーボードのみ抽出
"""

import fitz
import os
from datetime import datetime

class FinalSmartExtractorV2:
    """改良版最終スマート抽出器"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595  # A4
        self.page_height = 842
        self.margin = 40
        
        # バンドスコアの標準的なレイアウト
        # 通常の配置（上から）：
        # 1. ボーカル（コード含む）: 0-25%
        # 2. ギター: 25-45%
        # 3. ベース: 45-65%
        # 4. キーボード/ピアノ: 65-85%
        # 5. ドラム: 85-100%
        
        # ボーカルは最上部25%
        self.vocal_start_ratio = 0.0
        self.vocal_end_ratio = 0.25
        
        # キーボードは中下部（ギター・ベースをスキップ）
        self.keyboard_start_ratio = 0.65
        self.keyboard_end_ratio = 0.85
    
    def extract_smart_final(self, pdf_path):
        """
        改良版スマート抽出
        - 1行に4小節を確実に表示
        - ギター・ベースを除外
        """
        
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力パス
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # プロジェクトルートからの相対パス
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(project_root, "outputs", "extracted_scores")
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(
                output_dir,
                f"{base_name}_final_v2_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction V2")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Mode: 4 measures per line")
            print(f"  - Parts: Vocal (top 25%) + Keyboard (65-85%)")
            
            # 現在の出力ページ
            current_page = output_pdf.new_page(
                width=self.page_width,
                height=self.page_height
            )
            current_y = self.margin
            output_page_count = 1
            
            # タイトル
            current_page.insert_text(
                (self.margin, current_y),
                base_name,
                fontsize=16,
                color=(0, 0, 0)
            )
            current_y += 35
            
            # 通算小節番号
            total_measure = 1
            
            # 各ページを処理
            for page_num in range(min(len(src_pdf), 20)):
                page = src_pdf[page_num]
                page_rect = page.rect
                
                # 通常、1ページには2システム（各8小節）がある
                # 各システムを4小節ずつに分割して処理
                systems_per_page = 2
                
                for sys_idx in range(systems_per_page):
                    # システムの垂直位置
                    system_y_start = page_rect.height * (sys_idx * 0.5)
                    system_y_end = page_rect.height * ((sys_idx + 1) * 0.5)
                    system_height = system_y_end - system_y_start
                    
                    # 1システム（8小節）を1回で処理（4小節として）
                    # 元のPDFの8小節分の幅全体を使用
                    x_start = 0
                    x_end = page_rect.width
                    
                    # 新しいページが必要かチェック
                    if current_y + 160 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # 小節番号
                    current_page.insert_text(
                        (self.margin, current_y),
                        f"Measures {total_measure}-{total_measure + 3}",
                        fontsize=12,
                        color=(0.3, 0.3, 0.3)
                    )
                    current_y += 20
                    
                    # 1. ボーカルパート（最上部25%のみ）
                    vocal_y_start = system_y_start + (system_height * self.vocal_start_ratio)
                    vocal_y_end = system_y_start + (system_height * self.vocal_end_ratio)
                    
                    try:
                        # 8小節分の幅を取得（4小節として表示）
                        vocal_clip = fitz.Rect(
                            x_start,
                            vocal_y_start,
                            x_end * 0.5,  # 前半4小節分
                            vocal_y_end
                        )
                        
                        vocal_dest = fitz.Rect(
                            self.margin + 40,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 80
                        )
                        
                        current_page.show_pdf_page(
                            vocal_dest, src_pdf, page_num, clip=vocal_clip
                        )
                        
                        # ラベル
                        current_page.insert_text(
                            (self.margin, current_y + 40),
                            "Vo",
                            fontsize=11,
                            color=(0, 0, 0.8)
                        )
                        
                        # 枠線
                        current_page.draw_rect(
                            vocal_dest,
                            color=(0.6, 0.6, 0.8),
                            width=0.5
                        )
                        
                    except Exception as e:
                        print(f"  Vocal placement error: {e}")
                    
                    current_y += 85
                    
                    # 2. キーボードパート（65-85%の範囲）
                    keyboard_y_start = system_y_start + (system_height * self.keyboard_start_ratio)
                    keyboard_y_end = system_y_start + (system_height * self.keyboard_end_ratio)
                    
                    try:
                        keyboard_clip = fitz.Rect(
                            x_start,
                            keyboard_y_start,
                            x_end * 0.5,  # 前半4小節分
                            keyboard_y_end
                        )
                        
                        keyboard_dest = fitz.Rect(
                            self.margin + 40,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 60
                        )
                        
                        current_page.show_pdf_page(
                            keyboard_dest, src_pdf, page_num, clip=keyboard_clip
                        )
                        
                        # ラベル
                        current_page.insert_text(
                            (self.margin, current_y + 30),
                            "Key",
                            fontsize=11,
                            color=(0, 0.5, 0)
                        )
                        
                        # 枠線
                        current_page.draw_rect(
                            keyboard_dest,
                            color=(0.6, 0.8, 0.6),
                            width=0.5
                        )
                        
                    except Exception as e:
                        print(f"  Keyboard placement error: {e}")
                    
                    current_y += 70
                    total_measure += 4
                    
                    # 同じシステムの後半4小節も処理
                    if current_y + 160 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # 後半4小節
                    current_page.insert_text(
                        (self.margin, current_y),
                        f"Measures {total_measure}-{total_measure + 3}",
                        fontsize=12,
                        color=(0.3, 0.3, 0.3)
                    )
                    current_y += 20
                    
                    # ボーカル（後半）
                    try:
                        vocal_clip = fitz.Rect(
                            x_end * 0.5,  # 後半4小節分
                            vocal_y_start,
                            x_end,
                            vocal_y_end
                        )
                        
                        vocal_dest = fitz.Rect(
                            self.margin + 40,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 80
                        )
                        
                        current_page.show_pdf_page(
                            vocal_dest, src_pdf, page_num, clip=vocal_clip
                        )
                        
                        current_page.insert_text(
                            (self.margin, current_y + 40),
                            "Vo",
                            fontsize=11,
                            color=(0, 0, 0.8)
                        )
                        
                        current_page.draw_rect(
                            vocal_dest,
                            color=(0.6, 0.6, 0.8),
                            width=0.5
                        )
                        
                    except Exception as e:
                        print(f"  Vocal placement error: {e}")
                    
                    current_y += 85
                    
                    # キーボード（後半）
                    try:
                        keyboard_clip = fitz.Rect(
                            x_end * 0.5,  # 後半4小節分
                            keyboard_y_start,
                            x_end,
                            keyboard_y_end
                        )
                        
                        keyboard_dest = fitz.Rect(
                            self.margin + 40,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 60
                        )
                        
                        current_page.show_pdf_page(
                            keyboard_dest, src_pdf, page_num, clip=keyboard_clip
                        )
                        
                        current_page.insert_text(
                            (self.margin, current_y + 30),
                            "Key",
                            fontsize=11,
                            color=(0, 0.5, 0)
                        )
                        
                        current_page.draw_rect(
                            keyboard_dest,
                            color=(0.6, 0.8, 0.6),
                            width=0.5
                        )
                        
                    except Exception as e:
                        print(f"  Keyboard placement error: {e}")
                    
                    current_y += 70
                    total_measure += 4
            
            # フッター
            if output_page_count > 0:
                footer_text = f"Generated by Band Part Key App - Total {output_page_count} pages"
                current_page.insert_text(
                    (self.margin, self.page_height - 20),
                    footer_text,
                    fontsize=8,
                    color=(0.5, 0.5, 0.5)
                )
            
            # 保存
            output_pdf.save(output_path)
            print(f"\n✅ Extraction Complete!")
            print(f"  Output: {output_path}")
            print(f"  Pages: {output_page_count}")
            print(f"  Total measures: {total_measure - 1}")
            
            src_pdf.close()
            output_pdf.close()
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None