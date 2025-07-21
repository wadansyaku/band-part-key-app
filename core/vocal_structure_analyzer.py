import fitz
import cv2
import numpy as np
import re

class VocalStructureAnalyzer:
    """ボーカルパートの構造（コード・メロディ・歌詞）を分析"""
    
    def __init__(self):
        # コード記号のパターン
        self.chord_patterns = [
            re.compile(r'^[A-G][#b]?(?:m|M|maj|min|dim|aug|sus)?(?:6|7|9|11|13)?(?:add|b|#)?(?:9|11|13)?(?:/[A-G][#b]?)?$'),
            re.compile(r'^[A-G][#b]?(?:m7|M7|maj7|min7|7sus4|6/9|add9)?$'),
            re.compile(r'^[IVX]+(?:m|M|7)?$'),  # ローマ数字コード
        ]
        
        # 歌詞の特徴（日本語・英語）
        self.lyrics_patterns = [
            re.compile(r'[ぁ-んァ-ヶー一-龠]+'),  # 日本語
            re.compile(r'^[a-z\s\'\-]+$', re.IGNORECASE),  # 英語の歌詞
        ]
        
        # ボーカルパートの典型的な高さ比率
        self.vocal_structure = {
            'chord_height_ratio': 0.15,    # コード行の高さ比率
            'staff_height_ratio': 0.50,    # 五線譜の高さ比率
            'lyrics_height_ratio': 0.35,   # 歌詞の高さ比率
        }
    
    def analyze_vocal_part(self, page, y_start, y_end):
        """指定範囲のボーカルパートを分析"""
        try:
            # テキストとグラフィック要素を取得
            text_blocks = self._get_text_in_range(page, y_start, y_end)
            graphic_elements = self._detect_staff_lines_in_range(page, y_start, y_end)
            
            # 構造を推定
            structure = {
                'chord_line': None,
                'staff_area': None,
                'lyrics_lines': [],
                'total_height': y_end - y_start,
                'components': []
            }
            
            # コード行を検出
            chord_y = self._find_chord_line(text_blocks, y_start, y_end)
            if chord_y:
                structure['chord_line'] = {
                    'y': chord_y,
                    'height': self._estimate_text_height(chord_y, y_start, y_end)
                }
                structure['components'].append('chord')
            
            # 五線譜を検出
            staff_area = self._find_staff_area(graphic_elements, y_start, y_end)
            if staff_area:
                structure['staff_area'] = staff_area
                structure['components'].append('staff')
            
            # 歌詞を検出
            lyrics = self._find_lyrics_lines(text_blocks, y_start, y_end, staff_area)
            if lyrics:
                structure['lyrics_lines'] = lyrics
                structure['components'].append('lyrics')
            
            # 推定された構造を返す
            return structure
            
        except Exception as e:
            print(f"ボーカルパート分析エラー: {str(e)}")
            return None
    
    def _get_text_in_range(self, page, y_start, y_end):
        """指定Y座標範囲内のテキストを取得"""
        text_blocks = []
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line["spans"]:
                    bbox = span["bbox"]
                    # Y座標が範囲内
                    if bbox[1] >= y_start and bbox[3] <= y_end:
                        text_blocks.append({
                            'text': span["text"].strip(),
                            'bbox': bbox,
                            'y': (bbox[1] + bbox[3]) / 2,
                            'x': bbox[0],
                            'font_size': span.get('size', 10)
                        })
        
        return sorted(text_blocks, key=lambda x: x['y'])
    
    def _detect_staff_lines_in_range(self, page, y_start, y_end):
        """指定範囲内の五線譜を検出"""
        # ページを画像に変換
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # OpenCVで処理
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 指定範囲を切り出し
        height, width = img.shape[:2]
        y_start_px = int(y_start * 2)  # 2倍の解像度
        y_end_px = int(y_end * 2)
        
        if y_start_px < 0:
            y_start_px = 0
        if y_end_px > height:
            y_end_px = height
            
        roi = img[y_start_px:y_end_px, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # 水平線を検出
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, 
                               minLineLength=width*0.3, maxLineGap=10)
        
        if lines is None:
            return []
        
        # 水平線をグループ化
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 3:  # ほぼ水平
                actual_y = y_start + (y1 / 2)  # 実際のY座標に変換
                horizontal_lines.append(actual_y)
        
        return self._group_staff_lines(horizontal_lines)
    
    def _group_staff_lines(self, lines):
        """水平線を五線譜としてグループ化"""
        if not lines:
            return []
        
        lines = sorted(lines)
        staff_groups = []
        current_group = []
        
        for line in lines:
            if not current_group:
                current_group.append(line)
            elif line - current_group[-1] < 15:  # 五線の間隔
                current_group.append(line)
                if len(current_group) >= 5:  # 5本で1つの五線譜
                    staff_groups.append({
                        'lines': current_group[:5],
                        'top': current_group[0],
                        'bottom': current_group[4],
                        'center': sum(current_group[:5]) / 5
                    })
                    current_group = current_group[5:]
            else:
                if len(current_group) >= 5:
                    staff_groups.append({
                        'lines': current_group[:5],
                        'top': current_group[0],
                        'bottom': current_group[4],
                        'center': sum(current_group[:5]) / 5
                    })
                current_group = [line]
        
        return staff_groups
    
    def _find_chord_line(self, text_blocks, y_start, y_end):
        """コード行を検出"""
        for block in text_blocks:
            text = block['text']
            # 短いテキストでコードパターンにマッチ
            if len(text) < 10:
                for pattern in self.chord_patterns:
                    if pattern.match(text):
                        return block['y']
            
            # 複数のコードが並んでいる行
            words = text.split()
            chord_count = sum(1 for word in words 
                            if any(p.match(word) for p in self.chord_patterns))
            if chord_count >= 2:
                return block['y']
        
        return None
    
    def _find_staff_area(self, staff_groups, y_start, y_end):
        """五線譜エリアを特定"""
        if not staff_groups:
            return None
        
        # 最も完全な五線譜を選択
        best_staff = max(staff_groups, key=lambda s: len(s.get('lines', [])))
        
        return {
            'top': best_staff['top'] - 10,
            'bottom': best_staff['bottom'] + 10,
            'center': best_staff['center'],
            'lines': best_staff['lines']
        }
    
    def _find_lyrics_lines(self, text_blocks, y_start, y_end, staff_area):
        """歌詞行を検出"""
        lyrics_lines = []
        
        # 五線譜より下のテキストを探す
        staff_bottom = staff_area['bottom'] if staff_area else (y_start + (y_end - y_start) * 0.6)
        
        for block in text_blocks:
            if block['y'] > staff_bottom:
                text = block['text']
                # 歌詞パターンにマッチ
                if any(p.search(text) for p in self.lyrics_patterns):
                    lyrics_lines.append({
                        'text': text,
                        'y': block['y'],
                        'x': block['x']
                    })
                # または長めのテキスト
                elif len(text) > 5 and not any(p.match(text) for p in self.chord_patterns):
                    lyrics_lines.append({
                        'text': text,
                        'y': block['y'],
                        'x': block['x']
                    })
        
        return lyrics_lines
    
    def _estimate_text_height(self, text_y, y_start, y_end):
        """テキストの高さを推定"""
        total_height = y_end - y_start
        # テキストの標準的な高さ
        return min(total_height * 0.1, 20)
    
    def calculate_optimal_extraction_area(self, structure):
        """最適な抽出エリアを計算"""
        if not structure or not structure['components']:
            return None
        
        # 各コンポーネントの境界を取得
        min_y = float('inf')
        max_y = float('-inf')
        
        if structure['chord_line']:
            chord_y = structure['chord_line']['y']
            min_y = min(min_y, chord_y - 5)
        
        if structure['staff_area']:
            min_y = min(min_y, structure['staff_area']['top'])
            max_y = max(max_y, structure['staff_area']['bottom'])
        
        if structure['lyrics_lines']:
            last_lyrics = max(structure['lyrics_lines'], key=lambda l: l['y'])
            max_y = max(max_y, last_lyrics['y'] + 15)
        
        # 余白を追加
        margin = 10
        return {
            'top': min_y - margin,
            'bottom': max_y + margin,
            'height': (max_y + margin) - (min_y - margin),
            'components': structure['components']
        }