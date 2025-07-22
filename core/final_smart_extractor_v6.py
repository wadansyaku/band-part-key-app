#!/usr/bin/env python3
"""
最終スマート抽出器 V6
- 正確な楽器位置で抽出（実際のPDF構造に基づく）
- Aセクションから開始
- GtやBaを完全に除外
"""

import fitz
import os
from datetime import datetime

class FinalSmartExtractorV6:
    """最終スマート抽出器 V6 - 正確な楽器配置"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595  # A4
        self.page_height = 842
        self.margin = 25  # 余白を最小化
        
        # 実際のPDF構造に基づく楽器配置
        # 各システム内での相対位置（実測値）
        self.vocal_start_ratio = 0.08    # 8%から（上部の空白を避ける）
        self.vocal_end_ratio = 0.16      # 16%まで（ボーカルのみ）
        
        self.keyboard_start_ratio = 0.73  # 73%から（ドラムの上）
        self.keyboard_end_ratio = 0.88    # 88%まで（ドラムを避ける）
        
        # 余白の調整
        self.horizontal_margin_ratio = 0.01  # 最小余白
    
    def extract_smart_final(self, pdf_path):
        """
        V6スマート抽出 - 正確な楽器位置で抽出
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
                f"{base_name}_final_v6_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction V6")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Mode: 4 measures per line (accurate positions)")
            print(f"  - Parts: Vocal only (8-16%) + Keyboard only (73-88%)")
            
            # 現在の出力ページ
            current_page = output_pdf.new_page(
                width=self.page_width,
                height=self.page_height
            )
            current_y = self.margin
            output_page_count = 1
            
            # 通算小節番号
            total_measure = 1
            
            # 最初のページ（インデックス0）は表紙なのでスキップ
            # 2ページ目（インデックス1）もタイトルページの可能性
            # 3ページ目（インデックス2）から開始してAセクションを含める
            start_page = 2  # 3ページ目から
            
            for page_num in range(start_page, min(len(src_pdf), start_page + 20)):
                page = src_pdf[page_num]
                page_rect = page.rect
                
                # ページの実際の楽譜領域
                content_width = page_rect.width * (1 - 2 * self.horizontal_margin_ratio)
                content_x_start = page_rect.width * self.horizontal_margin_ratio
                
                # 1ページに2システム
                systems_per_page = 2
                
                for sys_idx in range(systems_per_page):
                    # システムの垂直位置
                    system_y_start = page_rect.height * (sys_idx * 0.5)
                    system_height = page_rect.height * 0.5
                    
                    # 新しいページが必要かチェック
                    if current_y + 210 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # 8小節全体を4小節として表示
                    x_start = content_x_start
                    x_end = content_x_start + content_width
                    
                    # 1. ボーカルパート（正確な位置）
                    vocal_y_start = system_y_start + (system_height * self.vocal_start_ratio)
                    vocal_y_end = system_y_start + (system_height * self.vocal_end_ratio)
                    
                    try:
                        # クリップ領域
                        vocal_clip = fitz.Rect(
                            x_start,
                            vocal_y_start,
                            x_end,
                            vocal_y_end
                        )
                        
                        # 配置先（大きく表示）
                        vocal_dest = fitz.Rect(
                            self.margin + 15,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 110  # さらに大きく
                        )
                        
                        # 薄い背景
                        bg_rect = fitz.Rect(
                            vocal_dest.x0 - 1,
                            vocal_dest.y0 - 1,
                            vocal_dest.x1 + 1,
                            vocal_dest.y1 + 1
                        )
                        current_page.draw_rect(
                            bg_rect,
                            color=(0.98, 0.98, 1.0),
                            fill=(0.99, 0.99, 1.0),
                            width=0
                        )
                        
                        # 楽譜を配置
                        current_page.show_pdf_page(
                            vocal_dest, src_pdf, page_num, 
                            clip=vocal_clip,
                            keep_proportion=False
                        )
                        
                        # ミニマルなラベル
                        current_page.draw_circle(
                            fitz.Point(self.margin, current_y + 55),
                            8,
                            color=(0.2, 0.2, 0.8),
                            fill=(0.2, 0.2, 0.8)
                        )
                        current_page.insert_text(
                            (self.margin - 3, current_y + 58),
                            "V",
                            fontsize=10,
                            color=(1, 1, 1)
                        )
                        
                    except Exception as e:
                        print(f"  Vocal placement warning: {e}")
                    
                    current_y += 115
                    
                    # 2. キーボードパート（正確な位置）
                    keyboard_y_start = system_y_start + (system_height * self.keyboard_start_ratio)
                    keyboard_y_end = system_y_start + (system_height * self.keyboard_end_ratio)
                    
                    try:
                        keyboard_clip = fitz.Rect(
                            x_start,
                            keyboard_y_start,
                            x_end,
                            keyboard_y_end
                        )
                        
                        keyboard_dest = fitz.Rect(
                            self.margin + 15,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 85  # 大きく表示
                        )
                        
                        # 薄い背景
                        bg_rect = fitz.Rect(
                            keyboard_dest.x0 - 1,
                            keyboard_dest.y0 - 1,
                            keyboard_dest.x1 + 1,
                            keyboard_dest.y1 + 1
                        )
                        current_page.draw_rect(
                            bg_rect,
                            color=(0.98, 1.0, 0.98),
                            fill=(0.99, 1.0, 0.99),
                            width=0
                        )
                        
                        # 楽譜を配置
                        current_page.show_pdf_page(
                            keyboard_dest, src_pdf, page_num, 
                            clip=keyboard_clip,
                            keep_proportion=False
                        )
                        
                        # ミニマルなラベル
                        current_page.draw_circle(
                            fitz.Point(self.margin, current_y + 42),
                            8,
                            color=(0, 0.6, 0),
                            fill=(0, 0.6, 0)
                        )
                        current_page.insert_text(
                            (self.margin - 3, current_y + 45),
                            "K",
                            fontsize=10,
                            color=(1, 1, 1)
                        )
                        
                    except Exception as e:
                        print(f"  Keyboard placement warning: {e}")
                    
                    current_y += 95
                    total_measure += 8
            
            # 保存
            output_pdf.save(output_path)
            print(f"\n✅ Extraction Complete!")
            print(f"  Output: {output_path}")
            print(f"  Pages: {output_page_count}")
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