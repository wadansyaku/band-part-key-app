import fitz
import cv2
import numpy as np
from PIL import Image
import io
import pytesseract

class MeasureBasedExtractor:
    """小節ベースの高精度抽出 - 8小節単位で整理"""
    
    def __init__(self):
        # 抽出対象の楽器定義
        self.target_instruments = {
            'vocal': ['Vo.', 'Vocal', 'Vo', 'VOC', 'ボーカル', 'Vo.&Cho.', 'VOCAL', 'Voc', 'V.', 'Vcl', 'Lead', 'Vora'],
            'chord': [],  # コードは実際のコード記号で検出する
            'keyboard': ['Keyb.', 'Keyb', 'Key.', 'Key', 'Piano', 'Pf.', 'Pf', 'Synth', 
                        'Organ', 'キーボード', 'P.f.', 'KEYBOARD', 'PIANO', 'E.Piano', 
                        'E.P.', 'Pno', 'Kb', 'Kbd.', 'Syn.', 'Syn', 'Keys', 'Pno.', 'Ep', 'Key.1', 'Key.2', 'Key.3']
        }
        
        # OCRで誤認識されやすいパターン
        self.ocr_corrections = {
            'Vora': 'Vocal',
            'Vocai': 'Vocal',
            'Ke/': 'Key',
            'Ke/.': 'Key.',
            'P/ano': 'Piano',
            'Synfh': 'Synth',
            'Key2': 'Key.2',
            'Key1': 'Key.1',
            'Key3': 'Key.3',
            'Keyl': 'Key.1',
            'Key2': 'Key.2',
            'Key3': 'Key.3'
        }
        
        # コード記号のパターン
        import re
        self.chord_pattern = re.compile(r'^[A-G][#b]?(?:m|M|maj|min|dim|aug|sus)?(?:6|7|9|11|13)?(?:add|b|#)?(?:9|11|13)?(?:/[A-G][#b]?)?$')
        
        # 簡易コードパターン（より幅広くマッチ）
        self.simple_chord_pattern = re.compile(r'^[A-G][#b]?')
        
        # 日本語コード名パターン
        self.jp_chord_pattern = re.compile(r'^[イロハニホヘト][#b]?')  # イロハニホヘト = CDEFGAB
        
        # 除外する楽器
        self.exclude_exact = ['Ba.', 'Bass', 'E.B.', 'E.Ba.', 'E.Ba', 'B.', 'Gt.', 'Gt', 'Dr.', 'Dr']
        self.exclude_partial = ['ベース', 'bass', 'Guitar', 'ギター', 'Drum', 'Drums', 'ドラム']
        
        # A4縦のサイズ
        self.page_width = 595
        self.page_height = 842
        self.margin = 40
        
        # パート高さの設定
        self.part_height_4measures = 45  # 4小節時
        self.part_height_8measures = 30  # 8小節時
        
        # 小節設定
        self.measures_per_line = 8  # 1行あたり8小節（デフォルト）
        self.measures_per_line_options = [4, 8]  # 利用可能なオプション
        
        # デフォルトの楽器レイアウト（フォールバック用）
        self.default_layouts = [
            {'type': 'vocal', 'y_ratio': 0.15, 'height_ratio': 0.10, 'label': 'Vocal'},
            {'type': 'chord', 'y_ratio': 0.25, 'height_ratio': 0.05, 'label': 'Chord'},
            {'type': 'keyboard', 'y_ratio': 0.30, 'height_ratio': 0.15, 'label': 'Keyboard'}
        ]
        
    def extract_parts(self, pdf_path, selected_parts, pages_to_extract=None, progress_callback=None, measures_per_line=None, show_lyrics=False):
        """選択したパートを小節単位で抽出"""
        try:
            # 小節数の設定
            if measures_per_line and measures_per_line in self.measures_per_line_options:
                self.measures_per_line = measures_per_line
            
            # 歌詞表示オプションを保存
            self.show_lyrics = show_lyrics
            
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            all_systems = []
            total_pages = len(src_pdf)
            processed_pages = 0
            
            # 高速モードフラグ（最初の3ページのみOCRを試行）
            use_fast_mode = total_pages > 3
            
            for page_num in range(total_pages):
                if pages_to_extract and page_num not in pages_to_extract:
                    continue
                    
                page = src_pdf[page_num]
                print(f"\nページ {page_num + 1}/{total_pages} を処理中...")
                
                # 進捗コールバック
                if progress_callback:
                    progress_callback(page_num + 1, total_pages)
                
                # 高速モードの判定
                if use_fast_mode and page_num >= 3:
                    # 3ページ目以降は高速処理
                    page_systems = self._extract_systems_fast(
                        page, page_num, selected_parts
                    )
                else:
                    # 最初の3ページは通常のOCR処理
                    page_systems = self._extract_systems_from_page(
                        page, page_num, selected_parts
                    )
                
                all_systems.extend(page_systems)
                processed_pages += 1
            
            # A4縦に配置
            if all_systems:
                self._create_output_pdf(output_pdf, all_systems, src_pdf)
            
            # 保存
            output_path = pdf_path.replace('.pdf', f'_measure_based_{self.measures_per_line}m.pdf')
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
    
    def _extract_systems_from_page(self, page, page_num, selected_parts):
        """ページからシステムを抽出"""
        # 楽器ラベルを検出
        instrument_labels = self._find_instrument_labels(page)
        
        # システムにグループ化
        systems = self._group_into_systems(instrument_labels)
        
        page_systems = []
        
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
                    print(f"    {part_type}: {inst['label']}")
            
            # システムに何も選択されていない場合、全て自動追加
            if len(selected_in_system) == 0 and system:
                base_y = system[0]['y']
                
                # ボーカルを追加
                if 'vocal' in selected_parts:
                    selected_in_system.append({
                        'type': 'vocal',
                        'label': 'Vocal (auto)',
                        'x': 10,
                        'y': base_y - 60,
                        'bbox': [10, base_y - 60, 60, base_y - 35],
                        'height': 25
                    })
                    print(f"    vocal: ボーカルラインを自動追加")
                
                # キーボードを追加
                if 'keyboard' in selected_parts:
                    selected_in_system.append({
                        'type': 'keyboard',
                        'label': 'Keyboard (auto)',
                        'x': 10,
                        'y': base_y,
                        'bbox': [10, base_y, 60, base_y + 25],
                        'height': 25
                    })
                    print(f"    keyboard: キーボードラインを自動追加")
            else:
                # ボーカルパートが選択されているが検出されていない場合、デフォルトで追加
                if 'vocal' in selected_parts and not any(inst['type'] == 'vocal' for inst in selected_in_system):
                    # システムの上部にボーカルラインがあると仮定
                    if system:
                        vocal_y = min(inst['y'] for inst in system) - 30
                        selected_in_system.append({
                            'type': 'vocal',
                            'label': 'Vocal (auto)',
                            'x': 10,
                            'y': vocal_y,
                            'bbox': [10, vocal_y, 60, vocal_y + 25],
                            'height': 25
                        })
                        print(f"    vocal: ボーカルラインを自動追加 at y={vocal_y:.1f}")
            
            # コードパートが選択されている場合、コード記号を検出
            if 'chord' in selected_parts:
                print("    コード記号の検出を実行...")
                try:
                    chord_lines = self._detect_chord_lines(page, system)
                    if chord_lines:
                        # 最も上にあるコードラインを選択（通常はボーカルの上）
                        chord_lines.sort(key=lambda x: x['y'])
                        best_chord_line = chord_lines[0]
                        
                        best_chord_line['type'] = 'chord'
                        best_chord_line['label'] = 'Chord Line'
                        selected_in_system.append(best_chord_line)
                        print(f"    chord: コードライン検出 at y={best_chord_line['y']:.1f}")
                    else:
                        # コードが検出されなかった場合、デフォルトで追加
                        if system:
                            chord_y = min(inst['y'] for inst in system) - 60
                            selected_in_system.append({
                                'type': 'chord',
                                'label': 'Chord (auto)',
                                'x': 10,
                                'y': chord_y,
                                'bbox': [10, chord_y, 60, chord_y + 20],
                                'height': 20
                            })
                            print(f"    chord: コードラインを自動追加 at y={chord_y:.1f}")
                except Exception as e:
                    print(f"    コード検出エラー: {str(e)}")
            
            if selected_in_system:
                # システムの小節を検出
                measures = self._detect_measures(page, system)
                
                page_systems.append({
                    'page_num': page_num,
                    'system_idx': sys_idx,
                    'instruments': selected_in_system,
                    'measures': measures,
                    'system_bounds': self._calculate_system_bounds(system),
                    'lyrics': self._extract_lyrics(page, system) if any(inst['type'] == 'vocal' for inst in selected_in_system) else None
                })
        
        return page_systems
    
    def _extract_systems_fast(self, page, page_num, selected_parts):
        """高速なシステム抽出（OCRを省略）"""
        systems = []
        page_rect = page.rect
        
        # デフォルトレイアウトを使用
        system_instruments = []
        for layout in self.default_layouts:
            if layout['type'] in selected_parts:
                system_instruments.append({
                    'type': layout['type'],
                    'label': layout['label'],
                    'y': page_rect.height * layout['y_ratio'],
                    'height': page_rect.height * layout['height_ratio']
                })
        
        if system_instruments:
            # ページの小節数を推定（通常8小節）
            measures_per_page = 8
            measure_width = page_rect.width / measures_per_page
            
            # 小節情報を生成
            measures = []
            for i in range(measures_per_page):
                measures.append({
                    'number': i + 1,
                    'x_start': i * measure_width,
                    'x_end': (i + 1) * measure_width,
                    'y_start': 0,
                    'y_end': page_rect.height,
                    'width': measure_width
                })
            
            # コード情報を簡易的に抽出
            chords = self._extract_chords_simple(page)
            
            systems.append({
                'page_num': page_num,
                'instruments': system_instruments,
                'measures': measures,
                'chords': chords,
                'has_all_selected': True
            })
        
        return systems
    
    def _extract_chords_simple(self, page):
        """簡易的なコード抽出"""
        chords = []
        text = page.get_text()
        
        # コードパターンにマッチする文字列を検索
        import re
        matches = self.chord_pattern.finditer(text)
        for match in matches:
            chords.append({
                'text': match.group(),
                'type': 'chord'
            })
        
        return chords[:20]  # 最初の20個まで
    
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
                        
                        # 左端のテキスト
                        if bbox[0] < 100 and text and len(text) < 20:
                            instrument_keywords = ['Vo', 'Gt', 'Ba', 'Dr', 'Key', 'Pf', 'Piano', 'Synth', 'Ch', 'Chord', 'コード']
                            # 除外パターンのチェック
                            exclude_patterns = ['Chime', 'Choice', 'Chorus', 'Echo', 'Pitch', 'Choir', 'Channel']
                            if not any(exc.lower() in text.lower() for exc in exclude_patterns):
                                if any(kw in text for kw in instrument_keywords):
                                    labels.append({
                                        'label': text,
                                        'x': bbox[0],
                                        'y': bbox[1],
                                        'bbox': bbox,
                                        'height': bbox[3] - bbox[1]
                                    })
        
        # テキストがない場合はOCR
        if not has_text or len(labels) == 0:
            print(f"    OCRを実行中...")
            ocr_labels = self._ocr_extract_labels(page)
            labels.extend(ocr_labels)
        
        # まだラベルが見つからない場合、デフォルトのラベルを追加
        if len(labels) == 0:
            print(f"    楽器ラベルが検出されなかったため、デフォルトを追加")
            # ページの中央付近にデフォルトのシステムを追加
            page_height = page.rect.height
            default_labels = [
                {
                    'label': 'System',
                    'x': 10,
                    'y': page_height * 0.3,
                    'bbox': [10, page_height * 0.3, 60, page_height * 0.3 + 25],
                    'height': 25
                },
                {
                    'label': 'System',
                    'x': 10,
                    'y': page_height * 0.6,
                    'bbox': [10, page_height * 0.6, 60, page_height * 0.6 + 25],
                    'height': 25
                }
            ]
            labels.extend(default_labels)
        
        return labels
    
    def _detect_measures(self, page, system):
        """システム内の小節を検出"""
        if not system:
            return []
        
        # システムの垂直範囲を取得
        min_y = min(inst['y'] for inst in system)
        max_y = max(inst['y'] + inst.get('height', 30) for inst in system)
        
        # ページを画像として取得
        mat = fitz.Matrix(200/72.0, 200/72.0)  # 高解像度
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        img = Image.open(io.BytesIO(img_data))
        img_array = np.array(img)
        
        # グレースケール変換
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # システム領域のみを処理
        y_start = int(min_y * 200/72)
        y_end = int(max_y * 200/72)
        system_img = gray[y_start:y_end, :]
        
        # システム全体の幅を取得
        width = system_img.shape[1]
        
        # 常にシステム全体を指定の小節数に分割
        # 楽器ラベルの右端からページの右端までを使用
        label_right_edge = 80  # 楽器ラベルの右端の推定位置（ピクセル）
        page_right_edge = width - 20  # 右端に少し余白
        effective_width = page_right_edge - label_right_edge
        
        # 実際の小節数を決定（通常、8小節がシステムに含まれる）
        actual_measures = 8  # デフォルトで8小節
        
        measure_bounds = []
        for i in range(actual_measures):
            x_start = label_right_edge + (effective_width * i / actual_measures)
            x_end = label_right_edge + (effective_width * (i + 1) / actual_measures)
            
            measure_bounds.append({
                'x_start': x_start * 72/200,
                'x_end': x_end * 72/200,
                'width': (x_end - x_start) * 72/200,
                'index': i + 1
            })
        
        # デバッグ情報
        print(f"    小節数: {len(measure_bounds)} 小節")
        
        return measure_bounds
    
    def _detect_vertical_lines(self, img, measures_per_line=8):
        """縦線（小節線）を検出"""
        # エッジ検出
        edges = cv2.Canny(img, 30, 100)  # 闾値を調整
        
        # 縦線を検出
        lines = cv2.HoughLinesP(edges, 1, np.pi/2, 
                               threshold=40,  # 闾値を下げてより多く検出
                               minLineLength=img.shape[0]*0.3,  # 最小長さを短く
                               maxLineGap=10)  # ギャップを大きく
        
        vertical_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # ほぼ垂直な線（許容度を少し大きく）
                if abs(x2 - x1) < 8:
                    vertical_lines.append(x1)
        
        # 近い線をマージ（同じ小節線が複数検出される場合への対処）
        merged_lines = []
        if vertical_lines:
            vertical_lines = sorted(vertical_lines)
            merged_lines = [vertical_lines[0]]
            for x in vertical_lines[1:]:
                if x - merged_lines[-1] > 20:  # 20ピクセル以上離れていれば別の線
                    merged_lines.append(x)
        
        vertical_lines = merged_lines
        
        # 楽器ラベルの右側から始まるように調整
        if vertical_lines and vertical_lines[0] < 80:
            # 最初の線が左端に近すぎる場合、適切な位置を追加
            vertical_lines = [80] + [x for x in vertical_lines if x > 80]
        elif not vertical_lines:
            # 線が見つからない場合はデフォルトを設定
            vertical_lines = [80]
        
        # 最後の線を追加（右端近く）
        if vertical_lines[-1] < img.shape[1] - 50:
            vertical_lines.append(img.shape[1] - 20)
        
        # デバッグ情報
        print(f"      検出された縦線: {len(vertical_lines)}本")
        
        return vertical_lines
    
    def _group_into_systems(self, labels):
        """楽器をシステムにグループ化"""
        if not labels:
            return []
        
        # Y座標でソート
        sorted_labels = sorted(labels, key=lambda x: x['y'])
        
        systems = []
        current_system = [sorted_labels[0]]
        
        for label in sorted_labels[1:]:
            # 大きなギャップがあれば新しいシステム
            if label['y'] - current_system[-1]['y'] > 200:
                systems.append(current_system)
                current_system = [label]
            else:
                current_system.append(label)
        
        if current_system:
            systems.append(current_system)
        
        return systems
    
    def _calculate_system_bounds(self, system):
        """システムの境界を計算"""
        if not system:
            return None
        
        min_y = min(inst['y'] for inst in system) - 10
        max_y = max(inst['y'] + inst.get('height', 30) for inst in system) + 10
        
        return {
            'top': min_y,
            'bottom': max_y,
            'height': max_y - min_y
        }
    
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
        
        # 特殊ケース
        if 'bass' in label_clean.lower():
            return True
        
        if label_clean.startswith('Gt.'):
            return True
        
        return False
    
    def _identify_part_type(self, label, selected_parts):
        """楽器ラベルからパートタイプを識別"""
        label_clean = label.strip()
        
        # 誤検出を防ぐための除外パターン（コードパート以外）
        if 'chord' not in selected_parts:
            exclude_patterns = ['Chime', 'Choice', 'Chorus', 'Echo', 'Pitch', 'Choir', 'Channel', 'Check']
            for pattern in exclude_patterns:
                if pattern.lower() in label_clean.lower():
                    return None
        
        for part_type in selected_parts:
            if part_type not in self.target_instruments:
                continue
            
            for keyword in self.target_instruments[part_type]:
                # 完全一致を優先
                if keyword == label_clean:
                    return part_type
                
                # コードパートの場合、特別な処理
                if part_type == 'chord':
                    # 完全一致または先頭一致をチェック
                    chord_exact_patterns = ['Ch', 'Ch.', 'CHO', 'CHO.', 'C.', 'Chord', 'Chords', 'コード']
                    for pattern in chord_exact_patterns:
                        if label_clean == pattern or label_clean.startswith(pattern + ' '):
                            return part_type
                        # ピリオドがないバージョンもチェック
                        if pattern.endswith('.') and label_clean == pattern[:-1]:
                            return part_type
                    # 部分一致もチェック
                    if keyword.lower() in label_clean.lower():
                        return part_type
                else:
                    # その他のパートは通常の部分一致
                    if keyword.lower() in label_clean.lower():
                        return part_type
        
        return None
    
    def _create_output_pdf(self, output_pdf, all_systems, src_pdf):
        """出力PDFを作成 - 指定された小節単位で配置"""
        current_page = output_pdf.new_page(width=self.page_width, height=self.page_height)
        current_y = self.margin
        
        # タイトル
        current_page.insert_text(
            (self.margin, current_y),
            f"Extracted Parts ({self.measures_per_line} measures per line)",
            fontsize=14,
            color=(0, 0, 0)
        )
        current_y += 30
        
        # グループ番号
        group_number = 1
        
        for system in all_systems:
            page_num = system['page_num']
            instruments = system['instruments']
            measures = system['measures']
            
            # 8小節モードの場合、4小節ずつに分割して横に並べる
            if self.measures_per_line == 8:
                # 小節を4小節ずつに分割
                measure_groups = self._group_measures(measures, 4)
                
                # 2つずつペアにして処理
                for i in range(0, len(measure_groups), 2):
                    group_pair = measure_groups[i:i+2]
                    self._render_measure_groups_8mode(current_page, current_y, group_pair, instruments, 
                                                     page_num, src_pdf, system)
                    
                    # 高さを計算
                    part_height = self.part_height_8measures
                    required_height = len(instruments) * part_height + 40
                    current_y += required_height + 20
                    
                    # 新しいページが必要か
                    if current_y + required_height > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
            else:
                # 4小節モード
                measure_groups = self._group_measures(measures, self.measures_per_line)
                
                for group_idx, group in enumerate(measure_groups):
                    # 必要な高さを計算
                    part_height = self.part_height_4measures if self.measures_per_line == 4 else self.part_height_8measures
                    required_height = len(instruments) * part_height + 40  # グループヘッダー分を追加
                    
                    # 新しいページが必要か
                    if current_y + required_height > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width,
                            height=self.page_height
                        )
                        current_y = self.margin
                    
                    # グループヘッダーを表示
                    group_rect = fitz.Rect(
                        self.margin - 10,
                        current_y - 5,
                        self.page_width - self.margin + 10,
                        current_y + required_height - 10
                    )
                    current_page.draw_rect(group_rect, color=(0.9, 0.9, 0.9), width=0.5)
                    
                    # グループラベルと小節範囲
                    # システム内の実際の小節番号を表示
                    actual_measure_count = len(group)
                    if group:
                        # 実際の小節番号をグループから取得
                        measure_start = group[0].get('index', group_idx * self.measures_per_line + 1)
                        measure_end = group[-1].get('index', measure_start + actual_measure_count - 1)
                    else:
                        measure_start = group_idx * self.measures_per_line + 1
                        measure_end = measure_start
                    
                    current_page.insert_text(
                        (self.margin, current_y),
                        f"Measures {measure_start}-{measure_end}",
                        fontsize=10,
                        color=(0.5, 0.5, 0.5)
                    )
                    current_y += 20
                    
                    # 各楽器を配置
                    for inst in instruments:
                        # 小節の範囲を計算
                        if group:
                            x_start = group[0]['x_start']
                            x_end = group[-1]['x_end']
                            
                            # ソース領域（最初の小節を含むように調整）
                            # ソース領域の調整
                            adjusted_x_start = x_start
                            if group_idx == 0 and x_start < 80:  # 最初のグループで左端に近い場合
                                adjusted_x_start = 60  # 楽器ラベルを避ける
                        
                        # 音符が切れないように、少し余裕を持たせる
                        clip_rect = fitz.Rect(
                            adjusted_x_start - 5,  # 左に少し余裕
                            inst['y'] - 10,  # 上に余裕
                            x_end + 10,  # 右に余裕（音符の尻切れ防止）
                            inst['y'] + inst.get('height', 30) + 10  # 下に余裕
                        )
                        
                        # 出力サイズを計算（拡大縮小してフィット）
                        dest_width = self.page_width - 2 * self.margin - 30
                        # 高さを固定し、幅に対してスケールを調整
                        dest_height = 30  # 固定高さ
                        
                        # ソース領域の高さ
                        source_height = inst.get('height', 30) + 20
                        
                        # 小節数に応じた高さを設定
                        dest_height = self.part_height_4measures if self.measures_per_line == 4 else self.part_height_8measures
                        
                        # 配置先
                        dest_rect = fitz.Rect(
                            self.margin + 30,
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
                            
                            # ボーカルパートの歌詞を表示（オプションが有効の場合）
                            if self.show_lyrics and inst.get('type') == 'vocal' and system.get('lyrics'):
                                # グループ内の歌詞のみを抽出
                                group_lyrics = self._filter_lyrics_for_group(system['lyrics'], group)
                                if group_lyrics:
                                    self._render_lyrics(current_page, group_lyrics, current_y, dest_rect, clip_rect)
                            
                            # コードパートの強調表示
                            if inst.get('type') == 'chord':
                                # コードラインの背景を明るい黄色に
                                chord_bg = fitz.Rect(
                                    dest_rect.x0 - 2,
                                    dest_rect.y0 - 2,
                                    dest_rect.x1 + 2,
                                    dest_rect.y1 + 2
                                )
                                current_page.draw_rect(chord_bg, color=(1, 1, 0.85), fill=(1, 1, 0.85))
                                
                                # コンテンツを再描画
                                current_page.show_pdf_page(
                                    dest_rect, src_pdf, page_num, clip=clip_rect
                                )
                                
                                # コード記号を目立たせるための太いフレーム
                                chord_frame = fitz.Rect(
                                    dest_rect.x0 - 1,
                                    dest_rect.y0 - 1,
                                    dest_rect.x1 + 1,
                                    dest_rect.y1 + 1
                                )
                                current_page.draw_rect(chord_frame, color=(0.8, 0.8, 0), width=2)
                                
                                # コードラベルを強調
                                label_bg = fitz.Rect(
                                    self.margin - 15,
                                    current_y - 2,
                                    self.margin + 25,
                                    current_y + 20
                                )
                                current_page.draw_rect(label_bg, color=(1, 0.9, 0), fill=(1, 0.9, 0))
                            
                            current_y += dest_height + 5
                            
                        except Exception as e:
                            print(f"    配置エラー: {str(e)}")
                    
                    # システム間のスペース
                    current_y += 15
                    group_number += 1
    
    def _group_measures(self, measures, group_size):
        """小節を指定サイズにグループ化"""
        groups = []
        for i in range(0, len(measures), group_size):
            group = measures[i:i + group_size]
            if group:
                groups.append(group)
        return groups
    
    def _render_lyrics(self, page, lyrics, y_position, dest_rect, clip_rect):
        """歌詞をレンダリング"""
        try:
            if not lyrics:
                return
            
            # 歌詞の表示位置を計算
            lyrics_y = y_position + 22  # ボーカルラインの下
            
            # 歌詞テキストを結合
            lyrics_text = ' '.join([lyric['text'] for lyric in lyrics])
            
            # 背景を薄い色で塗る
            lyrics_bg = fitz.Rect(
                dest_rect.x0,
                lyrics_y - 2,
                dest_rect.x1,
                lyrics_y + 10
            )
            page.draw_rect(lyrics_bg, color=(0.95, 0.95, 1), fill=(0.95, 0.95, 1))
            
            # 歌詞を表示
            page.insert_text(
                (dest_rect.x0 + 5, lyrics_y + 8),
                lyrics_text,
                fontsize=8,
                color=(0, 0, 0.5),
                fontname="Helvetica"
            )
            
        except Exception as e:
            print(f"      歌詞レンダリングエラー: {str(e)}")
    
    def _filter_lyrics_for_group(self, lyrics, group):
        """指定された小節グループに対応する歌詞をフィルタリング"""
        if not lyrics or not group:
            return None
        
        x_start = group[0]['x_start']
        x_end = group[-1]['x_end']
        
        filtered_lyrics = []
        for lyric in lyrics:
            # 歌詞のX座標がグループの範囲内にあるかチェック
            if x_start <= lyric['x'] <= x_end:
                filtered_lyrics.append(lyric)
        
        return filtered_lyrics if filtered_lyrics else None
    
    def _render_measure_groups_8mode(self, current_page, start_y, group_pair, instruments, page_num, src_pdf, system):
        """「8小節モード」で4小節×2を横に並べて表示"""
        # 横幅を半分に
        half_width = (self.page_width - 2 * self.margin - 20) / 2
        
        # グループ全体の背景
        part_height = self.part_height_8measures
        required_height = len(instruments) * part_height + 40
        
        group_rect = fitz.Rect(
            self.margin - 10,
            start_y - 5,
            self.page_width - self.margin + 10,
            start_y + required_height - 10
        )
        current_page.draw_rect(group_rect, color=(0.9, 0.9, 0.9), width=0.5)
        
        # 小節番号の表示
        if group_pair:
            first_group = group_pair[0]
            last_group = group_pair[-1] if len(group_pair) > 1 else first_group
            
            measure_start = first_group[0].get('index', 1) if first_group else 1
            measure_end = last_group[-1].get('index', 8) if last_group else 8
            
            current_page.insert_text(
                (self.margin, start_y),
                f"Measures {measure_start}-{measure_end}",
                fontsize=10,
                color=(0.5, 0.5, 0.5)
            )
        
        current_y = start_y + 20
        
        # 各パートを表示
        for inst in instruments:
            # ラベル
            label_text = inst.get('type', '').upper()[:3]
            current_page.insert_text(
                (self.margin - 5, current_y + 15),
                label_text,
                fontsize=9,
                color=(0, 0, 0)
            )
            
            # 左側の4小節
            if len(group_pair) > 0 and group_pair[0]:
                self._render_single_group(current_page, group_pair[0], inst, page_num, src_pdf,
                                        self.margin + 30, current_y, half_width - 15, part_height)
            
            # 右側の4小節
            if len(group_pair) > 1 and group_pair[1]:
                self._render_single_group(current_page, group_pair[1], inst, page_num, src_pdf,
                                        self.margin + 30 + half_width + 10, current_y, half_width - 15, part_height)
            
            current_y += part_height + 5
    
    def _render_single_group(self, current_page, group, inst, page_num, src_pdf, dest_x, dest_y, dest_width, dest_height):
        """単一の小節グループをレンダリング"""
        if not group:
            return
        
        x_start = group[0]['x_start']
        x_end = group[-1]['x_end']
        
        # 最初のグループの場合、楽器ラベルを避ける
        adjusted_x_start = x_start
        if group[0].get('index', 1) == 1 and x_start < 80:
            adjusted_x_start = 60
        
        # クリップ領域
        clip_rect = fitz.Rect(
            adjusted_x_start - 5,
            inst['y'] - 10,
            x_end + 10,
            inst['y'] + inst.get('height', 30) + 10
        )
        
        # 出力領域
        dest_rect = fitz.Rect(
            dest_x,
            dest_y,
            dest_x + dest_width,
            dest_y + dest_height
        )
        
        try:
            # コードパートの強調表示
            if inst.get('type') == 'chord':
                # 背景を明るい黄色に
                chord_bg = fitz.Rect(
                    dest_rect.x0 - 2,
                    dest_rect.y0 - 2,
                    dest_rect.x1 + 2,
                    dest_rect.y1 + 2
                )
                current_page.draw_rect(chord_bg, color=(1, 1, 0.85), fill=(1, 1, 0.85))
            
            current_page.show_pdf_page(
                dest_rect, src_pdf, page_num, clip=clip_rect
            )
            
            # コードパートのフレーム
            if inst.get('type') == 'chord':
                chord_frame = fitz.Rect(
                    dest_rect.x0 - 1,
                    dest_rect.y0 - 1,
                    dest_rect.x1 + 1,
                    dest_rect.y1 + 1
                )
                current_page.draw_rect(chord_frame, color=(0.8, 0.8, 0), width=2)
            
        except Exception as e:
            print(f"    配置エラー: {str(e)}")
    
    def _ocr_extract_labels(self, page):
        """ページからOCRで楽器ラベルを抽出"""
        labels = []
        
        try:
            # 高解像度でスキャン
            mat = fitz.Matrix(300/72.0, 300/72.0)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)
            
            # グレースケール変換
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # コントラスト強化
            gray = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
            
            # ノイズ除去
            gray = cv2.medianBlur(gray, 3)
            
            # 左端領域のみ処理
            height, width = gray.shape[:2]
            left_region = gray[:, :int(width * 0.15)]
            
            # OCR設定の最適化
            custom_config = r'--oem 3 --psm 11'
            
            # OCR実行
            ocr_data = pytesseract.image_to_data(
                left_region, 
                output_type=pytesseract.Output.DICT,
                config=custom_config,
                lang='eng'  # 英語のみで精度向上
            )
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                if text and ocr_data['conf'][i] > 20:  # 信頼度闾値を下げる
                    # OCR誤認識の修正
                    corrected_text = text
                    for wrong, correct in self.ocr_corrections.items():
                        if wrong.lower() in text.lower():
                            corrected_text = text.replace(wrong, correct)
                            break
                    # コードパートの特別チェック
                    chord_patterns = ['Ch', 'Ch.', 'CHO', 'CHO.', 'Chord', 'Chords', 'C.', 'コード']
                    is_chord = any(pattern == text or text.startswith(pattern + ' ') for pattern in chord_patterns)
                    
                    if is_chord:
                        x = ocr_data['left'][i] * 72/200
                        y = ocr_data['top'][i] * 72/200
                        height = ocr_data['height'][i] * 72/200
                        
                        labels.append({
                            'label': text,
                            'x': x,
                            'y': y,
                            'bbox': [x, y, x + 50, y + height],
                            'height': height
                        })
                        print(f"      OCR検出 (コード): '{text}' at y={y:.1f}")
                        continue
                    
                    # その他の楽器
                    instrument_keywords = ['Vo', 'Pf', 'Key', 'Ba', 'Dr', 'Gt', 'Piano', 'Keyboard', 'Organ', 'Synth', 'Voc', 'Lead']
                    # 柔軟なマッチング（部分一致、大文字小文字を無視）
                    if any(kw.lower() in corrected_text.lower() for kw in instrument_keywords):
                        # Ba. や Bass は除外
                        if 'ba' in corrected_text.lower() and 'key' not in corrected_text.lower():
                            continue
                            x = ocr_data['left'][i] * 72/200
                            y = ocr_data['top'][i] * 72/200
                            height = ocr_data['height'][i] * 72/200
                            
                            labels.append({
                                'label': corrected_text,
                                'x': x,
                                'y': y,
                                'bbox': [x, y, x + 50, y + height],
                                'height': height
                            })
                            if corrected_text != text:
                                print(f"      OCR検出: '{corrected_text}' at y={y:.1f} (元: '{text}')")
                            else:
                                print(f"      OCR検出: '{corrected_text}' at y={y:.1f}")
            
        except Exception as e:
            print(f"      OCRエラー: {str(e)}")
        
        return labels
    
    def _detect_chord_lines(self, page, system):
        """コード記号が書かれた行を検出"""
        chord_lines = []
        
        try:
            # システムの範囲を取得
            if not system:
                return chord_lines
            
            min_y = min(inst['y'] for inst in system)
            max_y = max(inst['y'] + inst.get('height', 30) for inst in system)
            
            # テキストを取得
            blocks = page.get_text("dict")
            
            # Y座標別にコード記号を収集
            chord_by_y = {}
            has_text = False
            
            for block in blocks.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            bbox = span.get("bbox")
                            
                            if bbox and text:
                                # システム範囲内
                                if min_y <= bbox[1] <= max_y:
                                    # コード記号パターンにマッチするかチェック
                                    if self._is_chord_symbol(text):
                                        has_text = True
                                        y_coord = round(bbox[1])  # Y座標を丸める
                                        if y_coord not in chord_by_y:
                                            chord_by_y[y_coord] = []
                                        chord_by_y[y_coord].append({
                                            'text': text,
                                            'x': bbox[0],
                                            'y': bbox[1],
                                            'bbox': bbox
                                        })
            
            # テキストがない場合、OMRアプローチでコードを検出
            if not has_text and len(chord_by_y) == 0:
                print("      テキストがないため、OMRでコード検出を試行...")
                chord_by_y = self._detect_chords_by_omr(page, system)
            
            # 近いY座標のコードをグループ化
            grouped_chords = self._group_chord_by_y(chord_by_y)
            
            # コードが2つ以上ある行をコードラインとして認識
            for y_group, chords in grouped_chords.items():
                if len(chords) >= 2:  # 2つ以上のコードがある場合
                    avg_y = sum(c['y'] for c in chords) / len(chords)
                    min_x = min(c['x'] for c in chords)
                    max_x = max(c['x'] + c['bbox'][2] - c['bbox'][0] for c in chords)
                    
                    chord_lines.append({
                        'y': avg_y,
                        'x': min_x,
                        'bbox': [min_x, avg_y - 10, max_x, avg_y + 20],
                        'height': 30,
                        'chords': chords
                    })
                    
                    chord_text = [c['text'] for c in chords[:5]]
                    if len(chords) > 5:
                        chord_text.append('...')
                    print(f"      コードライン検出: {chord_text} at y={avg_y:.1f}")
            
        except Exception as e:
            print(f"      コード検出エラー: {str(e)}")
        
        return chord_lines
    
    def _is_chord_symbol(self, text):
        """テキストがコード記号かどうか判定"""
        # 空白や長すぎるテキストを除外
        if not text or len(text) > 15:
            return False
        
        # 数字のみ、または特殊文字のみを除外
        if text.isdigit() or all(c in '.,!?-_()[]{}' for c in text):
            return False
        
        # 基本的なコードパターン
        # C, Cm, C7, Cmaj7, C#m7b5, C/G など
        if self.chord_pattern.match(text):
            return True
        
        # シンプルなパターン（A-Gで始まる）
        if self.simple_chord_pattern.match(text) and len(text) <= 7:
            return True
        
        # 日本語コード名（イロハニホヘト）
        if self.jp_chord_pattern.match(text):
            return True
        
        # 括弧付きコード（(C), [G7] など）
        if text.startswith('(') and text.endswith(')'):
            inner = text[1:-1]
            return self._is_chord_symbol(inner)
        if text.startswith('[') and text.endswith(']'):
            inner = text[1:-1]
            return self._is_chord_symbol(inner)
        
        # N.C. (No Chord)
        if text == 'N.C.' or text == 'NC' or text == 'N.C':
            return True
        
        return False
    
    def _group_chord_by_y(self, chord_by_y):
        """近いY座標のコードをグループ化"""
        grouped = {}
        threshold = 5  # Y座標の闾値
        
        for y, chords in sorted(chord_by_y.items()):
            found_group = False
            for group_y in grouped:
                if abs(y - group_y) <= threshold:
                    grouped[group_y].extend(chords)
                    found_group = True
                    break
            
            if not found_group:
                grouped[y] = chords
        
        return grouped
    
    def _detect_chords_by_omr(self, page, system):
        """画像解析によるコード検出（OMRアプローチ）"""
        chord_by_y = {}
        
        try:
            # システムの範囲
            min_y = min(inst['y'] for inst in system)
            max_y = max(inst['y'] + inst.get('height', 30) for inst in system)
            
            # 高解像度でページをスキャン
            mat = fitz.Matrix(300/72.0, 300/72.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)
            
            # グレースケール変換
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # システム領域を切り抜き
            y_start = int(min_y * 300/72)
            y_end = int(max_y * 300/72)
            system_img = gray[y_start:y_end, :]
            
            # コードがありそうな領域（上部20%）をスキャン
            chord_region = system_img[:int(system_img.shape[0] * 0.3), :]
            
            # コントラスト強化
            chord_region = cv2.convertScaleAbs(chord_region, alpha=1.5, beta=20)
            
            # OCR実行
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGabcdefgm#b0123456789M7majindsugo-/() '
            ocr_result = pytesseract.image_to_string(chord_region, config=custom_config, lang='eng')
            
            # コード記号を抽出
            if ocr_result:
                words = ocr_result.split()
                y_coord = min_y + 10  # 推定位置
                chord_by_y[round(y_coord)] = []
                
                for i, word in enumerate(words):
                    # コード記号の修正（OCR誤認識対応）
                    corrected_word = word
                    # 一般的なOCR誤認識の修正
                    corrections = {
                        '0': 'D',  # 0 -> D
                        'l': '/',  # l -> /
                        'I': '/',  # I -> /
                        '6': 'G',  # 6 -> G
                    }
                    for wrong, correct in corrections.items():
                        if wrong in word and len(word) <= 4:
                            corrected_word = word.replace(wrong, correct)
                    
                    if self._is_chord_symbol(corrected_word):
                        chord_by_y[round(y_coord)].append({
                            'text': corrected_word,
                            'x': 100 + i * 50,  # 推定位置
                            'y': y_coord,
                            'bbox': [100 + i * 50, y_coord, 100 + i * 50 + 40, y_coord + 20]
                        })
                        
                if chord_by_y.get(round(y_coord)):
                    print(f"      OMRコード検出: {[c['text'] for c in chord_by_y[round(y_coord)]]}")
            
        except Exception as e:
            print(f"      OMRコード検出エラー: {str(e)}")
        
        return chord_by_y
    
    def _ocr_find_chord_parts(self, page, system):
        """コードパートをOCRで検索"""
        chord_labels = []
        
        try:
            # システムの範囲を取得
            if not system:
                return chord_labels
            
            min_y = min(inst['y'] for inst in system)
            max_y = max(inst['y'] + inst.get('height', 30) for inst in system)
            
            # ページを画像として取得
            mat = fitz.Matrix(200/72.0, 200/72.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)
            
            # システム領域の左端部分のみをOCR
            height, width = img_array.shape[:2]
            y_start = int(min_y * 200/72)
            y_end = int(max_y * 200/72)
            left_region = img_array[y_start:y_end, :int(width * 0.2)]
            
            # OCR実行
            ocr_data = pytesseract.image_to_data(
                left_region, 
                output_type=pytesseract.Output.DICT,
                lang='eng',  # 英語のみでChやChordを検索
                config='--psm 6'  # 均一なブロックを想定
            )
            
            # コード関連のキーワードを検索
            chord_keywords = ['Ch.', 'Ch', 'Chord', 'CHO', 'CHORD']
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                if text and ocr_data['conf'][i] > 40:
                    # コードキーワードの完全一致をチェック
                    if text in chord_keywords:
                        x = ocr_data['left'][i] * 72/200
                        y = y_start * 72/200 + ocr_data['top'][i] * 72/200
                        height = ocr_data['height'][i] * 72/200
                        
                        chord_labels.append({
                            'label': text,
                            'x': x,
                            'y': y,
                            'bbox': [x, y, x + 50, y + height],
                            'height': height
                        })
                        print(f"      コードOCR検出: '{text}' at y={y:.1f}")
                        break  # 1つ見つかったら終了
            
        except Exception as e:
            print(f"      コードOCRエラー: {str(e)}")
        
        return chord_labels
    
    def _extract_lyrics(self, page, system):
        """ボーカルパートの歌詞を抽出"""
        lyrics = []
        
        try:
            # ボーカルパートを特定
            vocal_part = None
            for inst in system:
                if self._identify_part_type(inst['label'], ['vocal']) == 'vocal':
                    vocal_part = inst
                    break
            
            if not vocal_part:
                return None
            
            # ボーカルライン周辺のテキストを抽出
            blocks = page.get_text("dict")
            
            # 歌詞の候補を収集
            lyric_candidates = []
            
            for block in blocks.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            bbox = span.get("bbox")
                            
                            if bbox and text:
                                # ボーカルラインの上下20ピクセル以内
                                y_distance = abs(bbox[1] - vocal_part['y'])
                                if y_distance < 20:
                                    # X座標が楽器名より右
                                    if bbox[0] > 80:
                                        # 楽器名ではない
                                        is_instrument = any(kw in text for kw in ['Vo', 'Gt', 'Ba', 'Dr', 'Key', 'Pf', 'Kb'])
                                        # 数字だけではない
                                        is_number_only = text.isdigit()
                                        # 記号だけではない
                                        is_symbol_only = all(c in '.,!?-_()[]{}' for c in text)
                                        
                                        if not is_instrument and not is_number_only and not is_symbol_only:
                                            lyric_candidates.append({
                                                'text': text,
                                                'x': bbox[0],
                                                'y': bbox[1],
                                                'width': bbox[2] - bbox[0],
                                                'y_distance': y_distance
                                            })
            
            # Y距離が最も近いものを優先して選択
            lyric_candidates.sort(key=lambda x: x['y_distance'])
            
            # 同じY座標のものをグループ化
            if lyric_candidates:
                current_y = lyric_candidates[0]['y']
                for candidate in lyric_candidates:
                    if abs(candidate['y'] - current_y) < 5:  # 同じ行とみなす
                        lyrics.append(candidate)
            
            # X座標でソート
            lyrics.sort(key=lambda x: x['x'])
            
        except Exception as e:
            print(f"      歌詞抽出エラー: {str(e)}")
        
        return lyrics if lyrics else None