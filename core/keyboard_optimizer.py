import fitz
import cv2
import numpy as np
import os

class KeyboardOptimizer:
    """キーボードパート（大譜表）の最適化抽出"""
    
    def __init__(self):
        # 大譜表の特徴
        self.grand_staff_characteristics = {
            'brace_width': 15,  # 大括弧の幅
            'staff_gap': 60,    # ト音とヘ音の間隔（ピクセル）
            'min_staff_lines': 10,  # 最小ライン数（5+5）
            'typical_height_ratio': 0.25  # ページに対する典型的な高さ比
        }
        
        # 音部記号の検出パターン
        self.clef_regions = {
            'treble': {'x_ratio': 0.05, 'y_ratio': 0.4},  # ト音記号の位置
            'bass': {'x_ratio': 0.05, 'y_ratio': 0.6}     # ヘ音記号の位置
        }
    
    def detect_grand_staff(self, page, y_start, y_end):
        """大譜表（Grand Staff）を検出"""
        try:
            # ページを画像に変換
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 指定範囲を切り出し
            height, width = img.shape[:2]
            y_start_px = int(y_start * 2)
            y_end_px = int(y_end * 2)
            
            roi = gray[y_start_px:y_end_px, :]
            
            # 五線を検出
            staff_lines = self._detect_staff_lines(roi)
            
            # 大譜表を識別
            grand_staffs = self._identify_grand_staffs(staff_lines, y_start)
            
            return grand_staffs
            
        except Exception as e:
            print(f"大譜表検出エラー: {str(e)}")
            return []
    
    def _detect_staff_lines(self, gray_img):
        """五線を検出"""
        # エッジ検出
        edges = cv2.Canny(gray_img, 50, 150)
        
        # 水平線を検出
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100,
                               minLineLength=gray_img.shape[1]*0.5,
                               maxLineGap=10)
        
        if lines is None:
            return []
        
        # 水平線をフィルタリング
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 3:  # ほぼ水平
                horizontal_lines.append({
                    'y': y1 / 2,  # 元の解像度に戻す
                    'x_start': x1 / 2,
                    'x_end': x2 / 2,
                    'length': (x2 - x1) / 2
                })
        
        # Y座標でソート
        horizontal_lines.sort(key=lambda l: l['y'])
        
        return horizontal_lines
    
    def _identify_grand_staffs(self, staff_lines, y_offset):
        """大譜表を識別"""
        if len(staff_lines) < 10:  # 最低10本必要（5+5）
            return []
        
        grand_staffs = []
        i = 0
        
        while i < len(staff_lines) - 9:
            # 最初の5本をチェック（ト音記号の五線）
            first_group = []
            for j in range(5):
                if i + j < len(staff_lines):
                    first_group.append(staff_lines[i + j])
            
            if len(first_group) == 5:
                # 五線の間隔をチェック
                intervals = [first_group[k+1]['y'] - first_group[k]['y'] 
                           for k in range(4)]
                avg_interval = sum(intervals) / len(intervals)
                
                # 間隔が一定かチェック
                if all(abs(iv - avg_interval) < avg_interval * 0.3 for iv in intervals):
                    # 次の5本を探す（ヘ音記号の五線）
                    gap_start = i + 5
                    
                    # 適切な間隔の後に次の五線があるか
                    for k in range(gap_start, min(gap_start + 10, len(staff_lines) - 4)):
                        second_group = []
                        for j in range(5):
                            if k + j < len(staff_lines):
                                second_group.append(staff_lines[k + j])
                        
                        if len(second_group) == 5:
                            # 二つ目の五線の間隔をチェック
                            intervals2 = [second_group[m+1]['y'] - second_group[m]['y'] 
                                        for m in range(4)]
                            avg_interval2 = sum(intervals2) / len(intervals2)
                            
                            if all(abs(iv - avg_interval2) < avg_interval2 * 0.3 for iv in intervals2):
                                # 大譜表として記録
                                grand_staff = {
                                    'treble_staff': {
                                        'lines': first_group,
                                        'top': first_group[0]['y'] + y_offset,
                                        'bottom': first_group[4]['y'] + y_offset,
                                        'center': sum(l['y'] for l in first_group) / 5 + y_offset
                                    },
                                    'bass_staff': {
                                        'lines': second_group,
                                        'top': second_group[0]['y'] + y_offset,
                                        'bottom': second_group[4]['y'] + y_offset,
                                        'center': sum(l['y'] for l in second_group) / 5 + y_offset
                                    },
                                    'total_top': first_group[0]['y'] + y_offset - 10,
                                    'total_bottom': second_group[4]['y'] + y_offset + 10,
                                    'gap': second_group[0]['y'] - first_group[4]['y']
                                }
                                
                                grand_staffs.append(grand_staff)
                                i = k + 5  # 次の検索位置
                                break
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        return grand_staffs
    
    def optimize_keyboard_extraction(self, page, grand_staff, measures_per_line=4):
        """キーボードパートの抽出を最適化"""
        page_rect = page.rect
        
        # 小節の位置を推定
        measures_per_page = 8
        measure_width = page_rect.width / measures_per_page
        
        extraction_areas = []
        
        for group_idx in range(0, measures_per_page, measures_per_line):
            # 水平範囲
            x_start = group_idx * measure_width
            x_end = x_start + (measures_per_line * measure_width)
            
            # 垂直範囲（大譜表全体を含む）
            y_margin = 15
            area = {
                'measure_range': f"{group_idx + 1}-{group_idx + measures_per_line}",
                'clip_rect': fitz.Rect(
                    x_start - 10,
                    grand_staff['total_top'] - y_margin,
                    x_end + 10,
                    grand_staff['total_bottom'] + y_margin
                ),
                'has_treble': True,
                'has_bass': True,
                'is_grand_staff': True
            }
            
            extraction_areas.append(area)
        
        return extraction_areas
    
    def extract_with_optimization(self, pdf_path, measures_per_line=4, pages_to_extract=None):
        """最適化されたキーボード抽出"""
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力パス
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = os.path.join(
                os.path.dirname(pdf_path),
                f"{base_name}_keyboard_optimized_{measures_per_line}m.pdf"
            )
            
            # 新しいページ
            current_page = output_pdf.new_page(width=595, height=842)
            current_y = 40
            
            # タイトル
            current_page.insert_text(
                (40, current_y),
                f"Keyboard Part - Optimized ({measures_per_line} measures/line)",
                fontsize=14,
                color=(0, 0, 0)
            )
            current_y += 35
            
            # 各ページを処理
            for page_num in range(min(5, len(src_pdf))):
                if pages_to_extract and page_num not in pages_to_extract:
                    continue
                
                print(f"\nページ {page_num + 1} を処理中...")
                page = src_pdf[page_num]
                
                # キーボードパートの領域を推定（通常ページの中央付近）
                page_rect = page.rect
                y_start = page_rect.height * 0.35
                y_end = page_rect.height * 0.65
                
                # 大譜表を検出
                grand_staffs = self.detect_grand_staff(page, y_start, y_end)
                
                if grand_staffs:
                    print(f"  大譜表を{len(grand_staffs)}個検出")
                    
                    for staff_idx, grand_staff in enumerate(grand_staffs):
                        # 抽出エリアを最適化
                        areas = self.optimize_keyboard_extraction(
                            page, grand_staff, measures_per_line
                        )
                        
                        # 各エリアをレンダリング
                        for area in areas:
                            if current_y + 100 > 842 - 40:
                                current_page = output_pdf.new_page(width=595, height=842)
                                current_y = 40
                            
                            # ラベル
                            current_page.insert_text(
                                (40, current_y),
                                f"Measures {area['measure_range']}",
                                fontsize=10,
                                color=(0.5, 0.5, 0.5)
                            )
                            current_y += 15
                            
                            # 大譜表を配置
                            dest_rect = fitz.Rect(
                                60,
                                current_y,
                                595 - 40,
                                current_y + 80
                            )
                            
                            # 背景
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
                            
                            # キーボードパートを配置
                            current_page.show_pdf_page(
                                dest_rect, src_pdf, page_num,
                                clip=area['clip_rect']
                            )
                            
                            # ラベル
                            current_page.insert_text(
                                (35, current_y + 40),
                                "Key.",
                                fontsize=11,
                                color=(0, 0, 0.8)
                            )
                            
                            # 大譜表インジケーター
                            brace_x = 55
                            brace_top = current_y + 10
                            brace_bottom = current_y + 70
                            
                            # 大括弧を描画
                            current_page.draw_line(
                                fitz.Point(brace_x, brace_top),
                                fitz.Point(brace_x - 3, brace_top + 5),
                                width=2,
                                color=(0, 0, 0)
                            )
                            current_page.draw_line(
                                fitz.Point(brace_x - 3, brace_top + 5),
                                fitz.Point(brace_x - 3, brace_bottom - 5),
                                width=2,
                                color=(0, 0, 0)
                            )
                            current_page.draw_line(
                                fitz.Point(brace_x - 3, brace_bottom - 5),
                                fitz.Point(brace_x, brace_bottom),
                                width=2,
                                color=(0, 0, 0)
                            )
                            
                            current_y += 85
                else:
                    print("  大譜表が検出されませんでした")
            
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