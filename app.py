from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv

# 環境に応じて設定を選択
load_dotenv()
if os.environ.get('FLASK_ENV') == 'production':
    from config_production import ProductionConfig as Config
else:
    from config import Config

from core.pdf_processor import PDFProcessor
from core.pdf_type_detector import PDFTypeDetector
from core.final_smart_extractor_v17_accurate import FinalSmartExtractorV17Accurate
from core.measure_based_extractor import MeasureBasedExtractor
from core.ai_layout_extractor import AILayoutExtractor, AILayoutError
from utils.file_handler import FileHandler

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

CORS(app, origins=app.config['CORS_ORIGINS'])

# インスタンス化
pdf_processor = PDFProcessor()
pdf_type_detector = PDFTypeDetector()
final_smart_extractor = FinalSmartExtractorV17Accurate()
measure_based_extractor = MeasureBasedExtractor()
file_handler = FileHandler(app.config)
ai_layout_extractor = AILayoutExtractor(app.config)

@app.route('/')
def index():
    """メインページ"""
    return render_template('index_v3.html')

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
    """パートの抽出 - 最終スマート抽出のみ使用"""
    data = request.json
    file_id = data.get('file_id')
    mode = data.get('mode', 'fast')
    margin = int(data.get('margin', 0))
    
    if not file_id:
        return jsonify({'error': 'ファイルIDが指定されていません'}), 400
    
    try:
        filepath = file_handler.get_upload_path(file_id)
        if not filepath:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        if mode == 'ai_precision':
            app.logger.info("AI precision extraction requested")
            try:
                temp_output_path = os.path.join(
                    file_handler.temp_folder,
                    f"{file_id}_ai_precision.pdf"
                )
                ai_result = ai_layout_extractor.extract_parts_pdf(
                    filepath,
                    temp_output_path,
                    margin_px=margin,
                )
                return jsonify({
                    'id': file_id,
                    'output_id': f"{file_id}_ai_precision",
                    'status': 'completed',
                    'mode': 'ai_precision',
                    'ai_confidence': ai_result['confidence'],
                    'parts_extracted': ['vocal', 'keyboard'],
                    'fallback': False
                }), 200
            except AILayoutError as e:
                app.logger.warning(f"AI precision failed, fallback to fast: {e}")
                fallback_message = str(e)
            except Exception as e:
                app.logger.error(f"AI precision error: {e}")
                fallback_message = "AI精度モードでエラーが発生したため高速モードに切り替えました"
        else:
            fallback_message = None

        # 最終スマート抽出V17（正確版：ギター位置回避ロジック付き）を実行
        app.logger.info("Final smart extraction V17 (accurate: with guitar position avoidance logic)")

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
                'parts_extracted': ['vocal_integrated', 'keyboard'],
                'fallback': mode == 'ai_precision',
                'fallback_message': fallback_message
            }), 200
        return jsonify({'error': '抽出に失敗しました'}), 500
        
    except Exception as e:
        app.logger.error(f"Extraction error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'抽出中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/download/<output_id>', methods=['GET'])
def download_result(output_id):
    """抽出結果のダウンロード"""
    try:
        # 一時フォルダから出力ファイルを探す
        output_path = os.path.join(file_handler.temp_folder, f"{output_id}.pdf")
        
        if not os.path.exists(output_path):
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        # ダウンロード用のファイル名を生成
        download_name = f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'ダウンロード中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/preview/<file_id>/<int:page_num>', methods=['GET'])
def get_preview(file_id, page_num):
    """ページプレビューの取得"""
    try:
        filepath = file_handler.get_upload_path(file_id)
        if not filepath:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        # プレビュー画像を生成
        preview_path = pdf_processor.generate_preview(
            filepath,
            page_num,
            file_id=file_id,
            dpi=app.config.get('PREVIEW_DPI', 150)
        )
        
        if preview_path and os.path.exists(preview_path):
            return send_file(preview_path, mimetype='image/png')
        else:
            return jsonify({'error': 'プレビュー生成に失敗しました'}), 500
            
    except Exception as e:
        return jsonify({'error': f'プレビュー取得中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/ai-layout/<file_id>/<int:page_num>', methods=['GET'])
def get_ai_layout(file_id, page_num):
    """AIレイアウト推定の取得"""
    try:
        filepath = file_handler.get_upload_path(file_id)
        if not filepath:
            return jsonify({'error': 'ファイルが見つかりません'}), 404

        layout_result = ai_layout_extractor.extract_layout_for_page(filepath, page_num)
        return jsonify({
            'layout': layout_result.layout
        }), 200
    except AILayoutError as e:
        app.logger.warning(f"AI layout error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"AI layout error: {str(e)}")
        return jsonify({'error': f'AIレイアウト取得中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_files():
    """古いファイルのクリーンアップ"""
    try:
        deleted_count = file_handler.cleanup_old_files()
        return jsonify({
            'status': 'success',
            'deleted_count': deleted_count
        }), 200
    except Exception as e:
        return jsonify({'error': f'クリーンアップ中にエラーが発生しました: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
