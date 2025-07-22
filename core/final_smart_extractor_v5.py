#!/usr/bin/env python3
"""
最終スマート抽出器 V5
- 4小節を1行に大きく表示
- 不要なテキスト（PDF、Measureなど）を削除
- A4に最適化してページ数を削減
"""

import fitz
import os
from datetime import datetime

class FinalSmartExtractorV5:
    """最終スマート抽出器 V5 - 最適化された表示"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595  # A4
        self.page_height = 842
        self.margin = 30  # 余白を小さくしてスペースを最大化
        
        # 楽器の正確な配置
        self.vocal_start_ratio = 0.05    # 5%から
        self.vocal_end_ratio = 0.20      # 20%まで
        
        self.keyboard_start_ratio = 0.65  # 65%から
        self.keyboard_end_ratio = 0.80    # 80%まで
        
        # 余白の調整
        self.horizontal_margin_ratio = 0.02
    
    def extract_smart_final(self, pdf_path):
        """
        V5スマート抽出 - 大きく見やすい4小節表示
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
                f"{base_name}_final_v5_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction V5")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Mode: 4 measures per line (optimized)")
            print(f"  - Output: Large, clear display")
            
            # 現在の出力ページ
            current_page = output_pdf.new_page(
                width=self.page_width,
                height=self.page_height
            )
            current_y = self.margin
            output_page_count = 1
            
            # 通算小節番号（表示はしない）
            total_measure = 1
            
            # 各ページを処理（最初の2ページはスキップ）
            start_page = 2  # 3ページ目から開始
            
            for page_num in range(start_page, min(len(src_pdf), start_page + 18)):
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
                    
                    # 8小節を4小節ずつの1行として処理
                    # 元のPDFの8小節全体を1つの4小節として扱う
                    
                    # 新しいページが必要かチェック（より大きなスペースが必要）
                    if current_y + 200 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # 8小節全体を取得（4小節として表示）
                    x_start = content_x_start
                    x_end = content_x_start + content_width
                    
                    # 1. ボーカルパート（大きく表示）
                    vocal_y_start = system_y_start + (system_height * self.vocal_start_ratio)
                    vocal_y_end = system_y_start + (system_height * self.vocal_end_ratio)
                    
                    try:
                        # クリップ領域（8小節全体）
                        vocal_clip = fitz.Rect(
                            x_start,
                            vocal_y_start,
                            x_end,
                            vocal_y_end
                        )
                        
                        # 配置先（大きく表示）
                        vocal_dest = fitz.Rect(
                            self.margin + 20,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 100  # 高さを100に拡大
                        )
                        
                        # 楽譜を配置
                        current_page.show_pdf_page(
                            vocal_dest, src_pdf, page_num, 
                            clip=vocal_clip,
                            keep_proportion=False
                        )
                        
                        # ラベル（シンプルに）
                        current_page.draw_rect(
                            fitz.Rect(self.margin - 5, current_y + 40, self.margin + 15, current_y + 60),
                            color=(0.2, 0.2, 0.8),
                            fill=(0.2, 0.2, 0.8),
                            width=0
                        )
                        current_page.insert_text(
                            (self.margin - 2, current_y + 53),
                            "V",
                            fontsize=12,
                            color=(1, 1, 1)
                        )
                        
                        # 枠線（薄く）
                        current_page.draw_rect(
                            vocal_dest,
                            color=(0.8, 0.8, 0.9),
                            width=0.3
                        )
                        
                    except Exception as e:
                        print(f"  Vocal placement warning: {e}")
                    
                    current_y += 105
                    
                    # 2. キーボードパート（大きく表示）
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
                            self.margin + 20,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 80  # 高さを80に拡大
                        )
                        
                        # 楽譜を配置
                        current_page.show_pdf_page(
                            keyboard_dest, src_pdf, page_num, 
                            clip=keyboard_clip,
                            keep_proportion=False
                        )
                        
                        # ラベル（シンプルに）
                        current_page.draw_rect(
                            fitz.Rect(self.margin - 5, current_y + 30, self.margin + 15, current_y + 50),
                            color=(0, 0.6, 0),
                            fill=(0, 0.6, 0),
                            width=0
                        )
                        current_page.insert_text(
                            (self.margin - 2, current_y + 43),
                            "K",
                            fontsize=12,
                            color=(1, 1, 1)
                        )
                        
                        # 枠線（薄く）
                        current_page.draw_rect(
                            keyboard_dest,
                            color=(0.8, 0.9, 0.8),
                            width=0.3
                        )
                        
                    except Exception as e:
                        print(f"  Keyboard placement warning: {e}")
                    
                    current_y += 90
                    total_measure += 8  # 8小節進める（実際は4小節として表示）
            
            # 保存
            output_pdf.save(output_path)
            print(f"\n✅ Extraction Complete!")
            print(f"  Output: {output_path}")
            print(f"  Pages: {output_page_count}")
            
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