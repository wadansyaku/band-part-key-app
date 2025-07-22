#!/usr/bin/env python3
"""
最終スマート抽出器 V9 - 適応型
- 楽器位置を動的に判定
- 様々な楽譜レイアウトに対応
- 視覚的パターンとテキスト認識の組み合わせ
"""

import fitz
import os
from datetime import datetime
import numpy as np
import cv2
import pytesseract
from PIL import Image
import io
import re

class FinalSmartExtractorV9Adaptive:
    """最終スマート抽出器 V9 - 適応型楽器検出"""
    
    def __init__(self):
        # 出力設定
        self.page_width = 595  # A4
        self.page_height = 842
        self.margin = 20
        
        # 楽器名パターン（複数言語対応）
        self.instrument_patterns = {
            'vocal': [
                r'Vocal', r'Vo\.?', r'Voice', r'Melody', r'Chorus', r'Cho\.?',
                r'Lead', r'Sing', r'ボーカル', r'ヴォーカル', r'メロディ', r'歌'
            ],
            'keyboard': [
                r'Keyboard', r'Key\.?', r'Keyb\.?', r'Piano', r'Pf\.?', r'Synth',
                r'Organ', r'キーボード', r'ピアノ', r'シンセ', r'鍵盤'
            ],
            'guitar': [
                r'Guitar', r'Gt\.?', r'Gtr\.?', r'ギター', r'G\.'
            ],
            'bass': [
                r'Bass', r'Ba\.?', r'Bs\.?', r'ベース', r'B\.'
            ],
            'drums': [
                r'Drums?', r'Dr\.?', r'Percussion', r'ドラム', r'D\.'
            ]
        }
    
    def detect_staff_lines(self, page, system_idx=0):
        """五線譜の位置を検出してグループ化"""
        
        try:
            # ページを画像に変換
            mat = fitz.Matrix(2, 2)  # 高解像度
            pix = page.get_pixmap(matrix=mat)
            
            # OpenCVで処理
            img_data = pix.samples
            img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
            else:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # システムの範囲を限定
            height = gray.shape[0]
            system_height = height // 2
            y_start = system_idx * system_height
            y_end = (system_idx + 1) * system_height
            system_gray = gray[y_start:y_end, :]
            
            # 水平線検出
            edges = cv2.Canny(system_gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=200, maxLineGap=10)
            
            if lines is None:
                return []
            
            # 水平線をY座標でグループ化
            horizontal_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(y2 - y1) < 3:  # ほぼ水平
                    actual_y = (y1 + y_start) / 2  # 元の座標に戻して半分（元のスケール）
                    horizontal_lines.append(actual_y)
            
            # 重複を除去してソート
            horizontal_lines = sorted(list(set(horizontal_lines)))
            
            # 五線譜をグループ化（5本の近い線）
            staff_groups = []
            i = 0
            while i < len(horizontal_lines):
                group = [horizontal_lines[i]]
                j = i + 1
                
                # 近い線をグループ化
                while j < len(horizontal_lines) and horizontal_lines[j] - group[-1] < 20:
                    if horizontal_lines[j] - group[-1] > 2:  # 近すぎる重複を除外
                        group.append(horizontal_lines[j])
                    j += 1
                
                # 3本以上で五線譜と判定
                if len(group) >= 3:
                    staff_groups.append({
                        'lines': group,
                        'y_start': group[0] - 10,
                        'y_end': group[-1] + 10,
                        'y_center': (group[0] + group[-1]) / 2,
                        'line_count': len(group)
                    })
                
                i = j if j > i + 1 else i + 1
            
            return staff_groups
            
        except Exception as e:
            print(f"    Staff detection error: {e}")
            return []
    
    def detect_instrument_labels(self, page, system_idx=0):
        """楽器ラベルをOCRで検出"""
        
        try:
            # ページを画像に変換
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # システムの範囲に限定
            width, height = img.size
            system_height = height // 2
            y_start = system_idx * system_height
            y_end = (system_idx + 1) * system_height
            
            # 左端の領域のみOCR（楽器名は通常左側）
            left_region = img.crop((0, y_start, width // 4, y_end))
            
            # OCR実行
            ocr_text = pytesseract.image_to_string(left_region, lang='eng+jpn')
            
            # 楽器名を検出
            found_instruments = {}
            lines = ocr_text.split('\n')
            
            for line_idx, line in enumerate(lines):
                line_text = line.strip()
                if not line_text:
                    continue
                
                # 各楽器パターンをチェック
                for inst_type, patterns in self.instrument_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, line_text, re.IGNORECASE):
                            # Y座標を推定
                            y_ratio = (line_idx / len(lines)) if lines else 0.5
                            y_pos = y_start + (y_ratio * system_height)
                            
                            if inst_type not in found_instruments:
                                found_instruments[inst_type] = []
                            
                            found_instruments[inst_type].append({
                                'text': line_text,
                                'y_pos': y_pos / 2,  # 元のスケールに戻す
                                'confidence': 0.8  # OCR信頼度（仮）
                            })
                            break
            
            return found_instruments
            
        except Exception as e:
            print(f"    OCR error: {e}")
            return {}
    
    def analyze_system_instruments(self, page, system_idx):
        """システム内の楽器を総合的に分析"""
        
        # 五線譜を検出
        staff_groups = self.detect_staff_lines(page, system_idx)
        
        # 楽器ラベルを検出
        instrument_labels = self.detect_instrument_labels(page, system_idx)
        
        # 五線譜と楽器ラベルを対応付け
        instruments = {
            'vocal': None,
            'keyboard': None,
            'guitar': [],
            'bass': None,
            'drums': None
        }
        
        # ラベルが見つかった場合は優先
        if instrument_labels:
            # ボーカルを探す
            if 'vocal' in instrument_labels and staff_groups:
                # 最も上の五線譜をボーカルとする
                instruments['vocal'] = {
                    'staff': staff_groups[0],
                    'label': instrument_labels['vocal'][0],
                    'confidence': 0.9
                }
            
            # キーボードを探す
            if 'keyboard' in instrument_labels and staff_groups:
                # ラベルに最も近い五線譜を探す
                kbd_label = instrument_labels['keyboard'][0]
                best_staff = None
                min_distance = float('inf')
                
                for staff in staff_groups:
                    distance = abs(staff['y_center'] - kbd_label['y_pos'])
                    if distance < min_distance:
                        min_distance = distance
                        best_staff = staff
                
                if best_staff:
                    instruments['keyboard'] = {
                        'staff': best_staff,
                        'label': kbd_label,
                        'confidence': 0.9
                    }
        
        # ラベルが見つからない場合は位置で推定
        if not instruments['vocal'] and staff_groups:
            # 最上部の五線譜をボーカルと仮定
            instruments['vocal'] = {
                'staff': staff_groups[0],
                'label': None,
                'confidence': 0.6
            }
        
        if not instruments['keyboard'] and len(staff_groups) >= 5:
            # 下から2番目の五線譜をキーボードと仮定（ドラムの上）
            instruments['keyboard'] = {
                'staff': staff_groups[-2],
                'label': None,
                'confidence': 0.6
            }
        
        return instruments, staff_groups
    
    def extract_smart_final(self, pdf_path):
        """
        V9適応型スマート抽出
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
                f"{base_name}_final_v9_adaptive_{timestamp}.pdf"
            )
            
            print(f"\n📋 Final Smart Extraction V9 Adaptive")
            print(f"  - Input: {os.path.basename(pdf_path)}")
            print(f"  - Mode: Adaptive instrument detection")
            print(f"  - Features: Dynamic positioning, OCR, visual analysis")
            
            # 現在の出力ページ
            current_page = output_pdf.new_page(
                width=self.page_width,
                height=self.page_height
            )
            current_y = self.margin
            output_page_count = 1
            
            # 通算小節番号
            total_measure = 1
            
            # 楽譜ページを探す（最初の数ページをチェック）
            start_page = None
            for i in range(min(5, len(src_pdf))):
                page = src_pdf[i]
                # 五線譜があるかチェック
                staff_groups = self.detect_staff_lines(page, 0)
                if len(staff_groups) >= 3:  # 3つ以上の五線譜があれば楽譜
                    start_page = i
                    print(f"  Score detected starting at page {i + 1}")
                    break
            
            if start_page is None:
                start_page = 1  # デフォルトは2ページ目
                print(f"  No clear score page found, starting from page {start_page + 1}")
            
            # 各ページを処理
            for page_num in range(start_page, min(len(src_pdf), start_page + 20)):
                page = src_pdf[page_num]
                page_rect = page.rect
                
                print(f"\n  Analyzing page {page_num + 1}...")
                
                # 各システムを処理
                systems_per_page = 2
                
                for sys_idx in range(systems_per_page):
                    # このシステムの楽器を分析
                    instruments, staff_groups = self.analyze_system_instruments(page, sys_idx)
                    
                    if not instruments['vocal'] and not instruments['keyboard']:
                        continue
                    
                    print(f"    System {sys_idx + 1}: Found {len(staff_groups)} staves")
                    if instruments['vocal']:
                        print(f"      Vocal detected (confidence: {instruments['vocal']['confidence']})")
                    if instruments['keyboard']:
                        print(f"      Keyboard detected (confidence: {instruments['keyboard']['confidence']})")
                    
                    # 新しいページが必要かチェック
                    if current_y + 230 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # システムの垂直範囲
                    system_y_start = page_rect.height * (sys_idx * 0.5)
                    system_height = page_rect.height * 0.5
                    
                    # 1. ボーカルパート
                    if instruments['vocal']:
                        try:
                            staff = instruments['vocal']['staff']
                            
                            # 歌詞を含むように少し拡張
                            vocal_y_start = staff['y_start'] - 5
                            vocal_y_end = staff['y_end'] + 20
                            
                            vocal_clip = fitz.Rect(
                                0,
                                vocal_y_start,
                                page_rect.width,
                                vocal_y_end
                            )
                            
                            vocal_dest = fitz.Rect(
                                self.margin,
                                current_y,
                                self.page_width - self.margin,
                                current_y + 120
                            )
                            
                            # 楽譜を配置
                            current_page.show_pdf_page(
                                vocal_dest, src_pdf, page_num, 
                                clip=vocal_clip,
                                keep_proportion=False
                            )
                            
                            # ラベル
                            current_page.draw_circle(
                                fitz.Point(10, current_y + 60),
                                7,
                                color=(0.2, 0.2, 0.8),
                                fill=(0.2, 0.2, 0.8)
                            )
                            current_page.insert_text(
                                (7, current_y + 63),
                                "V",
                                fontsize=10,
                                color=(1, 1, 1)
                            )
                            
                        except Exception as e:
                            print(f"      Vocal error: {e}")
                        
                        current_y += 125
                    
                    # 2. キーボードパート
                    if instruments['keyboard']:
                        try:
                            staff = instruments['keyboard']['staff']
                            
                            keyboard_y_start = staff['y_start']
                            keyboard_y_end = staff['y_end'] + 10
                            
                            keyboard_clip = fitz.Rect(
                                0,
                                keyboard_y_start,
                                page_rect.width,
                                keyboard_y_end
                            )
                            
                            keyboard_dest = fitz.Rect(
                                self.margin,
                                current_y,
                                self.page_width - self.margin,
                                current_y + 100
                            )
                            
                            # 楽譜を配置
                            current_page.show_pdf_page(
                                keyboard_dest, src_pdf, page_num, 
                                clip=keyboard_clip,
                                keep_proportion=False
                            )
                            
                            # ラベル
                            current_page.draw_circle(
                                fitz.Point(10, current_y + 50),
                                7,
                                color=(0, 0.6, 0),
                                fill=(0, 0.6, 0)
                            )
                            current_page.insert_text(
                                (7, current_y + 53),
                                "K",
                                fontsize=10,
                                color=(1, 1, 1)
                            )
                            
                        except Exception as e:
                            print(f"      Keyboard error: {e}")
                        
                        current_y += 110
                    
                    total_measure += 8
            
            # 保存
            output_pdf.save(output_path)
            print(f"\n✅ Extraction Complete!")
            print(f"  Output: {output_path}")
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