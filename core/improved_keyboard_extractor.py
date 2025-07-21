import fitz
import os

class ImprovedKeyboardExtractor:
    """改善されたキーボード抽出 - より柔軟な検出"""
    
    def __init__(self):
        # キーボードの典型的な位置（ページ比率）
        self.keyboard_positions = [
            {'name': 'upper_keyboard', 'y_start': 0.35, 'y_end': 0.50},  # 上部キーボード
            {'name': 'middle_keyboard', 'y_start': 0.45, 'y_end': 0.60}, # 中央キーボード
            {'name': 'lower_keyboard', 'y_start': 0.55, 'y_end': 0.70},  # 下部キーボード
        ]
        
        # 検出方法の優先順位
        self.detection_methods = [
            'text_based',      # テキストラベルで検出
            'position_based',  # 位置で推定
            'default_layout'   # デフォルトレイアウト
        ]
    
    def extract_keyboard(self, pdf_path, measures_per_line=4, pages_to_extract=None):
        """キーボードパートを抽出（改善版）"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力パス
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = os.path.join(
                os.path.dirname(pdf_path),
                f"{base_name}_keyboard_improved_{measures_per_line}m.pdf"
            )
            
            # 新しいページ
            current_page = output_pdf.new_page(width=595, height=842)
            current_y = 40
            
            # タイトル
            current_page.insert_text(
                (40, current_y),
                f"Keyboard Part - Improved ({measures_per_line} measures/line)",
                fontsize=14,
                color=(0, 0, 0)
            )
            current_y += 35
            
            # 処理するページ
            pages = pages_to_extract if pages_to_extract else range(min(5, len(src_pdf)))
            
            for page_num in pages:
                print(f"\nページ {page_num + 1} を処理中...")
                page = src_pdf[page_num]
                
                # キーボード領域を検出
                keyboard_areas = self._detect_keyboard_areas(page, page_num)
                
                if not keyboard_areas:
                    print("  キーボード領域が検出されなかったため、デフォルト位置を使用")
                    keyboard_areas = self._get_default_keyboard_areas(page)
                
                # 各キーボード領域を処理
                for area_idx, area in enumerate(keyboard_areas):
                    print(f"  キーボード領域 {area_idx + 1} を抽出中...")
                    
                    # 小節ごとに分割
                    measure_groups = self._split_by_measures(area, measures_per_line)
                    
                    for group in measure_groups:
                        if current_y + 80 > 842 - 40:
                            current_page = output_pdf.new_page(width=595, height=842)
                            current_y = 40
                        
                        # ラベル
                        current_page.insert_text(
                            (40, current_y),
                            f"Page {page_num + 1}, Measures {group['measure_range']}",
                            fontsize=10,
                            color=(0.5, 0.5, 0.5)
                        )
                        current_y += 15
                        
                        # キーボードパートを配置
                        dest_rect = fitz.Rect(
                            60,
                            current_y,
                            595 - 40,
                            current_y + 60
                        )
                        
                        # 背景色
                        bg_rect = fitz.Rect(
                            dest_rect.x0 - 5,
                            dest_rect.y0 - 2,
                            dest_rect.x1 + 5,
                            dest_rect.y1 + 2
                        )
                        current_page.draw_rect(
                            bg_rect,
                            color=(0.95, 0.95, 1.0),
                            fill=(0.98, 0.98, 1.0)
                        )
                        
                        # PDFの内容を配置
                        try:
                            current_page.show_pdf_page(
                                dest_rect, src_pdf, page_num,
                                clip=group['clip_rect']
                            )
                            
                            # ラベル
                            current_page.insert_text(
                                (35, current_y + 30),
                                "Key.",
                                fontsize=11,
                                color=(0, 0, 0.8)
                            )
                            
                        except Exception as e:
                            print(f"    配置エラー: {str(e)}")
                        
                        current_y += 65
            
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
    
    def _detect_keyboard_areas(self, page, page_num):
        """キーボード領域を検出"""
        page_rect = page.rect
        detected_areas = []
        
        # 方法1: テキストベースの検出
        text_blocks = page.get_text("dict")["blocks"]
        keyboard_keywords = ['key', 'keyboard', 'piano', 'pf', 'synth', 'organ']
        
        for block in text_blocks:
            if "lines" not in block:
                continue
            
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip().lower()
                    
                    # キーワードマッチング
                    if any(kw in text for kw in keyboard_keywords):
                        bbox = span["bbox"]
                        if bbox[0] < 150:  # 左側のラベル
                            detected_areas.append({
                                'method': 'text_based',
                                'label': span["text"],
                                'y_center': (bbox[1] + bbox[3]) / 2,
                                'y_start': bbox[1] - 20,
                                'y_end': bbox[3] + 60
                            })
        
        # 方法2: 位置ベースの検出（テキストが見つからない場合）
        if not detected_areas:
            # ページの中央付近を探す
            for pos in self.keyboard_positions:
                y_start = page_rect.height * pos['y_start']
                y_end = page_rect.height * pos['y_end']
                
                # この範囲に何か内容があるかチェック
                clip_rect = fitz.Rect(0, y_start, page_rect.width, y_end)
                pix = page.get_pixmap(clip=clip_rect)
                
                # ピクセルデータをチェック（空白でないか）
                if self._has_content(pix):
                    detected_areas.append({
                        'method': 'position_based',
                        'label': f'Keyboard {pos["name"]}',
                        'y_center': (y_start + y_end) / 2,
                        'y_start': y_start,
                        'y_end': y_end
                    })
                    break  # 最初に見つかったものを使用
        
        return detected_areas
    
    def _get_default_keyboard_areas(self, page):
        """デフォルトのキーボード領域"""
        page_rect = page.rect
        
        # 典型的なバンドスコアのキーボード位置
        return [{
            'method': 'default_layout',
            'label': 'Keyboard (default)',
            'y_center': page_rect.height * 0.5,
            'y_start': page_rect.height * 0.45,
            'y_end': page_rect.height * 0.60
        }]
    
    def _split_by_measures(self, area, measures_per_line):
        """領域を小節ごとに分割"""
        page_width = 1067  # 元のページ幅（テストPDFから）
        measures_per_page = 8
        measure_width = page_width / measures_per_page
        
        groups = []
        
        for start_measure in range(0, measures_per_page, measures_per_line):
            x_start = start_measure * measure_width
            x_end = (start_measure + measures_per_line) * measure_width
            
            groups.append({
                'measure_range': f"{start_measure + 1}-{start_measure + measures_per_line}",
                'clip_rect': fitz.Rect(
                    x_start,
                    area['y_start'],
                    x_end,
                    area['y_end']
                )
            })
        
        return groups
    
    def _has_content(self, pixmap):
        """ピクスマップに内容があるかチェック"""
        # 簡易的なチェック：全体が白でないか
        samples = pixmap.samples
        if len(samples) > 1000:  # サンプルがある程度ある
            # 最初の1000バイトをチェック
            non_white = sum(1 for b in samples[:1000] if b < 250)
            return non_white > 100  # 100以上の非白ピクセルがあれば内容ありとする
        return False