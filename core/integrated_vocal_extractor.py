import fitz
import os
from .vocal_structure_analyzer import VocalStructureAnalyzer

class IntegratedVocalExtractor:
    """コード・メロディ・歌詞を一体として抽出"""
    
    def __init__(self):
        self.analyzer = VocalStructureAnalyzer()
        self.page_width = 595
        self.page_height = 842
        self.margin = 40
    
    def extract_vocal_parts(self, pdf_path, measures_per_line=4, include_chords=True, 
                           include_lyrics=True, pages_to_extract=None):
        """ボーカルパートを統合的に抽出"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力ファイル名
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = os.path.join(
                os.path.dirname(pdf_path),
                f"{base_name}_vocal_integrated_{measures_per_line}m.pdf"
            )
            
            # 最初のページでボーカル構造を分析
            print("ボーカルパートの構造を分析中...")
            vocal_structure = self._analyze_vocal_structure(src_pdf[0])
            
            if not vocal_structure:
                print("ボーカル構造が検出できませんでした。デフォルト設定を使用します。")
                vocal_structure = self._get_default_structure()
            
            # 新しいページを作成
            current_page = output_pdf.new_page(width=self.page_width, height=self.page_height)
            current_y = self.margin
            
            # タイトル
            title = f"Vocal Part ({measures_per_line} measures/line)"
            if include_chords:
                title += " with Chords"
            if include_lyrics:
                title += " and Lyrics"
            
            current_page.insert_text(
                (self.margin, current_y),
                title,
                fontsize=14,
                color=(0, 0, 0)
            )
            current_y += 35
            
            # 各ページを処理
            total_pages = len(src_pdf)
            if pages_to_extract:
                pages_to_process = [p for p in pages_to_extract if p < total_pages]
            else:
                pages_to_process = range(min(total_pages, 10))  # 最大10ページ
            
            for page_num in pages_to_process:
                print(f"\nページ {page_num + 1} を処理中...")
                page = src_pdf[page_num]
                
                # このページのボーカルパートを抽出
                result = self._extract_page_vocals(
                    page, page_num, src_pdf, vocal_structure,
                    measures_per_line, include_chords, include_lyrics,
                    current_page, current_y, output_pdf
                )
                
                current_y = result['current_y']
                if result.get('new_page'):
                    current_page = result['new_page']
            
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
    
    def _analyze_vocal_structure(self, page):
        """ページからボーカル構造を分析"""
        page_rect = page.rect
        
        # ページの上部1/3を分析（通常ボーカルパートがある位置）
        y_start = page_rect.height * 0.05
        y_end = page_rect.height * 0.35
        
        structure = self.analyzer.analyze_vocal_part(page, y_start, y_end)
        
        if structure and structure['components']:
            print(f"検出されたコンポーネント: {', '.join(structure['components'])}")
            
            # 最適な抽出エリアを計算
            optimal_area = self.analyzer.calculate_optimal_extraction_area(structure)
            if optimal_area:
                structure['optimal_area'] = optimal_area
                print(f"最適エリア高さ: {optimal_area['height']:.1f}")
        
        return structure
    
    def _get_default_structure(self):
        """デフォルトのボーカル構造"""
        return {
            'components': ['chord', 'staff', 'lyrics'],
            'optimal_area': {
                'top': 0.10,
                'bottom': 0.30,
                'height': 0.20
            }
        }
    
    def _extract_page_vocals(self, page, page_num, src_pdf, vocal_structure,
                           measures_per_line, include_chords, include_lyrics,
                           current_page, current_y, output_pdf):
        """1ページ分のボーカルパートを抽出"""
        page_rect = page.rect
        
        # ページを小節グループに分割
        measures_per_page = 8  # 標準的な1ページの小節数
        num_groups = measures_per_page // measures_per_line
        
        # 各小節グループを処理
        for group_idx in range(num_groups):
            # 新しいページが必要かチェック
            required_height = 100  # ボーカルパート1つ分の高さ
            if current_y + required_height > self.page_height - self.margin:
                current_page = output_pdf.new_page(width=self.page_width, height=self.page_height)
                current_y = self.margin
            
            # 小節番号
            measure_start = page_num * measures_per_page + group_idx * measures_per_line + 1
            measure_end = measure_start + measures_per_line - 1
            
            # グループラベル
            current_page.insert_text(
                (self.margin, current_y),
                f"Measures {measure_start}-{measure_end}",
                fontsize=10,
                color=(0.5, 0.5, 0.5)
            )
            current_y += 15
            
            # ボーカルパートの抽出
            current_y = self._render_vocal_group(
                page, page_num, src_pdf, vocal_structure,
                group_idx, measures_per_line, measures_per_page,
                include_chords, include_lyrics,
                current_page, current_y
            )
            
            current_y += 20  # グループ間のスペース
        
        return {
            'current_y': current_y,
            'new_page': current_page
        }
    
    def _render_vocal_group(self, page, page_num, src_pdf, vocal_structure,
                          group_idx, measures_per_line, measures_per_page,
                          include_chords, include_lyrics,
                          current_page, current_y):
        """ボーカルグループをレンダリング"""
        page_rect = page.rect
        
        # 小節の水平位置を計算
        measure_width = page_rect.width / measures_per_page
        x_start = group_idx * measures_per_line * measure_width
        x_end = x_start + (measures_per_line * measure_width)
        
        # ボーカルパートの垂直範囲
        if vocal_structure.get('optimal_area'):
            area = vocal_structure['optimal_area']
            if isinstance(area['top'], float) and area['top'] < 1:
                # 比率で指定されている場合
                y_top = page_rect.height * area['top']
                y_bottom = page_rect.height * area['bottom']
            else:
                # 絶対座標の場合
                y_top = area['top']
                y_bottom = area['bottom']
        else:
            # デフォルト
            y_top = page_rect.height * 0.10
            y_bottom = page_rect.height * 0.30
        
        # 全体の高さ
        total_height = y_bottom - y_top
        
        # コンポーネントごとの高さを計算
        if include_chords and include_lyrics:
            chord_height = total_height * 0.15
            staff_height = total_height * 0.50
            lyrics_height = total_height * 0.35
        elif include_chords:
            chord_height = total_height * 0.20
            staff_height = total_height * 0.80
            lyrics_height = 0
        elif include_lyrics:
            chord_height = 0
            staff_height = total_height * 0.65
            lyrics_height = total_height * 0.35
        else:
            chord_height = 0
            staff_height = total_height
            lyrics_height = 0
        
        # 統合された抽出エリア
        clip_rect = fitz.Rect(x_start, y_top, x_end, y_bottom)
        
        # 配置先の高さを調整
        dest_height = 80  # 基本高さ
        if not include_chords:
            dest_height -= 15
        if not include_lyrics:
            dest_height -= 20
        
        dest_rect = fitz.Rect(
            self.margin + 20,
            current_y,
            self.page_width - self.margin,
            current_y + dest_height
        )
        
        # 背景を薄い色で塗る
        bg_rect = fitz.Rect(
            dest_rect.x0 - 5,
            dest_rect.y0 - 2,
            dest_rect.x1 + 5,
            dest_rect.y1 + 2
        )
        current_page.draw_rect(bg_rect, color=(0.95, 0.98, 1.0), fill=(0.98, 0.99, 1.0))
        
        # ボーカルパートを配置
        try:
            current_page.show_pdf_page(dest_rect, src_pdf, page_num, clip=clip_rect)
            
            # ラベル
            current_page.insert_text(
                (self.margin - 10, current_y + dest_height / 2),
                "Vo.",
                fontsize=11,
                color=(0, 0, 0.8)
            )
            
            # コンポーネントの説明（デバッグ用）
            if include_chords or include_lyrics:
                info_y = current_y + 5
                info_x = dest_rect.x1 + 10
                
                if include_chords:
                    current_page.insert_text(
                        (info_x, info_y),
                        "C",
                        fontsize=8,
                        color=(0, 0.5, 0)
                    )
                    info_y += 10
                
                current_page.insert_text(
                    (info_x, info_y + staff_height/2),
                    "♪",
                    fontsize=10,
                    color=(0, 0, 0)
                )
                
                if include_lyrics:
                    current_page.insert_text(
                        (info_x, info_y + staff_height + 5),
                        "詞",
                        fontsize=8,
                        color=(0.5, 0, 0)
                    )
            
        except Exception as e:
            print(f"  レンダリングエラー: {str(e)}")
        
        return current_y + dest_height