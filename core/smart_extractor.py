import fitz
import cv2
import numpy as np
from PIL import Image
import io

class SmartExtractor:
    """スマートな楽譜抽出 - 楽譜の構造を自動認識"""
    
    def __init__(self):
        self.standard_layouts = {
            'band_score': {
                'instruments': [
                    {'name': 'Vocal', 'y_ratio': 0.12, 'height_ratio': 0.08},
                    {'name': 'Guitar1', 'y_ratio': 0.20, 'height_ratio': 0.08},
                    {'name': 'Guitar2', 'y_ratio': 0.28, 'height_ratio': 0.08},
                    {'name': 'Bass', 'y_ratio': 0.36, 'height_ratio': 0.08},
                    {'name': 'Keyboard', 'y_ratio': 0.44, 'height_ratio': 0.12},
                    {'name': 'Drums', 'y_ratio': 0.56, 'height_ratio': 0.12}
                ],
                'measures_per_line': 4,
                'systems_per_page': 2
            },
            'piano_vocal': {
                'instruments': [
                    {'name': 'Vocal', 'y_ratio': 0.15, 'height_ratio': 0.15},
                    {'name': 'Piano_R', 'y_ratio': 0.35, 'height_ratio': 0.15},
                    {'name': 'Piano_L', 'y_ratio': 0.50, 'height_ratio': 0.15}
                ],
                'measures_per_line': 4,
                'systems_per_page': 2
            }
        }
    
    def analyze_score_structure(self, pdf_path, sample_page=0):
        """楽譜の構造を分析"""
        try:
            pdf = fitz.open(pdf_path)
            if sample_page >= len(pdf):
                sample_page = 0
            
            page = pdf[sample_page]
            
            # 画像に変換
            mat = fitz.Matrix(2.0, 2.0)  # 2倍の解像度
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # OpenCVで処理
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 構造を分析
            structure = {
                'staff_lines': self._detect_staff_lines(gray),
                'measure_lines': self._detect_measure_lines(gray),
                'systems': self._detect_systems(gray),
                'text_regions': self._detect_text_regions(page)
            }
            
            pdf.close()
            return structure
            
        except Exception as e:
            print(f"構造分析エラー: {str(e)}")
            return None
    
    def _detect_staff_lines(self, gray_img):
        """五線譜を検出"""
        # 水平線を検出
        edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                                minLineLength=gray_img.shape[1]*0.5, maxLineGap=10)
        
        if lines is None:
            return []
        
        # 水平線をグループ化（五線譜として）
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 5:  # ほぼ水平
                horizontal_lines.append(y1)
        
        horizontal_lines.sort()
        
        # 五線譜をグループ化（5本の線が近接）
        staff_groups = []
        current_group = []
        
        for i, y in enumerate(horizontal_lines):
            if not current_group:
                current_group.append(y)
            elif y - current_group[-1] < 20:  # 線の間隔
                current_group.append(y)
                if len(current_group) == 5:
                    staff_groups.append({
                        'top': current_group[0],
                        'bottom': current_group[-1],
                        'center': sum(current_group) / len(current_group)
                    })
                    current_group = []
            else:
                current_group = [y]
        
        return staff_groups
    
    def _detect_measure_lines(self, gray_img):
        """小節線を検出"""
        # 垂直線を検出
        edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50,
                                minLineLength=gray_img.shape[0]*0.1, maxLineGap=20)
        
        if lines is None:
            return []
        
        vertical_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(x2 - x1) < 5:  # ほぼ垂直
                vertical_lines.append(x1)
        
        # 重複を除去して並び替え
        vertical_lines = sorted(list(set(vertical_lines)))
        
        # 等間隔の線を小節線として認識
        measure_lines = []
        if len(vertical_lines) > 2:
            # 間隔を計算
            intervals = [vertical_lines[i+1] - vertical_lines[i] 
                        for i in range(len(vertical_lines)-1)]
            avg_interval = sum(intervals) / len(intervals)
            
            # 平均間隔に近い線を選択
            for i, x in enumerate(vertical_lines):
                if i == 0 or i == len(vertical_lines) - 1:
                    measure_lines.append(x)
                else:
                    prev_interval = x - vertical_lines[i-1]
                    next_interval = vertical_lines[i+1] - x
                    if (abs(prev_interval - avg_interval) < avg_interval * 0.3 or 
                        abs(next_interval - avg_interval) < avg_interval * 0.3):
                        measure_lines.append(x)
        
        return measure_lines
    
    def _detect_systems(self, gray_img):
        """システム（段）を検出"""
        staff_lines = self._detect_staff_lines(gray_img)
        
        systems = []
        current_system = []
        
        for i, staff in enumerate(staff_lines):
            if not current_system:
                current_system.append(staff)
            else:
                # 前の五線譜との距離を確認
                distance = staff['top'] - current_system[-1]['bottom']
                if distance < 100:  # 同じシステム内
                    current_system.append(staff)
                else:  # 新しいシステム
                    systems.append({
                        'staffs': current_system,
                        'top': current_system[0]['top'],
                        'bottom': current_system[-1]['bottom']
                    })
                    current_system = [staff]
        
        if current_system:
            systems.append({
                'staffs': current_system,
                'top': current_system[0]['top'],
                'bottom': current_system[-1]['bottom']
            })
        
        return systems
    
    def _detect_text_regions(self, page):
        """テキスト領域を検出（楽器名など）"""
        text_blocks = page.get_text("dict")["blocks"]
        
        text_regions = []
        for block in text_blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text and len(text) < 20:  # 短いテキスト（楽器名の可能性）
                            bbox = span["bbox"]
                            if bbox[0] < 100:  # 左端
                                text_regions.append({
                                    'text': text,
                                    'bbox': bbox,
                                    'x': bbox[0],
                                    'y': (bbox[1] + bbox[3]) / 2
                                })
        
        return text_regions
    
    def extract_with_structure(self, pdf_path, structure, selected_parts=['vocal', 'keyboard']):
        """構造情報を使って抽出"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # A4サイズ
            page_width = 595
            page_height = 842
            margin = 40
            
            current_page = output_pdf.new_page(width=page_width, height=page_height)
            current_y = margin
            
            # タイトル
            current_page.insert_text(
                (margin, current_y),
                "Smart Extracted Parts",
                fontsize=16,
                color=(0, 0, 0)
            )
            current_y += 40
            
            # 各ページを処理
            for page_num in range(min(3, len(src_pdf))):
                page = src_pdf[page_num]
                page_rect = page.rect
                
                # このページの構造を取得または分析
                if page_num == 0:
                    page_structure = structure
                else:
                    page_structure = self.analyze_score_structure(pdf_path, page_num)
                
                if not page_structure or not page_structure['systems']:
                    # 構造が検出できない場合はデフォルト
                    self._extract_default(page, current_page, current_y, page_num, src_pdf)
                    continue
                
                # システムごとに処理
                for system in page_structure['systems']:
                    if current_y + 150 > page_height - margin:
                        current_page = output_pdf.new_page(width=page_width, height=page_height)
                        current_y = margin
                    
                    # 選択されたパートを抽出
                    for part in selected_parts:
                        # パートの位置を推定
                        part_rect = self._estimate_part_position(part, system, page_structure)
                        if part_rect:
                            dest_rect = fitz.Rect(
                                margin,
                                current_y,
                                page_width - margin,
                                current_y + 40
                            )
                            
                            current_page.show_pdf_page(
                                dest_rect, src_pdf, page_num, clip=part_rect
                            )
                            
                            current_y += 45
                    
                    current_y += 20
            
            # 保存
            output_path = pdf_path.replace('.pdf', '_smart_extracted.pdf')
            output_pdf.save(output_path)
            src_pdf.close()
            output_pdf.close()
            
            return output_path
            
        except Exception as e:
            print(f"抽出エラー: {str(e)}")
            return None
    
    def _estimate_part_position(self, part_name, system, structure):
        """パートの位置を推定"""
        # テキスト領域から楽器名を探す
        for text_region in structure['text_regions']:
            if part_name.lower() in text_region['text'].lower():
                # 対応する五線譜を探す
                y = text_region['y']
                for staff in system['staffs']:
                    if abs(staff['center'] - y) < 30:
                        return fitz.Rect(
                            0,
                            staff['top'] - 10,
                            1000,  # 幅は大きめに
                            staff['bottom'] + 10
                        )
        
        return None
    
    def _extract_default(self, page, current_page, current_y, page_num, src_pdf):
        """デフォルトの抽出方法"""
        page_rect = page.rect
        
        # 標準的なレイアウトを仮定
        parts = [
            {'name': 'Part1', 'y_ratio': 0.15, 'height_ratio': 0.15},
            {'name': 'Part2', 'y_ratio': 0.35, 'height_ratio': 0.15},
            {'name': 'Part3', 'y_ratio': 0.55, 'height_ratio': 0.15}
        ]
        
        for part in parts:
            clip_rect = fitz.Rect(
                0,
                page_rect.height * part['y_ratio'],
                page_rect.width,
                page_rect.height * (part['y_ratio'] + part['height_ratio'])
            )
            
            dest_rect = fitz.Rect(
                40,
                current_y,
                555,
                current_y + 40
            )
            
            current_page.show_pdf_page(
                dest_rect, src_pdf, page_num, clip=clip_rect
            )
            
            current_y += 45
        
        return current_y