from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

import os

# 環境に応じて設定を選択
if os.environ.get('FLASK_ENV') == 'production':
    from config_production import ProductionConfig as Config
else:
    from config import Config
from core.pdf_processor import PDFProcessor
from core.precise_extractor import PreciseExtractor
from core.measure_based_extractor import MeasureBasedExtractor
from utils.file_handler import FileHandler

# オプショナルなインポート（エラーを防ぐ）
try:
    from core.preset_extractor import PresetExtractor
    preset_extractor = PresetExtractor()
except Exception as e:
    print(f"Warning: PresetExtractor could not be loaded: {e}")
    preset_extractor = None

try:
    from core.integrated_vocal_extractor import IntegratedVocalExtractor
    integrated_vocal_extractor = IntegratedVocalExtractor()
except Exception as e:
    print(f"Warning: IntegratedVocalExtractor could not be loaded: {e}")
    integrated_vocal_extractor = None

try:
    from core.image_based_extractor import ImageBasedExtractor
    image_extractor = ImageBasedExtractor()
except Exception as e:
    print(f"Warning: ImageBasedExtractor could not be loaded: {e}")
    image_extractor = None

try:
    from core.pdf_type_detector import PDFTypeDetector
    pdf_type_detector = PDFTypeDetector()
except Exception as e:
    print(f"Warning: PDFTypeDetector could not be loaded: {e}")
    pdf_type_detector = None

try:
    from core.fast_image_extractor import FastImageExtractor
    fast_extractor = FastImageExtractor()
except Exception as e:
    print(f"Warning: FastImageExtractor could not be loaded: {e}")
    fast_extractor = None

try:
    from core.practical_extractor import PracticalExtractor
    practical_extractor = PracticalExtractor()
except Exception as e:
    print(f"Warning: PracticalExtractor could not be loaded: {e}")
    practical_extractor = None

try:
    from core.final_smart_extractor import FinalSmartExtractor
    final_smart_extractor = FinalSmartExtractor()
except Exception as e:
    print(f"Warning: FinalSmartExtractor could not be loaded: {e}")
    final_smart_extractor = None

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

CORS(app, origins=app.config['CORS_ORIGINS'])

