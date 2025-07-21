import fitz
import os

class FastMeasureExtractorV2:
    """高速化された小節ベース抽出（OCR最小化）"""
    
    def __init__(self):
        # デフォルトの楽器配置
        self.default_layouts = {
            'vocal_keyboard': [
                {'type': 'vocal', 'label': 'Vo.', 'y_ratio': 0.15, 'height_ratio': 0.15},
                {'type': 'keyboard', 'label': 'Key.', 'y_ratio': 0.45, 'height_ratio': 0.20}
            ],
            'vocal_chord_keyboard': [
                {'type': 'vocal', 'label': 'Vo.', 'y_ratio': 0.10, 'height_ratio': 0.12},
                {'type': 'chord', 'label': 'Chord', 'y_ratio': 0.25, 'height_ratio': 0.08},
                {'type': 'keyboard', 'label': 'Key.', 'y_ratio': 0.40, 'height_ratio': 0.20}
            ]
        }
        
        self.page_width = 595
        self.page_height = 842
        self.margin = 40
    
    def extract_fast(self, pdf_path, selected_parts, measures_per_line=4, 
                    show_lyrics=False, use_ocr=False):
        """高速抽出（OCRオプション付き）"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # レイアウトを選択
            if 'chord' in selected_parts:
                layout = self.default_layouts['vocal_chord_keyboard']
            else:
                layout = self.default_layouts['vocal_keyboard']
            
            # 選択されたパートのみフィルタ
            active_parts = [part for part in layout if part['type'] in selected_parts]
            
            # 出力パス
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            ocr_suffix = "" if use_ocr else "_no_ocr"
            output_path = os.path.join(
                os.path.dirname(pdf_path),
                f"{base_name}_fast_v2_{measures_per_line}m{ocr_suffix}.pdf"
            )
            
            # 新しいページ
            current_page = output_pdf.new_page(width=self.page_width, height=self.page_height)
            current_y = self.margin
            
            # タイトル
            mode_text = "Fast Mode (OCR)" if use_ocr else "Fast Mode (No OCR)"
            current_page.insert_text(
                (self.margin, current_y),
                f"{mode_text} - {measures_per_line} measures/line",
                fontsize=14,
                color=(0, 0, 0)
            )
            current_y += 35
            
            # 各ページを処理（最大5ページ）
            for page_num in range(min(5, len(src_pdf))):
                print(f"\nページ {page_num + 1} を処理中...")
                page = src_pdf[page_num]
                
                # OCRを使う場合のみ楽器検出
                if use_ocr:
                    detected_parts = self._quick_detect_parts(page)
                    if detected_parts:
                        print(f"  OCRで{len(detected_parts)}個の楽器を検出")
                else:
                    detected_parts = []
                
                # 検出されない場合はデフォルトレイアウトを使用
                if not detected_parts:
                    detected_parts = active_parts
                    print(f"  デフォルトレイアウトを使用")
                
                # 小節グループを処理
                current_y = self._process_measure_groups(
                    page, page_num, src_pdf, detected_parts,
                    measures_per_line, show_lyrics,
                    current_page, current_y, output_pdf
                )
                
                if current_y > self.page_height - 200:
                    current_page = output_pdf.new_page(
                        width=self.page_width,
                        height=self.page_height
                    )
                    current_y = self.margin
            
            # 保存
            output_pdf.save(output_path)
            print(f"\n✓ 保存完了: {output_path}")
            
            src_pdf.close()
            output_pdf.close()
            
            return output_path
            
        except Exception as e:
            print(f"エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _quick_detect_parts(self, page):
        """高速な楽器検出（簡易OCR）"""
        # テキストのみチェック（画像OCRは行わない）
        text_blocks = page.get_text("dict")["blocks"]
        detected = []
        
        keywords = {
            'vocal': ['vo', 'vocal', 'melody', 'sing'],
            'chord': ['chord', 'ch', 'c', 'コード'],
            'keyboard': ['key', 'piano', 'pf', 'synth', 'keyboard']
        }
        
        for block in text_blocks:
            if "lines" not in block:
                continue
            
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip().lower()
                    bbox = span["bbox"]
                    
                    # 左側のテキストのみチェック
                    if bbox[0] < 150 and len(text) < 20:
                        for part_type, kws in keywords.items():
                            if any(kw in text for kw in kws):
                                detected.append({
                                    'type': part_type,
                                    'label': span["text"],
                                    'y': bbox[1],
                                    'height': bbox[3] - bbox[1]
                                })
                                break
        
        return detected
    
    def _process_measure_groups(self, page, page_num, src_pdf, parts,
                              measures_per_line, show_lyrics,
                              current_page, current_y, output_pdf):
        """小節グループを処理"""
        page_rect = page.rect
        measures_per_page = 8
        measure_width = page_rect.width / measures_per_page
        
        # システムごとに処理（通常2システム/ページ）
        systems = [
            {'y_start': 0, 'y_end': page_rect.height * 0.5},
            {'y_start': page_rect.height * 0.5, 'y_end': page_rect.height}
        ]
        
        for sys_idx, system in enumerate(systems):
            # 小節グループごとに処理
            for group_start in range(0, measures_per_page, measures_per_line):
                # グループラベル
                measure_start = page_num * measures_per_page + group_start + 1
                measure_end = measure_start + measures_per_line - 1
                
                current_page.insert_text(
                    (self.margin, current_y),
                    f"Measures {measure_start}-{measure_end}",
                    fontsize=10,
                    color=(0.5, 0.5, 0.5)
                )
                current_y += 15
                
                # 各パートを配置
                for part in parts:
                    # パートの位置を計算
                    if isinstance(part, dict) and 'y_ratio' in part:
                        # デフォルトレイアウトの場合
                        part_y = system['y_start'] + (system['y_end'] - system['y_start']) * part['y_ratio']
                        part_height = (system['y_end'] - system['y_start']) * part['height_ratio']
                        part_type = part['type']
                        part_label = part['label']
                    else:
                        # 検出されたパートの場合
                        part_y = part.get('y', system['y_start'] + 50)
                        part_height = part.get('height', 50)
                        part_type = part.get('type', 'unknown')
                        part_label = part.get('label', part_type.title())
                    
                    # クリップ領域
                    clip_rect = fitz.Rect(
                        group_start * measure_width,
                        part_y - 10,
                        (group_start + measures_per_line) * measure_width,
                        part_y + part_height + 10
                    )
                    
                    # 配置先
                    dest_height = 40
                    if part_type == 'keyboard':
                        dest_height = 50
                    elif part_type == 'chord':
                        dest_height = 30
                    
                    dest_rect = fitz.Rect(
                        self.margin + 50,
                        current_y,
                        self.page_width - self.margin,
                        current_y + dest_height
                    )
                    
                    # 背景色（パートタイプに応じて）
                    bg_color = (0.98, 0.98, 1.0)  # デフォルト
                    if part_type == 'chord':
                        bg_color = (0.98, 1.0, 0.98)
                    elif part_type == 'vocal':
                        bg_color = (1.0, 0.98, 0.98)
                    
                    bg_rect = fitz.Rect(
                        dest_rect.x0 - 2,
                        dest_rect.y0 - 1,
                        dest_rect.x1 + 2,
                        dest_rect.y1 + 1
                    )
                    current_page.draw_rect(bg_rect, fill=bg_color)
                    
                    # パートを配置
                    try:
                        current_page.show_pdf_page(
                            dest_rect, src_pdf, page_num, clip=clip_rect
                        )
                        
                        # ラベル
                        current_page.insert_text(
                            (self.margin, current_y + dest_height / 2),
                            part_label,
                            fontsize=9,
                            color=(0, 0, 0)
                        )
                        
                    except Exception as e:
                        print(f"  配置エラー: {str(e)}")
                    
                    current_y += dest_height + 5
                
                current_y += 15  # グループ間スペース
        
        return current_y