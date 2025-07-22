#!/usr/bin/env python3
"""
改良版最終スマート抽出器 V3
- PDFエラーの回避
- より正確な楽譜配置
- 視覚的品質の改善
"""

import fitz
import os
from datetime import datetime

class FinalSmartExtractorV3:
    """改良版最終スマート抽出器 V3"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595  # A4
        self.page_height = 842
        self.margin = 40
        
        # バンドスコアの標準的なレイアウト
        # ボーカルは最上部25%（コード・メロディ・歌詞を含む）
        self.vocal_start_ratio = 0.0
        self.vocal_end_ratio = 0.25
        
        # キーボードは65-85%（ギター・ベースをスキップ）
        self.keyboard_start_ratio = 0.65
        self.keyboard_end_ratio = 0.85
        
        # 余白の調整
        self.horizontal_margin_ratio = 0.05  # 左右の余白
    
    def extract_smart_final(self, pdf_path):
        """
        改良版スマート抽出 V3
        - エラー処理の改善
        - より正確な楽譜配置
        """
        
        try:
            # PDFエラーを抑制するための設定
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
                f"{base_name}_final_v3_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction V3")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Mode: 4 measures per line (improved)")
            print(f"  - Parts: Vocal + Keyboard only")
            
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
            
            # 各ページを処理（最大20ページ）
            for page_num in range(min(len(src_pdf), 20)):
                page = src_pdf[page_num]
                page_rect = page.rect
                
                # ページの実際の楽譜領域を考慮（余白を除く）
                content_width = page_rect.width * (1 - 2 * self.horizontal_margin_ratio)
                content_x_start = page_rect.width * self.horizontal_margin_ratio
                
                # 通常、1ページには2システム（各8小節）
                systems_per_page = 2
                
                for sys_idx in range(systems_per_page):
                    # システムの垂直位置
                    system_y_start = page_rect.height * (sys_idx * 0.5)
                    system_y_end = page_rect.height * ((sys_idx + 1) * 0.5)
                    system_height = system_y_end - system_y_start
                    
                    # 1システム（8小節）を2つの4小節グループに分割
                    for half_idx in range(2):
                        # 新しいページが必要かチェック
                        if current_y + 160 > self.page_height - self.margin:
                            # フッターを追加
                            if output_page_count > 0:
                                footer_text = f"Page {output_page_count}"
                                current_page.insert_text(
                                    (self.page_width / 2 - 20, self.page_height - 20),
                                    footer_text,
                                    fontsize=8,
                                    color=(0.5, 0.5, 0.5)
                                )
                            
                            current_page = output_pdf.new_page(
                                width=self.page_width,
                                height=self.page_height
                            )
                            current_y = self.margin
                            output_page_count += 1
                        
                        # 4小節分の水平位置
                        x_start = content_x_start + (content_width * half_idx * 0.5)
                        x_end = content_x_start + (content_width * (half_idx + 0.5))
                        
                        # 小節番号
                        current_page.insert_text(
                            (self.margin, current_y),
                            f"Measures {total_measure}-{total_measure + 3}",
                            fontsize=12,
                            color=(0.3, 0.3, 0.3)
                        )
                        current_y += 20
                        
                        # 1. ボーカルパート（コード・メロディ・歌詞統合）
                        vocal_y_start = system_y_start + (system_height * self.vocal_start_ratio)
                        vocal_y_end = system_y_start + (system_height * self.vocal_end_ratio)
                        
                        try:
                            # クリップ領域（少し余裕を持たせる）
                            vocal_clip = fitz.Rect(
                                x_start - 5,
                                vocal_y_start,
                                x_end + 5,
                                vocal_y_end
                            )
                            
                            # 配置先
                            vocal_dest = fitz.Rect(
                                self.margin + 30,
                                current_y,
                                self.page_width - self.margin,
                                current_y + 85
                            )
                            
                            # 薄い背景色
                            bg_rect = fitz.Rect(
                                vocal_dest.x0 - 2,
                                vocal_dest.y0 - 2,
                                vocal_dest.x1 + 2,
                                vocal_dest.y1 + 2
                            )
                            current_page.draw_rect(
                                bg_rect,
                                color=(0.9, 0.9, 1.0),
                                fill=(0.98, 0.98, 1.0),
                                width=0
                            )
                            
                            # 楽譜を配置
                            current_page.show_pdf_page(
                                vocal_dest, src_pdf, page_num, 
                                clip=vocal_clip,
                                keep_proportion=True
                            )
                            
                            # ラベル
                            label_rect = fitz.Rect(
                                self.margin - 5,
                                current_y + 35,
                                self.margin + 25,
                                current_y + 50
                            )
                            current_page.draw_rect(
                                label_rect,
                                color=(0, 0, 0.8),
                                fill=(0, 0, 0.8),
                                width=0
                            )
                            current_page.insert_text(
                                (self.margin, current_y + 45),
                                "Vo",
                                fontsize=11,
                                color=(1, 1, 1)
                            )
                            
                            # 枠線
                            current_page.draw_rect(
                                vocal_dest,
                                color=(0.6, 0.6, 0.8),
                                width=0.5
                            )
                            
                        except Exception as e:
                            print(f"  Vocal placement warning: {e}")
                        
                        current_y += 90
                        
                        # 2. キーボードパート
                        keyboard_y_start = system_y_start + (system_height * self.keyboard_start_ratio)
                        keyboard_y_end = system_y_start + (system_height * self.keyboard_end_ratio)
                        
                        try:
                            keyboard_clip = fitz.Rect(
                                x_start - 5,
                                keyboard_y_start,
                                x_end + 5,
                                keyboard_y_end
                            )
                            
                            keyboard_dest = fitz.Rect(
                                self.margin + 30,
                                current_y,
                                self.page_width - self.margin,
                                current_y + 65
                            )
                            
                            # 薄い背景色
                            bg_rect = fitz.Rect(
                                keyboard_dest.x0 - 2,
                                keyboard_dest.y0 - 2,
                                keyboard_dest.x1 + 2,
                                keyboard_dest.y1 + 2
                            )
                            current_page.draw_rect(
                                bg_rect,
                                color=(0.9, 1.0, 0.9),
                                fill=(0.98, 1.0, 0.98),
                                width=0
                            )
                            
                            # 楽譜を配置
                            current_page.show_pdf_page(
                                keyboard_dest, src_pdf, page_num, 
                                clip=keyboard_clip,
                                keep_proportion=True
                            )
                            
                            # ラベル
                            label_rect = fitz.Rect(
                                self.margin - 5,
                                current_y + 25,
                                self.margin + 25,
                                current_y + 40
                            )
                            current_page.draw_rect(
                                label_rect,
                                color=(0, 0.5, 0),
                                fill=(0, 0.5, 0),
                                width=0
                            )
                            current_page.insert_text(
                                (self.margin - 2, current_y + 35),
                                "Key",
                                fontsize=11,
                                color=(1, 1, 1)
                            )
                            
                            # 枠線
                            current_page.draw_rect(
                                keyboard_dest,
                                color=(0.6, 0.8, 0.6),
                                width=0.5
                            )
                            
                        except Exception as e:
                            print(f"  Keyboard placement warning: {e}")
                        
                        current_y += 75
                        total_measure += 4
            
            # 最終ページのフッター
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
            
            # エラー表示を元に戻す
            fitz.TOOLS.mupdf_display_errors(True)
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None