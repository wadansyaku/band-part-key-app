#!/usr/bin/env python3
"""
最終スマート抽出器 V8 修正版
- シンプルで確実なアプローチ
- 2ページ目から開始（通常楽譜が始まる）
- ボーカルとキーボードを正確に抽出
"""

import fitz
import os
from datetime import datetime

class FinalSmartExtractorV8Fixed:
    """最終スマート抽出器 V8 修正版"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595  # A4
        self.page_height = 842
        self.margin = 20
        
        # 実測に基づく楽器位置
        # より正確な位置設定
        self.vocal_start_ratio = 0.08    # 8%から
        self.vocal_end_ratio = 0.18      # 18%まで（歌詞含む）
        
        self.keyboard_start_ratio = 0.68  # 68%から（ベースの下）
        self.keyboard_end_ratio = 0.82    # 82%まで（ドラムの上）
    
    def extract_smart_final(self, pdf_path):
        """
        V8修正版スマート抽出
        """
        
        try:
            # PDFエラーを抑制
            fitz.TOOLS.mupdf_display_errors(False)
            
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
                f"{base_name}_final_v8_fixed_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction V8 Fixed")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Starting from: Page 2 (usual score start)")
            print(f"  - Parts: Vocal (8-18%) + Keyboard (68-82%)")
            
            # 現在の出力ページ
            current_page = output_pdf.new_page(
                width=self.page_width,
                height=self.page_height
            )
            current_y = self.margin
            output_page_count = 1
            
            # 通算小節番号
            total_measure = 1
            
            # 2ページ目から開始（インデックス1）
            start_page = 1
            end_page = min(len(src_pdf), 19)  # 最大19ページまで
            
            # 各ページを処理
            for page_num in range(start_page, end_page):
                page = src_pdf[page_num]
                page_rect = page.rect
                
                print(f"  Processing page {page_num + 1}...")
                
                # 各システムを処理（1ページ2システム）
                systems_per_page = 2
                
                for sys_idx in range(systems_per_page):
                    # システムの垂直位置
                    system_y_start = page_rect.height * (sys_idx * 0.5)
                    system_height = page_rect.height * 0.5
                    
                    # 新しいページが必要かチェック
                    if current_y + 230 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # 楽譜領域（フル幅）
                    x_start = 0
                    x_end = page_rect.width
                    
                    # 1. ボーカルパート
                    try:
                        vocal_y_start = system_y_start + (system_height * self.vocal_start_ratio)
                        vocal_y_end = system_y_start + (system_height * self.vocal_end_ratio)
                        
                        vocal_clip = fitz.Rect(
                            x_start,
                            vocal_y_start,
                            x_end,
                            vocal_y_end
                        )
                        
                        vocal_dest = fitz.Rect(
                            self.margin,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 120
                        )
                        
                        # 薄い背景
                        bg_rect = fitz.Rect(
                            vocal_dest.x0,
                            vocal_dest.y0,
                            vocal_dest.x1,
                            vocal_dest.y1
                        )
                        current_page.draw_rect(
                            bg_rect,
                            color=(0.95, 0.95, 1.0),
                            fill=(0.99, 0.99, 1.0),
                            width=0
                        )
                        
                        # 楽譜を配置
                        current_page.show_pdf_page(
                            vocal_dest, src_pdf, page_num, 
                            clip=vocal_clip,
                            keep_proportion=False
                        )
                        
                        # ラベル
                        label_rect = fitz.Rect(5, current_y + 50, 18, current_y + 70)
                        current_page.draw_rect(
                            label_rect,
                            color=(0.2, 0.2, 0.8),
                            fill=(0.2, 0.2, 0.8)
                        )
                        current_page.insert_text(
                            (8, current_y + 64),
                            "V",
                            fontsize=11,
                            color=(1, 1, 1)
                        )
                        
                        # 枠線（薄く）
                        current_page.draw_rect(
                            vocal_dest,
                            color=(0.8, 0.8, 0.9),
                            width=0.3
                        )
                        
                    except Exception as e:
                        print(f"    Vocal error: {e}")
                    
                    current_y += 125
                    
                    # 2. キーボードパート
                    try:
                        keyboard_y_start = system_y_start + (system_height * self.keyboard_start_ratio)
                        keyboard_y_end = system_y_start + (system_height * self.keyboard_end_ratio)
                        
                        keyboard_clip = fitz.Rect(
                            x_start,
                            keyboard_y_start,
                            x_end,
                            keyboard_y_end
                        )
                        
                        keyboard_dest = fitz.Rect(
                            self.margin,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 100
                        )
                        
                        # 薄い背景
                        bg_rect = fitz.Rect(
                            keyboard_dest.x0,
                            keyboard_dest.y0,
                            keyboard_dest.x1,
                            keyboard_dest.y1
                        )
                        current_page.draw_rect(
                            bg_rect,
                            color=(0.95, 1.0, 0.95),
                            fill=(0.99, 1.0, 0.99),
                            width=0
                        )
                        
                        # 楽譜を配置
                        current_page.show_pdf_page(
                            keyboard_dest, src_pdf, page_num, 
                            clip=keyboard_clip,
                            keep_proportion=False
                        )
                        
                        # ラベル
                        label_rect = fitz.Rect(5, current_y + 40, 18, current_y + 60)
                        current_page.draw_rect(
                            label_rect,
                            color=(0, 0.6, 0),
                            fill=(0, 0.6, 0)
                        )
                        current_page.insert_text(
                            (8, current_y + 54),
                            "K",
                            fontsize=11,
                            color=(1, 1, 1)
                        )
                        
                        # 枠線
                        current_page.draw_rect(
                            keyboard_dest,
                            color=(0.8, 0.9, 0.8),
                            width=0.3
                        )
                        
                    except Exception as e:
                        print(f"    Keyboard error: {e}")
                    
                    current_y += 110
                    total_measure += 8
            
            # 保存
            output_pdf.save(output_path)
            print(f"\n✅ Extraction Complete!")
            print(f"  Output: {output_path}")
            print(f"  Pages processed: {end_page - start_page}")
            print(f"  Output pages: {output_page_count}")
            print(f"  Total measures: {total_measure - 1}")
            
            src_pdf.close()
            output_pdf.close()
            
            # エラー表示を元に戻す
            fitz.TOOLS.mupdf_display_errors(True)
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None