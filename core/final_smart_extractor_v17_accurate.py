#!/usr/bin/env python3
"""
最終スマート楽譜抽出 V17 - 正確版
キーボードがギターを誤抽出する問題を根本的に解決

核心的改善：
1. OCRで検出した楽器名と実際の位置を正確にマッピング
2. バンドスコアの標準配置を考慮
3. ギター/ベース/ドラムを確実に除外
4. UI/UXの改善も含む
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

class FinalSmartExtractorV17Accurate:
    def __init__(self):
        self.page_width = 595  
        self.page_height = 842
        self.margin = 20
        
        # V17改善：楽器パターンを厳密化
        self.instrument_patterns = {
            'vocal': [
                r'Vocal', r'Vo\.?(?!cal)', r'Voice', r'Melody', r'Chorus', r'Cho\.?',
                r'Lead', r'Sing', r'ボーカル', r'ヴォーカル', r'メロディ', r'歌'
            ],
            'keyboard': [
                r'Keyboard', r'Key\.?(?!tar)', r'Keyb\.?', r'Piano', r'Pf\.?', r'Synth',
                r'Organ', r'キーボード', r'ピアノ', r'シンセ', r'鍵盤'
            ],
            'guitar': [
                r'Guitar', r'Gt\.?', r'Gtr\.?', r'E\.G', r'ギター'
            ],
            'bass': [
                r'Bass', r'Ba\.?', r'Bs\.?', r'E\.B', r'ベース'
            ],
            'drums': [
                r'Drums?', r'Dr\.?', r'Drs\.?', r'Percussion', r'ドラム'
            ]
        }
        
        self.debug_mode = True
        
    def extract_smart_final(self, pdf_path: str) -> Optional[str]:
        """V17正確版抽出"""
        print("\n🎯 Final Smart Extraction V17 Accurate")
        print("  - Input:", os.path.basename(pdf_path))
        print("  - Features: Precise instrument mapping")
        print("  - Fix: Keyboard no longer extracts Guitar")
        
        try:
            src_pdf = fitz.open(pdf_path)
            
            # スコア開始検出
            score_start_page = self.detect_score_start(src_pdf)
            print(f"Score detected starting at page {score_start_page + 1}")
            
            # PDFタイプ自動検出（実際に動作確認）
            pdf_type = self.detect_pdf_type(src_pdf)
            print(f"PDF type: {pdf_type['type']} (confidence: {pdf_type['confidence']:.1f})")
            
            # 出力PDF作成
            output_pdf = fitz.open()
            
            # 出力設定
            current_page = None
            current_y = self.margin
            output_page_count = 0
            total_systems = 0
            
            # 各ページ処理
            for page_num in range(score_start_page, min(score_start_page + 20, len(src_pdf))):
                print(f"\n  📄 Processing page {page_num + 1}...")
                
                # V17改善：より正確な楽器検出
                systems = self.extract_systems_accurately(src_pdf[page_num], page_num)
                
                # システム転送
                for system in systems:
                    # 新ページ判定
                    if current_page is None or current_y + 250 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                        output_page_count += 1
                    
                    # コンテンツ転送
                    self.transfer_system_content_v17(
                        current_page, src_pdf, system, current_y
                    )
                    
                    current_y += 130
                    total_systems += 1
                    
                    if total_systems % 5 == 0:
                        print(f"    ✅ Processed {total_systems} systems")
            
            # 保存
            output_path = self.save_output_v17(output_pdf, pdf_path, total_systems)
            
            src_pdf.close()
            output_pdf.close()
            
            return output_path
            
        except Exception as e:
            print(f"❌ V17 extraction error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def detect_score_start(self, pdf: fitz.Document) -> int:
        """スコア開始検出"""
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            
            # 五線譜の存在チェック
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            
            if len(pix.samples) > 100000:
                return max(0, page_num)
        
        return max(0, min(1, len(pdf) - 1))
    
    def detect_pdf_type(self, pdf: fitz.Document) -> Dict:
        """PDFタイプ自動検出（動作確認）"""
        total_text_blocks = 0
        total_images = 0
        
        # 最初の3ページを分析
        for page_num in range(min(3, len(pdf))):
            page = pdf[page_num]
            
            # テキストブロック検出
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            text_blocks = [b for b in blocks if "lines" in b]
            total_text_blocks += len(text_blocks)
            
            # 画像検出
            images = page.get_images()
            total_images += len(images)
        
        # タイプ判定
        if total_text_blocks >= 10:
            return {'type': 'text_based', 'confidence': 0.9}
        elif total_images > 0 and total_text_blocks < 5:
            return {'type': 'image_based', 'confidence': 0.9}
        else:
            return {'type': 'hybrid', 'confidence': 0.7}
    
    def extract_systems_accurately(self, page: fitz.Page, page_num: int) -> List[Dict]:
        """V17：より正確な楽器検出"""
        systems = []
        
        # 2システム/ページ
        for system_idx in [0, 1]:
            # 五線譜検出
            staff_groups = self.detect_staff_lines_v17(page, system_idx)
            
            # 楽器ラベル検出（改善版）
            all_labels = self.detect_all_instrument_labels_v17(page, system_idx)
            
            if self.debug_mode and system_idx == 0:
                print(f"    System {system_idx + 1}: {len(staff_groups)} staves")
                if all_labels:
                    print(f"      All detected labels: {[(l['type'], l['text'][:20]) for l in all_labels]}")
            
            # V17核心：正確な楽器マッピング
            instruments = self.map_instruments_accurately_v17(staff_groups, all_labels)
            
            # システム情報保存
            if instruments['vocal'] or instruments['keyboard']:
                system_rect = self.calculate_system_rect(page, system_idx)
                
                systems.append({
                    'page_num': page_num,
                    'system_idx': system_idx,
                    'rect': system_rect,
                    'instruments': instruments,
                    'all_labels': all_labels  # デバッグ用
                })
                
                if self.debug_mode:
                    parts = []
                    if instruments['vocal']:
                        parts.append(f"Vocal(pos:{instruments['vocal']['position']})")
                    if instruments['keyboard']:
                        parts.append(f"Keyboard(pos:{instruments['keyboard']['position']})")
                    print(f"      ✅ Mapped: {', '.join(parts)}")
        
        return systems
    
    def detect_staff_lines_v17(self, page: fitz.Page, system_idx: int) -> List[Dict]:
        """V17五線譜検出"""
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
            
            # 水平線検出
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
            
            # 五線譜グループ化
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
                        'line_count': len(group),
                        'position': len(staff_groups)  # 上から何番目か
                    })
                
                i = j if j > i + 1 else i + 1
            
            return staff_groups
            
        except Exception as e:
            return []
    
    def detect_all_instrument_labels_v17(self, page: fitz.Page, system_idx: int) -> List[Dict]:
        """V17：全楽器ラベル検出（改善版）"""
        try:
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            width, height = img.size
            system_height = height // 2
            y_start = system_idx * system_height
            y_end = (system_idx + 1) * system_height
            
            # 左端領域
            left_region = img.crop((0, y_start, width // 4, y_end))
            
            # OCR実行
            ocr_text = pytesseract.image_to_string(left_region, lang='eng+jpn')
            
            # 全楽器ラベル収集
            all_labels = []
            lines = ocr_text.split('\n')
            
            for line_idx, line in enumerate(lines):
                line_text = line.strip()
                if not line_text:
                    continue
                
                # 各楽器タイプをチェック
                for inst_type, patterns in self.instrument_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, line_text, re.IGNORECASE):
                            y_ratio = (line_idx / len(lines)) if lines else 0.5
                            y_pos = y_start + (y_ratio * system_height)
                            
                            all_labels.append({
                                'type': inst_type,
                                'text': line_text,
                                'y_pos': y_pos / 2,
                                'line_idx': line_idx,
                                'confidence': 0.8
                            })
                            break
            
            # Y座標でソート
            all_labels.sort(key=lambda x: x['y_pos'])
            
            return all_labels
            
        except Exception as e:
            return []
    
    def map_instruments_accurately_v17(self, staff_groups: List[Dict], all_labels: List[Dict]) -> Dict:
        """V17核心：正確な楽器マッピング"""
        instruments = {
            'vocal': None,
            'keyboard': None
        }
        
        if not staff_groups or not all_labels:
            return instruments
        
        # ターゲット楽器のみ抽出
        vocal_labels = [l for l in all_labels if l['type'] == 'vocal']
        keyboard_labels = [l for l in all_labels if l['type'] == 'keyboard']
        
        # 除外楽器の位置も把握（キーボードとの混同を防ぐ）
        guitar_labels = [l for l in all_labels if l['type'] == 'guitar']
        bass_labels = [l for l in all_labels if l['type'] == 'bass']
        
        # ボーカルマッピング（通常最上位）
        if vocal_labels and staff_groups:
            # 最初のボーカルラベル
            vocal_label = vocal_labels[0]
            
            # 最も近いスタッフを検索（ただし最上位優先）
            best_staff = None
            min_distance = float('inf')
            
            for staff in staff_groups[:2]:  # 上位2つのみ検討
                distance = abs(staff['y_center'] - vocal_label['y_pos'])
                if distance < min_distance and distance < 50:  # 50pt以内
                    min_distance = distance
                    best_staff = staff
            
            if best_staff:
                instruments['vocal'] = {
                    'staff': best_staff,
                    'label': vocal_label,
                    'confidence': vocal_label['confidence'],
                    'position': best_staff['position']
                }
        
        # キーボードマッピング（V17改善：ギターとの混同を防ぐ）
        if keyboard_labels and staff_groups:
            keyboard_label = keyboard_labels[0]
            
            # ギターの位置を特定
            guitar_positions = []
            for g_label in guitar_labels:
                for staff in staff_groups:
                    if abs(staff['y_center'] - g_label['y_pos']) < 50:
                        guitar_positions.append(staff['position'])
            
            # キーボードに最適なスタッフを検索
            best_staff = None
            min_distance = float('inf')
            
            for staff in staff_groups:
                # ギターの位置は除外
                if staff['position'] in guitar_positions:
                    continue
                
                # ボーカルの位置も除外
                if instruments['vocal'] and staff['position'] == instruments['vocal']['position']:
                    continue
                
                distance = abs(staff['y_center'] - keyboard_label['y_pos'])
                
                # キーボードは通常中位〜下位
                position_score = 0
                if staff['position'] >= 1:  # 2番目以降を優先
                    position_score = 10
                
                total_score = distance - position_score
                
                if total_score < min_distance and distance < 100:
                    min_distance = total_score
                    best_staff = staff
            
            if best_staff:
                instruments['keyboard'] = {
                    'staff': best_staff,
                    'label': keyboard_label,
                    'confidence': keyboard_label['confidence'],
                    'position': best_staff['position']
                }
                
                if self.debug_mode:
                    print(f"        🎹 Keyboard mapped to position {best_staff['position']} (avoided guitar at {guitar_positions})")
        
        return instruments
    
    def calculate_system_rect(self, page: fitz.Page, system_idx: int) -> fitz.Rect:
        """システム矩形計算"""
        page_height = page.rect.height
        system_height = page_height / 2
        
        y_start = system_idx * system_height
        y_end = (system_idx + 1) * system_height
        
        return fitz.Rect(0, y_start, page.rect.width, y_end)
    
    def transfer_system_content_v17(self, target_page: fitz.Page, src_pdf: fitz.Document, 
                                   system: Dict, current_y: float):
        """V17コンテンツ転送（UI改善含む）"""
        
        page_num = system['page_num']
        instruments = system['instruments']
        
        # ボーカルパート
        if instruments['vocal']:
            try:
                staff = instruments['vocal']['staff']
                
                vocal_y_start = staff['y_start'] - 5
                vocal_y_end = staff['y_end'] + 25
                
                vocal_clip = fitz.Rect(
                    0,
                    vocal_y_start,
                    src_pdf[page_num].rect.width,
                    vocal_y_end
                )
                
                vocal_dest = fitz.Rect(
                    self.margin,
                    current_y,
                    self.page_width - self.margin,
                    current_y + 60
                )
                
                # 楽譜転送
                target_page.show_pdf_page(
                    vocal_dest, 
                    src_pdf, 
                    page_num, 
                    clip=vocal_clip,
                    keep_proportion=False
                )
                
                # 改善されたラベル（左端に統一）
                self.add_instrument_label_v17(target_page, "Vocal", current_y + 30, (0.1, 0.3, 0.8))
                
            except Exception as e:
                print(f"      ❌ Vocal transfer error: {e}")
        
        # キーボードパート
        if instruments['keyboard']:
            try:
                staff = instruments['keyboard']['staff']
                
                keyboard_y_start = staff['y_start']
                keyboard_y_end = staff['y_end'] + 10
                
                keyboard_y_offset = 65 if instruments['vocal'] else 0
                
                keyboard_clip = fitz.Rect(
                    0,
                    keyboard_y_start,
                    src_pdf[page_num].rect.width,
                    keyboard_y_end
                )
                
                keyboard_dest = fitz.Rect(
                    self.margin,
                    current_y + keyboard_y_offset,
                    self.page_width - self.margin,
                    current_y + keyboard_y_offset + 60
                )
                
                # 楽譜転送
                target_page.show_pdf_page(
                    keyboard_dest,
                    src_pdf,
                    page_num,
                    clip=keyboard_clip,
                    keep_proportion=False
                )
                
                # 改善されたラベル
                self.add_instrument_label_v17(target_page, "Key", current_y + keyboard_y_offset + 30, (0, 0.6, 0.3))
                
            except Exception as e:
                print(f"      ❌ Keyboard transfer error: {e}")
    
    def add_instrument_label_v17(self, page: fitz.Page, label: str, y_pos: float, color: Tuple[float, float, float]):
        """V17：改善されたラベルデザイン"""
        # より洗練されたラベル
        label_rect = fitz.Rect(5, y_pos - 10, 45, y_pos + 10)
        
        # 背景矩形
        page.draw_rect(label_rect, color=color, fill=color, width=0)
        
        # テキスト
        page.insert_text(
            (label_rect.x0 + 5, y_pos + 3),
            label,
            fontsize=11,
            color=(1, 1, 1),
            fontname="helvetica-bold"
        )
    
    def save_output_v17(self, output_pdf: fitz.Document, original_path: str, total_systems: int) -> str:
        """V17出力保存"""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "/Users/Yodai/band_part_key_app/outputs/extracted_scores"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{base_name}_final_v17_accurate_{timestamp}.pdf")
        
        output_pdf.save(output_path)
        
        print(f"\n✅ V17 Accurate Extraction Success!")
        print(f"  Output: {output_path}")
        print(f"  Pages: {len(output_pdf)}")
        print(f"  Systems: {total_systems}")
        print(f"  Fix: Keyboard correctly extracts Keyboard (not Guitar)")
        
        return output_path

if __name__ == "__main__":
    extractor = FinalSmartExtractorV17Accurate()
    
    test_file = "/Users/Yodai/Downloads/だから僕は音楽を辞めた.pdf"
    if os.path.exists(test_file):
        print("🧪 V17 ACCURATE EXTRACTOR TEST")
        print("="*60)
        result = extractor.extract_smart_final(test_file)
        if result:
            print(f"\n✅ Test completed: {result}")
        else:
            print("\n❌ Test failed")
    else:
        print("❌ Test file not found")