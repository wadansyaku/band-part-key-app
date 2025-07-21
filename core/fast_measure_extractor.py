import fitz
import re
import os

class FastMeasureExtractor:
    """高速な小節ベースの抽出 - OCRを最小限に"""
    
    def __init__(self):
        # 楽器パターン（簡略版）
        self.instrument_patterns = {
            'vocal': ['Vo', 'Vocal', 'VOC'],
            'chord': [],  # コードは記号で検出
            'keyboard': ['Key', 'Piano', 'Pf', 'Synth']
        }
        
        # コードパターン
        self.chord_pattern = re.compile(r'\b[A-G][#b]?(?:m|M|maj|min|dim|aug|sus)?(?:6|7|9|11|13)?(?:/[A-G][#b]?)?\b')
        
        # ページ設定
        self.page_width = 595
        self.page_height = 842
        self.margin = 40
    
    def extract_parts(self, pdf_path, selected_parts=['vocal', 'chord', 'keyboard'], 
                     measures_per_line=4, show_lyrics=False):
        """高速なパート抽出"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力先の設定
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = os.path.join(
                os.path.dirname(pdf_path),
                f"{base_name}_extracted_{measures_per_line}m.pdf"
            )
            
            # 新しいページを作成
            current_page = output_pdf.new_page(width=self.page_width, height=self.page_height)
            current_y = self.margin
            
            # タイトル
            current_page.insert_text(
                (self.margin, current_y),
                f"Extracted Parts ({measures_per_line} measures per line)",
                fontsize=14,
                color=(0, 0, 0)
            )
            current_y += 30
            
            # 各ページを処理（最初の3ページのみ高速処理）
            for page_num in range(min(3, len(src_pdf))):
                print(f"\nページ {page_num + 1} を高速処理中...")
                page = src_pdf[page_num]
                
                # ページからパートを検出（簡易版）
                parts = self._detect_parts_fast(page, selected_parts)
                
                if not parts:
                    # パートが見つからない場合は仮定
                    parts = self._assume_default_parts(page, selected_parts)
                
                # 小節グループごとに処理
                measure_groups = self._extract_measure_groups(
                    page, parts, page_num, src_pdf, measures_per_line
                )
                
                # 出力ページに配置
                for group in measure_groups:
                    if current_y + 150 > self.page_height - self.margin:
                        current_page = output_pdf.new_page(
                            width=self.page_width, 
                            height=self.page_height
                        )
                        current_y = self.margin
                    
                    current_y = self._render_measure_group(
                        current_page, current_y, group, page_num, src_pdf
                    )
            
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
    
    def _detect_parts_fast(self, page, selected_parts):
        """高速なパート検出（テキスト抽出のみ）"""
        parts = []
        
        # テキストブロックを取得
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    
                    # 楽器名をチェック
                    for part_type, patterns in self.instrument_patterns.items():
                        if part_type not in selected_parts:
                            continue
                            
                        for pattern in patterns:
                            if pattern.lower() in text.lower():
                                parts.append({
                                    'type': part_type,
                                    'text': text,
                                    'bbox': span["bbox"],
                                    'y': span["bbox"][1]
                                })
                                break
                    
                    # コードをチェック
                    if 'chord' in selected_parts and self.chord_pattern.match(text):
                        parts.append({
                            'type': 'chord',
                            'text': text,
                            'bbox': span["bbox"],
                            'y': span["bbox"][1]
                        })
        
        return parts
    
    def _assume_default_parts(self, page, selected_parts):
        """デフォルトのパート配置を仮定"""
        page_rect = page.rect
        parts = []
        
        # 典型的な楽譜レイアウトを仮定
        default_layout = [
            {'type': 'vocal', 'y_ratio': 0.15, 'height_ratio': 0.10},
            {'type': 'chord', 'y_ratio': 0.25, 'height_ratio': 0.05},
            {'type': 'keyboard', 'y_ratio': 0.30, 'height_ratio': 0.15}
        ]
        
        for layout in default_layout:
            if layout['type'] in selected_parts:
                parts.append({
                    'type': layout['type'],
                    'text': layout['type'].capitalize(),
                    'y': page_rect.height * layout['y_ratio'],
                    'height': page_rect.height * layout['height_ratio']
                })
        
        return parts
    
    def _extract_measure_groups(self, page, parts, page_num, src_pdf, measures_per_line):
        """小節グループの抽出"""
        groups = []
        page_rect = page.rect
        
        # ページの小節数を推定（通常8小節）
        total_measures = 8
        measure_width = page_rect.width / total_measures
        
        # 小節グループごとに処理
        for start_measure in range(0, total_measures, measures_per_line):
            group_parts = []
            
            for part in parts:
                # 小節範囲の切り抜き領域
                clip_rect = fitz.Rect(
                    measure_width * start_measure,
                    part.get('y', 0) - 10,
                    measure_width * (start_measure + measures_per_line),
                    part.get('y', 0) + part.get('height', 50)
                )
                
                group_parts.append({
                    'type': part['type'],
                    'text': part['text'],
                    'clip_rect': clip_rect
                })
            
            groups.append({
                'measures': f"{start_measure + 1}-{start_measure + measures_per_line}",
                'parts': group_parts
            })
        
        return groups
    
    def _render_measure_group(self, current_page, current_y, group, page_num, src_pdf):
        """小節グループをレンダリング"""
        # グループラベル
        current_page.insert_text(
            (self.margin, current_y),
            f"Measures {group['measures']}",
            fontsize=10,
            color=(0.3, 0.3, 0.3)
        )
        current_y += 15
        
        # 各パートを配置
        for part in group['parts']:
            # パート名
            current_page.insert_text(
                (self.margin, current_y + 20),
                part['text'],
                fontsize=9,
                color=(0, 0, 0)
            )
            
            # パートの内容を配置
            part_height = 40
            dest_rect = fitz.Rect(
                self.margin + 60,
                current_y,
                self.page_width - self.margin,
                current_y + part_height
            )
            
            try:
                current_page.show_pdf_page(
                    dest_rect, 
                    src_pdf, 
                    page_num, 
                    clip=part['clip_rect']
                )
            except Exception as e:
                print(f"配置エラー: {str(e)}")
            
            current_y += part_height + 5
        
        return current_y + 15