# インスタンス化
pdf_processor = PDFProcessor()
precise_extractor = PreciseExtractor()
measure_based_extractor = MeasureBasedExtractor()
file_handler = FileHandler(app.config)

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """PDFファイルのアップロード"""
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    if not file_handler.allowed_file(file.filename):
        return jsonify({'error': 'PDFファイルのみアップロード可能です'}), 400
    
    try:
        # ユニークなIDを生成
        file_id = str(uuid.uuid4())
        
        # ファイルを保存
        filename = secure_filename(file.filename)
        app.logger.info(f"Uploading file: {file.filename} -> {filename}")
        filepath = file_handler.save_upload(file, file_id, filename)
        app.logger.info(f"Saved file to: {filepath}")
        
        # 基本的な解析を実行
        page_count = pdf_processor.get_page_count(filepath)
        
        return jsonify({
            'id': file_id,
            'filename': filename,
            'page_count': page_count,
            'upload_time': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'アップロード中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/analyze/<file_id>', methods=['GET'])
def analyze_score(file_id):
    """楽譜の解析"""
    try:
        filepath = file_handler.get_upload_path(file_id)
        app.logger.info(f"Analyzing file_id: {file_id}, filepath: {filepath}")
        
        if not filepath:
            app.logger.error(f"File not found for file_id: {file_id}")
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        # 簡易解析（ページ数のみ）
        page_count = pdf_processor.get_page_count(filepath)
        
        # PDFタイプの自動検出
        pdf_type_info = None
        extraction_recommendation = None
        
        if pdf_type_detector:
            try:
                analysis_result = pdf_type_detector.analyze_for_extraction(filepath)
                pdf_type_info = analysis_result['pdf_type']
                extraction_recommendation = analysis_result['extraction_config']
                app.logger.info(f"PDF type detected: {pdf_type_info['type']}")
            except Exception as e:
                app.logger.warning(f"PDF type detection failed: {e}")
        
        return jsonify({
            'id': file_id,
            'analysis': {
                'page_count': page_count,
                'has_content': True,
                'pdf_type': pdf_type_info,
                'extraction_recommendation': extraction_recommendation
            }
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error analyzing file: {str(e)}")
        return jsonify({'error': f'解析中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/extract', methods=['POST'])
def extract_parts():
    """パートの抽出"""
    data = request.json
    file_id = data.get('file_id')
    selected_pages = data.get('selected_pages', [])
    extract_mode = data.get('mode', 'full_page')  # 'full_page', 'part_only', or 'smart'
    selected_parts = data.get('selected_parts', ['vocal', 'chord', 'keyboard'])  # スマートモード用
    measures_per_line = data.get('measures_per_line', 4)  # デフォルトを4に変更
    show_lyrics = data.get('show_lyrics', False)  # 歌詞表示オプション
    score_preset = data.get('score_preset', '')  # プリセット選択
    integrated_vocal = data.get('integrated_vocal', False)  # 統合ボーカル抽出
    use_image_based = data.get('use_image_based', False)  # 画像ベース抽出
    use_final_smart = data.get('use_final_smart', True)  # 最終スマート抽出（デフォルトTrue）
    
    if not file_id:
        return jsonify({'error': 'ファイルIDが指定されていません'}), 400
    
    try:
        filepath = file_handler.get_upload_path(file_id)
        if not filepath:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        # 最終スマート抽出モード（デフォルト）
        if use_final_smart and final_smart_extractor:
            app.logger.info("Final smart extraction mode (auto-detect, 4 measures, integrated vocal)")
            
            output_path = final_smart_extractor.extract_smart_final(filepath)
            
            if output_path and os.path.exists(output_path):
                temp_output_path = os.path.join(file_handler.temp_folder, f"{file_id}_final_smart.pdf")
                import shutil
                shutil.copy2(output_path, temp_output_path)
                
                return jsonify({
                    'id': file_id,
                    'output_id': f"{file_id}_final_smart",
                    'status': 'completed',
                    'mode': 'final_smart',
                    'parts_extracted': ['vocal_integrated', 'keyboard']
                }), 200
        
        # 画像ベース抽出モード（実用的抽出器を使用）
        elif use_image_based and practical_extractor:
            app.logger.info("Practical extraction mode")
            
            # selected_partsの形式を変換
            practical_parts = []
            for part in selected_parts:
                if part.lower() == 'vocal':
                    practical_parts.append('Vocal')
                elif part.lower() == 'keyboard':
                    practical_parts.append('Keyboard')
                elif part.lower() == 'chord':
                    practical_parts.append('Chord')
            
            output_path = practical_extractor.extract_practical(
                filepath,
                measures_per_line,
                practical_parts,
                show_lyrics
            )
            
            if output_path and os.path.exists(output_path):
                temp_output_path = os.path.join(file_handler.temp_folder, f"{file_id}_image.pdf")
                import shutil
                shutil.copy2(output_path, temp_output_path)
                
                return jsonify({
                    'id': file_id,
                    'output_id': f"{file_id}_image",
                    'status': 'completed',
                    'mode': 'image_based',
                    'parts_extracted': selected_parts
                }), 200
        
        # プリセットモード
        if score_preset and preset_extractor:
            app.logger.info(f"Preset extraction mode: {score_preset}")
            
            output_path = preset_extractor.extract_with_preset(
                filepath,
                score_preset,
                selected_parts,
                measures_per_line,
                show_lyrics
            )
            
            if output_path and os.path.exists(output_path):
                temp_output_path = os.path.join(file_handler.temp_folder, f"{file_id}_preset.pdf")
                import shutil
                shutil.copy2(output_path, temp_output_path)
                
                return jsonify({
                    'id': file_id,
                    'output_id': f"{file_id}_preset",
                    'status': 'completed',
                    'mode': 'preset',
                    'preset': score_preset,
                    'parts_extracted': selected_parts
                }), 200
        
        # 統合ボーカルモード
        elif integrated_vocal and 'vocal' in selected_parts and integrated_vocal_extractor:
            app.logger.info("Integrated vocal extraction mode")
            
            output_path = integrated_vocal_extractor.extract_vocal_parts(
                filepath,
                measures_per_line,
                include_chords='chord' in selected_parts,
                include_lyrics=show_lyrics,
                pages_to_extract=selected_pages if selected_pages else None
            )
            
            if output_path and os.path.exists(output_path):
                temp_output_path = os.path.join(file_handler.temp_folder, f"{file_id}_vocal.pdf")
                import shutil
                shutil.copy2(output_path, temp_output_path)
                
                return jsonify({
                    'id': file_id,
                    'output_id': f"{file_id}_vocal",
                    'status': 'completed',
                    'mode': 'integrated_vocal',
                    'parts_extracted': selected_parts
                }), 200
        
        elif extract_mode == 'smart':
            # スマート抽出モード（ベース除外、小節揃え）
            app.logger.info(f"Smart extraction mode with parts: {selected_parts}")
            
            # 小節ベース抽出を使用
            output_path = measure_based_extractor.extract_parts(
                filepath, 
                selected_parts,
                selected_pages if selected_pages else None,
                measures_per_line=measures_per_line,
                show_lyrics=show_lyrics
            )
            
            if output_path and os.path.exists(output_path):
                # 一時フォルダにコピー
                temp_output_path = os.path.join(file_handler.temp_folder, f"{file_id}_smart.pdf")
                import shutil
                shutil.copy2(output_path, temp_output_path)
                
                return jsonify({
                    'id': file_id,
                    'output_id': f"{file_id}_smart",
                    'status': 'completed',
                    'mode': 'smart',
                    'parts_extracted': selected_parts
                }), 200
            else:
                # スマート抽出に失敗した場合は通常の抽出にフォールバック
                app.logger.warning("Smart extraction failed, falling back to full page mode")
                extract_mode = 'full_page'
        
        elif extract_mode == 'part_only':
            # パート抽出モードはスマートモードに統合
            app.logger.info(f"Part only mode: extracting keyboard only")
            selected_parts = ['keyboard']  # キーボードのみ
            
            # 小節ベース抽出を使用
            output_path = measure_based_extractor.extract_parts(
                filepath, 
                selected_parts,
                selected_pages if selected_pages else None,
                measures_per_line=measures_per_line,
                show_lyrics=show_lyrics
            )
            
            if output_path and os.path.exists(output_path):
                # 一時フォルダにコピー
                temp_output_path = os.path.join(file_handler.temp_folder, f"{file_id}_parts.pdf")
                import shutil
                shutil.copy2(output_path, temp_output_path)
                
                return jsonify({
                    'id': file_id,
                    'output_id': f"{file_id}_parts",
                    'status': 'completed',
                    'mode': 'part_only',
                    'parts_extracted': selected_parts
                }), 200
            else:
                return jsonify({'error': 'キーボードパートの抽出に失敗しました'}), 500
        
        if extract_mode == 'full_page':
            # 従来の方法：ページ全体を抽出
            output_path = pdf_processor.extract_pages(filepath, selected_pages, file_id)
            
            return jsonify({
                'id': file_id,
                'output_id': os.path.basename(output_path).replace('.pdf', ''),
                'status': 'completed',
                'mode': 'full_page'
            }), 200
        
    except Exception as e:
        return jsonify({'error': f'抽出中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/download/<output_id>', methods=['GET'])
def download_file(output_id):
    """処理済みファイルのダウンロード"""
    try:
        filepath = file_handler.get_output_path(output_id)
        if not filepath or not os.path.exists(filepath):
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=f'keyboard_part_{output_id}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'ダウンロード中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/search_custom_parts', methods=['POST'])
def search_custom_parts():
    """カスタムキーワードでパートを検索"""
    data = request.json
    file_id = data.get('file_id')
    keywords = data.get('keywords', [])
    
    if not file_id or not keywords:
        return jsonify({'error': 'ファイルIDとキーワードが必要です'}), 400
    
    try:
        filepath = file_handler.get_upload_path(file_id)
        if not filepath:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        # カスタムキーワードで検索
        matching_pages = score_analyzer.search_by_keywords(filepath, keywords)
        
        return jsonify({
            'matching_pages': matching_pages,
            'keywords': keywords
        }), 200
        
    except Exception as e:
        app.logger.error(f"Custom search error: {str(e)}")
        return jsonify({'error': f'検索中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/preview/<file_id>/<int:page>', methods=['GET'])
def preview_page(file_id, page):
    """特定ページのプレビュー画像を返す"""
    try:
        filepath = file_handler.get_upload_path(file_id)
        if not filepath:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        # ページをプレビュー用画像に変換
        preview_path = pdf_processor.generate_preview(filepath, page, file_id)
        
        return send_file(preview_path, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'error': f'プレビュー生成中にエラーが発生しました: {str(e)}'}), 500

@app.errorhandler(413)
def file_too_large(e):
    """ファイルサイズエラー"""
    return jsonify({'error': 'ファイルサイズが大きすぎます（最大50MB）'}), 413

if __name__ == '__main__':
    app.run(debug=True, port=5003)