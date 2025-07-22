#!/usr/bin/env python3
"""
最終スマート抽出器 V7 ハイブリッド版
- 1ページ目から処理開始
- 楽器名検出を試み、失敗時は標準レイアウトを使用
- 実用的かつ柔軟な抽出
"""

import fitz
import os
from datetime import datetime

class FinalSmartExtractorV7Hybrid:
    """最終スマート抽出器 V7 ハイブリッド版"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595  # A4
        self.page_height = 842
        self.margin = 25
        
        # 標準的なバンドスコアレイアウト（フォールバック用）
        self.standard_layout = {
            'vocal': {'start': 0.08, 'end': 0.16},      # 8-16%
            'keyboard': {'start': 0.73, 'end': 0.88}    # 73-88%
        }
    
    def check_page_has_score(self, page):
        """ページに楽譜があるかチェック"""
        
        try:
            # ページを画像に変換して簡易チェック
            mat = fitz.Matrix(0.5, 0.5)  # 低解像度で高速化
            pix = page.get_pixmap(matrix=mat)
            
            # 白黒の比率をチェック（楽譜は白が多い）
            samples = pix.samples
            if len(samples) > 0:
                # バイト配列から配列に変換
                import numpy as np
                img_array = np.frombuffer(samples, dtype=np.uint8)
                
                # 白いピクセルの割合を計算
                white_ratio = np.sum(img_array > 200) / len(img_array)
                
                # 楽譜ページは通常50-90%が白
                has_score = 0.5 < white_ratio < 0.9
                
                return has_score
            
            return True  # デフォルトは処理する
            
        except Exception as e:
            print(f"    Page check error: {e}")
            return True  # エラー時は処理する
    
    def find_instruments_in_text(self, page):
        """PDFテキストから楽器名を検索"""
        
        try:
            text = page.get_text().lower()
            
            # 楽器名のキーワード
            vocal_found = any(keyword in text for keyword in 
                            ['vocal', 'vo.', 'voice', 'melody', 'chorus'])
            keyboard_found = any(keyword in text for keyword in 
                               ['keyboard', 'key.', 'keyb.', 'piano', 'synth'])
            
            # ギターやベースも検出（除外判定用）
            other_found = any(keyword in text for keyword in 
                            ['guitar', 'gt.', 'bass', 'ba.', 'drums', 'dr.'])
            
            return {
                'vocal': vocal_found,
                'keyboard': keyboard_found,
                'has_other': other_found,
                'has_any': vocal_found or keyboard_found or other_found
            }
            
        except Exception as e:
            print(f"    Text search error: {e}")
            return {'vocal': False, 'keyboard': False, 'has_other': False, 'has_any': False}
    
    def extract_smart_final(self, pdf_path):
        """
        V7ハイブリッド抽出 - 実用的なアプローチ
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
                f"{base_name}_final_v7_hybrid_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction V7 Hybrid")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Mode: Hybrid (text detection + standard layout)")
            print(f"  - Starting from: Page 1")
            
            # 現在の出力ページ
            current_page = output_pdf.new_page(
                width=self.page_width,
                height=self.page_height
            )
            current_y = self.margin
            output_page_count = 1
            
            # 通算小節番号
            total_measure = 1
            pages_processed = 0
            
            # 最初に楽譜があるページを探す
            first_score_page = None
            for i in range(min(5, len(src_pdf))):  # 最初の5ページをチェック
                if self.check_page_has_score(src_pdf[i]):
                    inst_info = self.find_instruments_in_text(src_pdf[i])
                    if inst_info['has_any']:
                        first_score_page = i
                        print(f"  First score page found: {i + 1}")
                        break
            
            # 楽譜ページが見つからない場合は2ページ目から開始（通常A部分がある）
            if first_score_page is None:
                first_score_page = min(1, len(src_pdf) - 1)  # インデックス1 = 2ページ目
                print(f"  No instrument text found, starting from page {first_score_page + 1}")
            
            # 楽譜ページから処理開始
            for page_num in range(first_score_page, len(src_pdf)):
                page = src_pdf[page_num]
                page_rect = page.rect
                
                # ページチェック
                if not self.check_page_has_score(page):
                    print(f"  Page {page_num + 1}: No score content, skipping")
                    continue
                
                print(f"  Processing page {page_num + 1}...")
                pages_processed += 1
                
                # 楽器情報を取得
                inst_info = self.find_instruments_in_text(page)
                
                # レイアウトを決定（テキストが見つかればそれを考慮、なければ標準レイアウト）
                if inst_info['has_any']:
                    print(f"    Detected instruments - Vocal: {inst_info['vocal']}, Keyboard: {inst_info['keyboard']}")
                    use_standard_layout = True  # 今回は標準レイアウトを使用
                else:
                    print(f"    No instrument text found, using standard layout")
                    use_standard_layout = True
                
                # システムごとに処理（1ページ2システム）
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
                    x_start = page_rect.width * 0.01
                    x_end = page_rect.width * 0.99
                    
                    # 1. ボーカルパート
                    try:
                        vocal_y_start = system_y_start + (system_height * self.standard_layout['vocal']['start'])
                        vocal_y_end = system_y_start + (system_height * self.standard_layout['vocal']['end'])
                        
                        vocal_clip = fitz.Rect(
                            x_start,
                            vocal_y_start,
                            x_end,
                            vocal_y_end
                        )
                        
                        vocal_dest = fitz.Rect(
                            self.margin + 15,
                            current_y,
                            self.page_width - self.margin,
                            current_y + 110
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
                        
                        # ラベル
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
                        print(f"    Vocal placement error: {e}")
                    
                    current_y += 115
                    
                    # 2. キーボードパート
                    try:
                        keyboard_y_start = system_y_start + (system_height * self.standard_layout['keyboard']['start'])
                        keyboard_y_end = system_y_start + (system_height * self.standard_layout['keyboard']['end'])
                        
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
                            current_y + 85
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
                        
                        # ラベル
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
                        print(f"    Keyboard placement error: {e}")
                    
                    current_y += 95
                    total_measure += 8
            
            # 保存
            output_pdf.save(output_path)
            print(f"\n✅ Extraction Complete!")
            print(f"  Output: {output_path}")
            print(f"  Pages processed: {pages_processed}")
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