import fitz
import json
import os

class PresetExtractor:
    """プリセットを使用した楽譜抽出"""
    
    def __init__(self):
        # プリセットを読み込み
        try:
            preset_file = os.path.join(os.path.dirname(__file__), '..', 'score_presets.json')
            with open(preset_file, 'r', encoding='utf-8') as f:
                self.presets_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load presets: {e}")
            # デフォルトプリセットを使用
            self.presets_data = {
                'presets': {
                    'default': {
                        'name': 'Default Layout',
                        'description': 'Standard layout',
                        'instruments': [
                            {'type': 'vocal', 'label': 'Vocal', 'y_ratio': 0.15, 'height_ratio': 0.15},
                            {'type': 'keyboard', 'label': 'Keyboard', 'y_ratio': 0.45, 'height_ratio': 0.20}
                        ],
                        'measures_per_page': 8,
                        'systems_per_page': 2
                    }
                },
                'publishers': {}
            }
        
        self.presets = self.presets_data['presets']
        self.publishers = self.presets_data['publishers']
        
        # ページ設定
        self.page_width = 595
        self.page_height = 842
        self.margin = 40
    
    def get_preset_list(self):
        """利用可能なプリセットのリストを返す"""
        return [
            {
                'id': preset_id,
                'name': preset['name'],
                'description': preset['description'],
                'instruments': [inst['label'] for inst in preset['instruments']]
            }
            for preset_id, preset in self.presets.items()
        ]
    
    def extract_with_preset(self, pdf_path, preset_id, selected_parts=None, 
                           measures_per_line=None, show_lyrics=False):
        """プリセットを使用して抽出"""
        if preset_id not in self.presets:
            print(f"プリセット '{preset_id}' が見つかりません")
            return None
        
        preset = self.presets[preset_id]
        
        # 選択されたパートがない場合は、プリセットの最初の3つを使用
        if not selected_parts:
            selected_parts = []
            for inst in preset['instruments']:
                if inst['type'] in ['vocal', 'chord', 'keyboard']:
                    selected_parts.append(inst['type'])
                if len(selected_parts) >= 3:
                    break
        
        # 小節数の設定
        if not measures_per_line:
            measures_per_line = preset.get('measures_per_page', 8) // 2
        
        try:
            src_pdf = fitz.open(pdf_path)
            output_pdf = fitz.open()
            
            # 出力パス
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = os.path.join(
                os.path.dirname(pdf_path),
                f"{base_name}_preset_{preset_id}_{measures_per_line}m.pdf"
            )
            
            # 新しいページを作成
            current_page = output_pdf.new_page(width=self.page_width, height=self.page_height)
            current_y = self.margin
            
            # タイトル
            current_page.insert_text(
                (self.margin, current_y),
                f"{preset['name']} - {measures_per_line}小節モード",
                fontsize=14,
                color=(0, 0, 0)
            )
            current_y += 30
            
            # 各ページを処理
            for page_num in range(len(src_pdf)):
                if page_num >= 10:  # 最初の10ページのみ
                    break
                
                print(f"ページ {page_num + 1} を処理中...")
                page = src_pdf[page_num]
                page_rect = page.rect
                
                # プリセットに基づいてシステムを抽出
                systems_extracted = self._extract_systems_with_preset(
                    page, page_num, src_pdf, preset, selected_parts,
                    current_page, current_y, measures_per_line, show_lyrics
                )
                
                current_y = systems_extracted['current_y']
                
                # ページがいっぱいになったら新しいページ
                if systems_extracted.get('need_new_page'):
                    current_page = output_pdf.new_page(
                        width=self.page_width,
                        height=self.page_height
                    )
                    current_y = self.margin
            
            # 保存
            output_pdf.save(output_path)
            print(f"保存完了: {output_path}")
            
            src_pdf.close()
            output_pdf.close()
            
            return output_path
            
        except Exception as e:
            print(f"エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_systems_with_preset(self, page, page_num, src_pdf, preset, 
                                   selected_parts, current_page, current_y,
                                   measures_per_line, show_lyrics):
        """プリセットに基づいてシステムを抽出"""
        page_rect = page.rect
        systems_per_page = preset.get('systems_per_page', 2)
        measures_per_page = preset.get('measures_per_page', 8)
        
        # ページの高さを等分してシステムを配置
        system_height = page_rect.height / systems_per_page
        
        # 各システムを処理
        for system_idx in range(systems_per_page):
            system_top = system_idx * system_height
            system_bottom = (system_idx + 1) * system_height
            
            # 小節グループごとに処理
            measures_per_group = measures_per_line
            num_groups = measures_per_page // measures_per_group
            
            for group_idx in range(num_groups):
                # 新しいページが必要かチェック
                required_height = len(selected_parts) * 50 + 40
                if current_y + required_height > self.page_height - self.margin:
                    return {
                        'current_y': current_y,
                        'need_new_page': True
                    }
                
                # グループラベル
                measure_start = system_idx * measures_per_page + group_idx * measures_per_group + 1
                measure_end = measure_start + measures_per_group - 1
                
                current_page.insert_text(
                    (self.margin, current_y),
                    f"小節 {measure_start}-{measure_end}",
                    fontsize=10,
                    color=(0.5, 0.5, 0.5)
                )
                current_y += 20
                
                # 選択された楽器を抽出
                for inst in preset['instruments']:
                    if inst['type'] not in selected_parts:
                        continue
                    
                    # 楽器の位置を計算
                    inst_y = system_top + (system_height * inst['y_ratio'])
                    inst_height = system_height * inst['height_ratio']
                    
                    # 小節の範囲を計算
                    measure_width = page_rect.width / measures_per_page
                    x_start = group_idx * measures_per_group * measure_width
                    x_end = x_start + (measures_per_group * measure_width)
                    
                    # クリップ領域
                    clip_rect = fitz.Rect(
                        x_start,
                        inst_y - 5,
                        x_end,
                        inst_y + inst_height + 5
                    )
                    
                    # 配置先
                    dest_height = 40
                    if inst['type'] == 'keyboard':
                        dest_height = 50
                    elif inst['type'] == 'chord':
                        dest_height = 30
                    
                    dest_rect = fitz.Rect(
                        self.margin + 60,
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
                        label_color = (0, 0, 0)
                        if inst['type'] == 'chord':
                            label_color = (0, 0.5, 0)
                        
                        current_page.insert_text(
                            (self.margin, current_y + dest_height / 2),
                            inst['label'],
                            fontsize=9,
                            color=label_color
                        )
                        
                        # コードパートの場合は背景を薄く
                        if inst['type'] == 'chord':
                            chord_bg = fitz.Rect(
                                dest_rect.x0 - 2,
                                dest_rect.y0 - 2,
                                dest_rect.x1 + 2,
                                dest_rect.y1 + 2
                            )
                            current_page.draw_rect(
                                chord_bg, 
                                color=(0.9, 1, 0.9), 
                                fill=(0.95, 1, 0.95)
                            )
                            # 再描画
                            current_page.show_pdf_page(
                                dest_rect, src_pdf, page_num, clip=clip_rect
                            )
                        
                    except Exception as e:
                        print(f"  パート配置エラー: {str(e)}")
                    
                    current_y += dest_height + 5
                
                current_y += 15  # グループ間のスペース
        
        return {
            'current_y': current_y,
            'need_new_page': False
        }