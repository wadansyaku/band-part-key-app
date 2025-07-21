import fitz
import cv2
import numpy as np
from PIL import Image
import io
import pytesseract

class PreciseExtractor:
    """高精度パート抽出 - 各楽器の正確な垂直範囲を特定"""
    
    def __init__(self):
        # 抽出対象の楽器定義
        self.target_instruments = {
            'vocal': ['Vo.', 'Vocal', 'Vo', 'VOC', 'ボーカル', 'Vo.&Cho.', 'VOCAL', 'Voc'],
            'chord': ['Ch', 'Ch.', 'Chord', 'CHO', 'コード', 'CHORD'],
            'keyboard': ['Keyb.', 'Keyb', 'Key.', 'Key', 'Piano', 'Pf.', 'Pf', 'Synth', 
                        'Organ', 'キーボード', 'P.f.', 'KEYBOARD', 'PIANO', 'E.Piano', 
                        'E.P.', 'Pno', 'Kb']
        }
        
        # 除外する楽器（完全一致を優先）
        self.exclude_exact = ['Ba.', 'Bass', 'E.B.', 'E.Ba.', 'E.Ba', 'B.', 'Gt.', 'Gt', 'Dr.', 'Dr']
        self.exclude_partial = ['ベース', 'bass', 'Guitar', 'ギター', 'Drum', 'Drums', 'ドラム']
        
        # A4縦のサイズ
        self.page_width = 595
        self.page_height = 842
        self.margin = 40
        
    def extract_parts(self, pdf_path, selected_parts, pages_to_extract=None):
        """選択したパートのみを高精度で抽出"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            all_extractions = []
            
            for page_num in range(len(src_pdf)):
                if pages_to_extract and page_num not in pages_to_extract:
                    continue
                    
                page = src_pdf[page_num]
                print(f"\nページ {page_num + 1} を処理中...")
                
                # このページから楽器パートを抽出
                page_extractions = self._extract_from_page(
                    page, page_num, selected_parts
                )
                
                for extraction in page_extractions:
                    extraction['src_pdf'] = src_pdf
                    all_extractions.append(extraction)
            
            # A4縦に配置
            if all_extractions:
                self._create_output_pdf(output_pdf, all_extractions)
            
            # 保存
            output_path = pdf_path.replace('.pdf', '_precise.pdf')
            output_pdf.save(output_path)
            
            src_pdf.close()
            output_pdf.close()
            
            print(f"\n抽出完了: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_from_page(self, page, page_num, selected_parts):
        """ページから選択されたパートのみを抽出"""
        # 楽器ラベルを検出
        instrument_labels = self._find_instrument_labels(page)
        
        # 各楽器の垂直範囲を計算
        instrument_ranges = self._calculate_instrument_ranges(instrument_labels)
        
        # システムにグループ化
        systems = self._group_into_systems(instrument_ranges)
        
        extractions = []
        
        for sys_idx, system in enumerate(systems):
            print(f"  システム {sys_idx + 1}:")
            
            # 選択されたパートのみフィルタリング
            selected_in_system = []
            
            for inst in system:
                # 除外チェック
                if self._should_exclude(inst['label']):
                    print(f"    除外: {inst['label']}")
                    continue
                
                # 選択されたパートかチェック
                part_type = self._identify_part_type(inst['label'], selected_parts)
                if part_type:
                    inst['type'] = part_type
                    selected_in_system.append(inst)
                    print(f"    {part_type}: {inst['label']} (Y: {inst['y_min']:.1f} - {inst['y_max']:.1f})")
            
            if selected_in_system:
                # システムの水平範囲を検出
                h_bounds = self._detect_horizontal_bounds(page, system)
                
                extractions.append({
                    'page_num': page_num,
                    'system_idx': sys_idx,
                    'instruments': selected_in_system,
                    'h_bounds': h_bounds
                })
        
        return extractions
    
    def _find_instrument_labels(self, page):
        """楽器ラベルを検出（OCR対応）"""
        labels = []
        
        blocks = page.get_text("dict")
        has_text = False
        
        for block in blocks.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            has_text = True
                        bbox = span.get("bbox")
                        
                        # 左端のテキスト（楽器ラベル候補）
                        if bbox[0] < 100 and text and len(text) < 20:
                            # 楽器っぽいキーワードをチェック
                            instrument_keywords = ['Vo', 'Gt', 'Ba', 'Dr', 'Key', 'Pf', 'Piano', 'Synth', 'Ch']
                            if any(kw in text for kw in instrument_keywords):
                                labels.append({
                                    'label': text,
                                    'x': bbox[0],
                                    'y': bbox[1],
                                    'bbox': bbox
                                })
        
        # テキストがない場合はOCRを試行
        if not has_text or len(labels) == 0:
            print(f"    OCRを実行中...")
            ocr_labels = self._ocr_extract_labels(page)
            labels.extend(ocr_labels)
        
        return labels
    
    def _calculate_instrument_ranges(self, labels):
        """各楽器の垂直範囲を計算"""
        if not labels:
            return []
        
        # Y座標でソート
        sorted_labels = sorted(labels, key=lambda x: x['y'])
        
        ranges = []
        for i, label in enumerate(sorted_labels):
            # 次の楽器までの距離を基に範囲を決定
            if i < len(sorted_labels) - 1:
                next_y = sorted_labels[i + 1]['y']
                # 楽器間の中点を境界とする
                y_max = label['y'] + (next_y - label['y']) * 0.85  # 少し余裕を持たせる
            else:
                # 最後の楽器は前の間隔を参考に
                if i > 0:
                    prev_gap = label['y'] - sorted_labels[i - 1]['y']
                    y_max = label['y'] + prev_gap * 0.85
                else:
                    y_max = label['y'] + 60  # デフォルト
            
            ranges.append({
                'label': label['label'],
                'x': label['x'],
                'y': label['y'],
                'y_min': label['y'] - 10,  # ラベルの少し上から
                'y_max': y_max
            })
        
        return ranges
    
    def _group_into_systems(self, ranges):
        """楽器をシステムにグループ化"""
        if not ranges:
            return []
        
        systems = []
        current_system = [ranges[0]]
        
        for inst in ranges[1:]:
            # 大きなギャップがあれば新しいシステム
            if inst['y'] - current_system[-1]['y'] > 200:
                systems.append(current_system)
                current_system = [inst]
            else:
                current_system.append(inst)
        
        if current_system:
            systems.append(current_system)
        
        return systems
    
    def _should_exclude(self, label):
        """除外すべき楽器かチェック"""
        label_clean = label.strip()
        
        # 完全一致チェック
        if label_clean in self.exclude_exact:
            return True
        
        # 部分一致チェック
        for exclude in self.exclude_partial:
            if exclude.lower() in label_clean.lower():
                return True
        
        # 特殊ケース: "Synth Bass"など
        if 'bass' in label_clean.lower():
            return True
        
        # Gt. I, Gt. IIなどのパターン
        if label_clean.startswith('Gt.'):
            return True
        
        return False
    
    def _identify_part_type(self, label, selected_parts):
        """楽器ラベルからパートタイプを識別"""
        label_clean = label.strip()
        
        for part_type in selected_parts:
            if part_type not in self.target_instruments:
                continue
            
            for keyword in self.target_instruments[part_type]:
                # 完全一致または部分一致
                if keyword == label_clean or keyword.lower() in label_clean.lower():
                    return part_type
        
        return None
    
    def _detect_horizontal_bounds(self, page, system):
        """システムの水平方向の境界を検出"""
        # デフォルトは楽器ラベルの右側から右端まで
        left_x = max(inst['x'] for inst in system) + 50  # ラベルの右側
        right_x = self.page_width - 20
        
        return {'left': left_x, 'right': right_x}
    
    def _create_output_pdf(self, output_pdf, extractions):
        """出力PDFを作成"""
        current_page = output_pdf.new_page(width=self.page_width, height=self.page_height)
        current_y = self.margin
        
        # タイトル
        current_page.insert_text(
            (self.margin, current_y),
            "Extracted Parts (Vocal / Chord / Keyboard)",
            fontsize=14,
            color=(0, 0, 0)
        )
        current_y += 30
        
        # 4小節ごとのグループを想定して配置
        for extraction in extractions:
            page_num = extraction['page_num']
            src_pdf = extraction['src_pdf']
            h_bounds = extraction['h_bounds']
            
            # このシステムの高さを計算
            system_height = sum(inst['y_max'] - inst['y_min'] for inst in extraction['instruments'])
            system_height += len(extraction['instruments']) * 5  # パート間のスペース
            
            # 新しいページが必要か
            if current_y + system_height > self.page_height - self.margin:
                current_page = output_pdf.new_page(
                    width=self.page_width,
                    height=self.page_height
                )
                current_y = self.margin
            
            # 各楽器を配置
            for inst in extraction['instruments']:
                # ソースの領域（楽器の垂直範囲のみ）
                clip_rect = fitz.Rect(
                    h_bounds['left'],
                    inst['y_min'],
                    h_bounds['right'],
                    inst['y_max']
                )
                
                # 配置先の高さを計算
                dest_height = inst['y_max'] - inst['y_min']
                
                # 配置先
                dest_rect = fitz.Rect(
                    self.margin + 30,  # ラベル用スペース
                    current_y,
                    self.page_width - self.margin,
                    current_y + dest_height
                )
                
                # パートを配置
                try:
                    current_page.show_pdf_page(
                        dest_rect, src_pdf, page_num, clip=clip_rect
                    )
                    
                    # ラベル
                    label_text = inst.get('type', '').upper()[:3]
                    current_page.insert_text(
                        (self.margin - 5, current_y + 15),
                        label_text,
                        fontsize=9,
                        color=(0, 0, 0)
                    )
                    
                    current_y += dest_height + 5
                    
                except Exception as e:
                    print(f"    配置エラー: {str(e)}")
            
            # システム間のスペース
            current_y += 15
    
    def _ocr_extract_labels(self, page):
        """ページからOCRで楽器ラベルを抽出"""
        labels = []
        
        try:
            # ページを画像として取得
            mat = fitz.Matrix(200/72.0, 200/72.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)
            
            # 左端領域のみ処理
            height, width = img_array.shape[:2]
            left_region = img_array[:, :int(width * 0.15)]
            
            # OCR実行
            ocr_data = pytesseract.image_to_data(
                left_region, 
                output_type=pytesseract.Output.DICT,
                lang='jpn+eng'
            )
            
            # 結果を解析
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                if text and ocr_data['conf'][i] > 30:
                    # 楽器キーワードチェック
                    instrument_keywords = ['Vo', 'Pf', 'Key', 'Ba', 'Dr', 'Gt', 'Piano', 'Keyboard']
                    if any(kw in text for kw in instrument_keywords):
                        # 座標を元の座標系に変換
                        x = ocr_data['left'][i] * 72/200
                        y = ocr_data['top'][i] * 72/200
                        height = ocr_data['height'][i] * 72/200
                        
                        labels.append({
                            'label': text,
                            'x': x,
                            'y': y,
                            'bbox': [x, y, x + 50, y + height]
                        })
                        print(f"      OCR検出: '{text}' at y={y:.1f}")
            
        except Exception as e:
            print(f"      OCRエラー: {str(e)}")
        
        return labels