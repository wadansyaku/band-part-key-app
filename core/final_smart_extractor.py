#!/usr/bin/env python3
"""
最終的なスマート抽出器
シンプルで実用的な実装
- ボーカル: コード・メロディ・歌詞を一体化（上部40%）
- キーボード: 下部のキーボードパート
- 4小節固定
"""

import fitz
import os

class FinalSmartExtractor:
    """最終的なスマート抽出器"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595
        self.page_height = 842
        self.margin = 40
        
        # 標準的なバンドスコアのレイアウト
        # 通常、1ページに2システム
        self.systems_per_page = 2
        self.system_height_ratio = 0.45
        
        # ボーカルパート（コード・メロディ・歌詞一体）は上部40%
        self.vocal_height_ratio = 0.40
        # キーボードは下部30%
        self.keyboard_start_ratio = 0.70
        self.keyboard_height_ratio = 0.30
    
    def extract_smart_final(self, pdf_path):
        """
        最終的なスマート抽出
        - 4小節固定
        - ボーカル（コード・メロディ・歌詞一体）とキーボード
        """
        
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力パス（プロジェクト内のoutputsディレクトリに保存）
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # プロジェクトルートからの相対パス
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(project_root, "outputs", "extracted_scores")
            
            # ディレクトリが存在しない場合は作成
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(
                output_dir,
                f"{base_name}_final_smart_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Mode: 4 measures fixed")
            print(f"  - Vocal: Chord/Melody/Lyrics integrated")
            print(f"  - Output: Including keyboard part")
            
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
                f"{base_name}",
                fontsize=16,
                color=(0, 0, 0)
            )
            current_y += 30
            
            # 通算小節番号
            total_measure = 1
            
            # 各ページを処理
            for page_num in range(min(len(src_pdf), 20)):  # 最大20ページ
                page = src_pdf[page_num]
                page_rect = page.rect
                
                # 各システムを処理
                for sys_idx in range(self.systems_per_page):
                    # システムの位置
                    system_y = page_rect.height * (sys_idx * 0.5)
                    system_height = page_rect.height * self.system_height_ratio
                    
                    # 1システムは通常8小節なので、4小節ずつ処理
                    for half in range(2):
                        # 新しいページが必要かチェック
                        if current_y + 160 > self.page_height - self.margin:
                            current_page = output_pdf.new_page(
                                width=self.page_width,
                                height=self.page_height
                            )
                            current_y = self.margin
                            output_page_count += 1
                        
                        # 小節の範囲（左半分または右半分）
                        x_start = page_rect.width * (half * 0.5)
                        x_end = page_rect.width * ((half + 0.5))
                        
                        # 小節番号（英語表記に変更）
                        current_page.insert_text(
                            (self.margin, current_y),
                            f"Measures {total_measure}-{total_measure + 3}",
                            fontsize=12,
                            color=(0.3, 0.3, 0.3)
                        )
                        current_y += 20
                        
                        # 1. ボーカルパート（コード・メロディ・歌詞一体）
                        vocal_y_start = system_y
                        vocal_y_end = system_y + (system_height * self.vocal_height_ratio)
                        
                        try:
                            vocal_clip = fitz.Rect(
                                x_start,
                                vocal_y_start,
                                x_end,
                                vocal_y_end
                            )
                            
                            vocal_dest = fitz.Rect(
                                self.margin + 40,
                                current_y,
                                self.page_width - self.margin,
                                current_y + 70  # 高さを大きく
                            )
                            
                            current_page.show_pdf_page(
                                vocal_dest, src_pdf, page_num, clip=vocal_clip
                            )
                            
                            # ラベルと枠
                            current_page.insert_text(
                                (self.margin, current_y + 35),
                                "Vo",
                                fontsize=11,
                                color=(0, 0, 0.8)
                            )
                            
                            # 薄い青の背景
                            bg_rect = fitz.Rect(
                                vocal_dest.x0 - 1,
                                vocal_dest.y0 - 1,
                                vocal_dest.x1 + 1,
                                vocal_dest.y1 + 1
                            )
                            current_page.draw_rect(
                                bg_rect,
                                color=(0.8, 0.8, 1.0),
                                fill=(0.95, 0.95, 1.0)
                            )
                            
                            # 再度楽譜を配置（背景の上に）
                            current_page.show_pdf_page(
                                vocal_dest, src_pdf, page_num, clip=vocal_clip
                            )
                            
                            # 枠線
                            current_page.draw_rect(
                                vocal_dest,
                                color=(0.6, 0.6, 0.8),
                                width=0.5
                            )
                            
                        except Exception as e:
                            print(f"  ボーカル配置エラー: {e}")
                        
                        current_y += 75
                        
                        # 2. キーボードパート
                        keyboard_y_start = system_y + (system_height * self.keyboard_start_ratio)
                        keyboard_y_end = system_y + system_height
                        
                        try:
                            keyboard_clip = fitz.Rect(
                                x_start,
                                keyboard_y_start,
                                x_end,
                                keyboard_y_end
                            )
                            
                            keyboard_dest = fitz.Rect(
                                self.margin + 40,
                                current_y,
                                self.page_width - self.margin,
                                current_y + 55
                            )
                            
                            current_page.show_pdf_page(
                                keyboard_dest, src_pdf, page_num, clip=keyboard_clip
                            )
                            
                            # ラベルと枠
                            current_page.insert_text(
                                (self.margin, current_y + 28),
                                "Key",
                                fontsize=11,
                                color=(0, 0.5, 0)
                            )
                            
                            # 薄い緑の背景
                            bg_rect = fitz.Rect(
                                keyboard_dest.x0 - 1,
                                keyboard_dest.y0 - 1,
                                keyboard_dest.x1 + 1,
                                keyboard_dest.y1 + 1
                            )
                            current_page.draw_rect(
                                bg_rect,
                                color=(0.8, 1.0, 0.8),
                                fill=(0.95, 1.0, 0.95)
                            )
                            
                            # 再度楽譜を配置
                            current_page.show_pdf_page(
                                keyboard_dest, src_pdf, page_num, clip=keyboard_clip
                            )
                            
                            # 枠線
                            current_page.draw_rect(
                                keyboard_dest,
                                color=(0.6, 0.8, 0.6),
                                width=0.5
                            )
                            
                        except Exception as e:
                            print(f"  キーボード配置エラー: {e}")
                        
                        current_y += 65  # 次の小節グループへ
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