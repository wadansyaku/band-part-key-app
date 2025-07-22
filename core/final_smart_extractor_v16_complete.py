#!/usr/bin/env python3
"""
最終スマート楽譜抽出 V16 - 完全版
V15の楽器検出成功 + V9のコンテンツ転送実装

根本的修正：
1. V15で正確に検出した楽器領域
2. V9のshow_pdf_pageでコンテンツを実際に転送
3. プレースホルダーではなく実際の楽譜を出力
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
from typing import List, Tuple, Dict, Optional

class FinalSmartExtractorV16Complete:
    def __init__(self):
        self.page_width = 595  
        self.page_height = 842
        self.margin = 20
        
        # V15と同じ楽器パターン
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
        
        self.debug_mode = True
        
    def extract_smart_final(self, pdf_path: str) -> Optional[str]:
        """V16完全版抽出"""
        print("\n🌟 Final Smart Extraction V16 Complete")
        print("  - Input:", os.path.basename(pdf_path))
        print("  - Features: V15 Detection + V9 Content Transfer")
        print("  - Output: Actual sheet music (not placeholders)")
        
        try:
            # ソースPDFを開く
            src_pdf = fitz.open(pdf_path)
            
            # V15と同じスコア開始検出
            score_start_page = self.detect_score_start(src_pdf)
            print(f"Score detected starting at page {score_start_page + 1}")
            
            # 出力PDFを作成
            output_pdf = fitz.open()
            
            # 出力設定
            current_page = None
            current_y = self.margin
            output_page_count = 0
            total_systems = 0
            
            # 各ページを処理
            for page_num in range(score_start_page, min(score_start_page + 20, len(src_pdf))):
                print(f"\n  📄 Processing page {page_num + 1}...")
                
                # V15スタイルで楽器検出
                systems = self.extract_systems_with_detection(src_pdf[page_num], page_num)
                
                # V9スタイルでコンテンツ転送
                for system in systems:
                    # 新しいページが必要かチェック
                    if current_page is None or current_y + 250 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # システムを実際に転送
                    self.transfer_system_content(
                        current_page, src_pdf, system, current_y
                    )
                    
                    current_y += 130  # 次のシステム位置
                    total_systems += 1
                    
                    if self.debug_mode and total_systems % 5 == 0:
                        print(f"    ✅ Processed {total_systems} systems")
            
            # 保存
            output_path = self.save_output(output_pdf, pdf_path, total_systems)
            
            # クリーンアップ
            src_pdf.close()
            output_pdf.close()
            
            return output_path
            
        except Exception as e:
            print(f"❌ V16 Complete extraction error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def detect_score_start(self, pdf: fitz.Document) -> int:
        """スコア開始検出（V15と同じ）"""
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.samples
            
            if len(img_data) > 100000:
                return max(0, page_num)
        
        return max(0, min(1, len(pdf) - 1))
    
    def extract_systems_with_detection(self, page: fitz.Page, page_num: int) -> List[Dict]:
        """V15スタイルの楽器検出"""
        systems = []
        
        # 1ページを2システムに分割
        for system_idx in [0, 1]:
            # 五線譜検出（V15と同じ）
            staff_groups = self.detect_staff_lines_v15(page, system_idx)
            
            # 楽器ラベル検出（V15と同じ）
            instrument_labels = self.detect_instrument_labels_v15(page, system_idx)
            
            if self.debug_mode and system_idx == 0:
                print(f"    System {system_idx + 1}: {len(staff_groups)} staves, labels: {list(instrument_labels.keys())}")
            
            # 楽器分析
            instruments = self.analyze_system_instruments_v15(staff_groups, instrument_labels)
            
            # システム情報を保存
            if instruments['vocal'] or instruments['keyboard']:
                system_rect = self.calculate_system_rect(page, system_idx)
                
                systems.append({
                    'page_num': page_num,
                    'system_idx': system_idx,
                    'rect': system_rect,
                    'instruments': instruments,
                    'staff_groups': staff_groups
                })
        
        return systems
    
    def detect_staff_lines_v15(self, page: fitz.Page, system_idx: int) -> List[Dict]:
        """V15の五線譜検出（簡略版）"""
        try:
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.samples
            img_array = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
            else:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            height = gray.shape[0]
            system_height = height // 2
            y_start = system_idx * system_height
            y_end = (system_idx + 1) * system_height
            system_gray = gray[y_start:y_end, :]
            
            edges = cv2.Canny(system_gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=200, maxLineGap=10)
            
            if lines is None:
                return []
            
            horizontal_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(y2 - y1) < 3:
                    actual_y = (y1 + y_start) / 2
                    horizontal_lines.append(actual_y)
            
            horizontal_lines = sorted(list(set(horizontal_lines)))
            
            staff_groups = []
            i = 0
            while i < len(horizontal_lines):
                group = [horizontal_lines[i]]
                j = i + 1
                
                while j < len(horizontal_lines) and horizontal_lines[j] - group[-1] < 20:
                    if horizontal_lines[j] - group[-1] > 2:
                        group.append(horizontal_lines[j])
                    j += 1
                
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
            return []
    
    def detect_instrument_labels_v15(self, page: fitz.Page, system_idx: int) -> Dict:
        """V15の楽器ラベル検出（PIL + OCR）"""
        try:
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            width, height = img.size
            system_height = height // 2
            y_start = system_idx * system_height
            y_end = (system_idx + 1) * system_height
            
            left_region = img.crop((0, y_start, width // 4, y_end))
            
            ocr_text = pytesseract.image_to_string(left_region, lang='eng+jpn')
            
            found_instruments = {}
            lines = ocr_text.split('\n')
            
            for line_idx, line in enumerate(lines):
                line_text = line.strip()
                if not line_text:
                    continue
                
                for inst_type, patterns in self.instrument_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, line_text, re.IGNORECASE):
                            y_ratio = (line_idx / len(lines)) if lines else 0.5
                            y_pos = y_start + (y_ratio * system_height)
                            
                            if inst_type not in found_instruments:
                                found_instruments[inst_type] = []
                            
                            found_instruments[inst_type].append({
                                'text': line_text,
                                'y_pos': y_pos / 2,
                                'confidence': 0.8
                            })
                            break
            
            return found_instruments
            
        except Exception as e:
            return {}
    
    def analyze_system_instruments_v15(self, staff_groups: List[Dict], instrument_labels: Dict) -> Dict:
        """V15スタイルの楽器分析"""
        instruments = {
            'vocal': None,
            'keyboard': None
        }
        
        if instrument_labels:
            # ボーカル検出
            if 'vocal' in instrument_labels and staff_groups:
                vocal_info = instrument_labels['vocal'][0]
                best_staff = self.find_best_staff(vocal_info, staff_groups, 'top')
                
                if best_staff:
                    instruments['vocal'] = {
                        'staff': best_staff,
                        'label': vocal_info,
                        'confidence': vocal_info['confidence']
                    }
            
            # キーボード検出
            if 'keyboard' in instrument_labels and staff_groups:
                keyboard_info = instrument_labels['keyboard'][0]
                best_staff = self.find_best_staff(keyboard_info, staff_groups, 'middle')
                
                if best_staff:
                    instruments['keyboard'] = {
                        'staff': best_staff,
                        'label': keyboard_info,
                        'confidence': keyboard_info['confidence']
                    }
        
        return instruments
    
    def find_best_staff(self, label_info: Dict, staff_groups: List[Dict], prefer: str) -> Optional[Dict]:
        """最適なスタッフを検索"""
        if not staff_groups:
            return None
        
        if prefer == 'top':
            return min(staff_groups, key=lambda s: s['y_center'])
        elif prefer == 'middle':
            sorted_staffs = sorted(staff_groups, key=lambda s: s['y_center'])
            if len(sorted_staffs) >= 2:
                return sorted_staffs[1]
            return sorted_staffs[0]
        else:
            label_y = label_info['y_pos']
            return min(staff_groups, key=lambda s: abs(s['y_center'] - label_y))
    
    def calculate_system_rect(self, page: fitz.Page, system_idx: int) -> fitz.Rect:
        """システム矩形計算"""
        page_height = page.rect.height
        system_height = page_height / 2
        
        y_start = system_idx * system_height
        y_end = (system_idx + 1) * system_height
        
        return fitz.Rect(0, y_start, page.rect.width, y_end)
    
    def transfer_system_content(self, target_page: fitz.Page, src_pdf: fitz.Document, 
                               system: Dict, current_y: float):
        """V9スタイルの実際のコンテンツ転送"""
        
        page_num = system['page_num']
        instruments = system['instruments']
        
        # 1. ボーカルパート転送
        if instruments['vocal']:
            try:
                staff = instruments['vocal']['staff']
                
                # 歌詞を含むように拡張
                vocal_y_start = staff['y_start'] - 5
                vocal_y_end = staff['y_end'] + 25  # 歌詞スペース
                
                # ソース領域
                vocal_clip = fitz.Rect(
                    0,
                    vocal_y_start,
                    src_pdf[page_num].rect.width,
                    vocal_y_end
                )
                
                # ターゲット領域
                vocal_dest = fitz.Rect(
                    self.margin,
                    current_y,
                    self.page_width - self.margin,
                    current_y + 60
                )
                
                # V9の核心：実際の楽譜転送！
                target_page.show_pdf_page(
                    vocal_dest, 
                    src_pdf, 
                    page_num, 
                    clip=vocal_clip,
                    keep_proportion=False
                )
                
                # ラベル追加
                target_page.draw_circle(
                    fitz.Point(10, current_y + 30),
                    7,
                    color=(0.2, 0.2, 0.8),
                    fill=(0.2, 0.2, 0.8)
                )
                target_page.insert_text(
                    (7, current_y + 33),
                    "V",
                    fontsize=10,
                    color=(1, 1, 1)
                )
                
                if self.debug_mode:
                    print(f"      ✅ Vocal transferred")
                
            except Exception as e:
                print(f"      ❌ Vocal transfer error: {e}")
        
        # 2. キーボードパート転送
        if instruments['keyboard']:
            try:
                staff = instruments['keyboard']['staff']
                
                keyboard_y_start = staff['y_start']
                keyboard_y_end = staff['y_end'] + 10
                
                # ボーカルがある場合は下に配置
                keyboard_y_offset = 65 if instruments['vocal'] else 0
                
                # ソース領域
                keyboard_clip = fitz.Rect(
                    0,
                    keyboard_y_start,
                    src_pdf[page_num].rect.width,
                    keyboard_y_end
                )
                
                # ターゲット領域
                keyboard_dest = fitz.Rect(
                    self.margin,
                    current_y + keyboard_y_offset,
                    self.page_width - self.margin,
                    current_y + keyboard_y_offset + 60
                )
                
                # 実際の楽譜転送！
                target_page.show_pdf_page(
                    keyboard_dest,
                    src_pdf,
                    page_num,
                    clip=keyboard_clip,
                    keep_proportion=False
                )
                
                # ラベル追加
                target_page.draw_circle(
                    fitz.Point(10, current_y + keyboard_y_offset + 30),
                    7,
                    color=(0, 0.6, 0),
                    fill=(0, 0.6, 0)
                )
                target_page.insert_text(
                    (7, current_y + keyboard_y_offset + 33),
                    "K",
                    fontsize=10,
                    color=(1, 1, 1)
                )
                
                if self.debug_mode:
                    print(f"      ✅ Keyboard transferred")
                
            except Exception as e:
                print(f"      ❌ Keyboard transfer error: {e}")
    
    def save_output(self, output_pdf: fitz.Document, original_path: str, total_systems: int) -> str:
        """出力PDFを保存"""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "/Users/Yodai/band_part_key_app/outputs/extracted_scores"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{base_name}_final_v16_complete_{timestamp}.pdf")
        
        output_pdf.save(output_path)
        
        print(f"\n✅ V16 Complete Extraction Success!")
        print(f"  Output: {output_path}")
        print(f"  Pages: {len(output_pdf)}")
        print(f"  Systems: {total_systems}")
        print(f"  Content: ACTUAL SHEET MUSIC (not placeholders)")
        
        return output_path

if __name__ == "__main__":
    extractor = FinalSmartExtractorV16Complete()
    
    test_file = "/Users/Yodai/Downloads/だから僕は音楽を辞めた.pdf"
    if os.path.exists(test_file):
        print("🧪 V16 COMPLETE EXTRACTOR TEST")
        print("="*60)
        result = extractor.extract_smart_final(test_file)
        if result:
            print(f"\n✅ Test completed: {result}")
        else:
            print("\n❌ Test failed")
    else:
        print("❌ Test file not found")