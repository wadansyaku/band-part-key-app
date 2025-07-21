import os
import shutil
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

class FileHandler:
    """ファイル操作のユーティリティクラス"""
    
    def __init__(self, config):
        self.config = config
        self.upload_folder = config['UPLOAD_FOLDER']
        self.temp_folder = config['TEMP_FOLDER']
        self.allowed_extensions = config['ALLOWED_EXTENSIONS']
        self.retention_minutes = config['FILE_RETENTION_MINUTES']
    
    def allowed_file(self, filename):
        """許可されたファイル拡張子かチェック"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_upload(self, file, file_id, filename):
        """アップロードファイルを保存"""
        # ファイル名を安全な形式に変換
        safe_filename = secure_filename(filename)
        
        # 拡張子が失われた場合は.pdfを追加
        if not safe_filename.endswith('.pdf'):
            safe_filename = safe_filename + '.pdf'
        
        # 保存先ディレクトリを作成
        upload_dir = os.path.join(self.upload_folder, file_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # ファイルパス
        filepath = os.path.join(upload_dir, safe_filename)
        
        # ファイルを保存
        file.save(filepath)
        
        # メタデータを保存
        self._save_metadata(file_id, {
            'original_filename': filename,
            'safe_filename': safe_filename,
            'upload_time': datetime.now().isoformat(),
            'file_size': os.path.getsize(filepath)
        })
        
        return filepath
    
    def get_upload_path(self, file_id):
        """アップロードファイルのパスを取得"""
        upload_dir = os.path.join(self.upload_folder, file_id)
        
        if not os.path.exists(upload_dir):
            return None
        
        # ディレクトリ内の最初のPDFファイルを返す
        for file in os.listdir(upload_dir):
            if file.endswith('.pdf'):
                return os.path.join(upload_dir, file)
        
        return None
    
    def get_output_path(self, output_id):
        """出力ファイルのパスを取得"""
        output_file = f"{output_id}.pdf"
        output_path = os.path.join(self.temp_folder, output_file)
        
        if os.path.exists(output_path):
            return output_path
        
        # _extracted.pdf のパターンも試す
        output_file = f"{output_id}_extracted.pdf"
        output_path = os.path.join(self.temp_folder, output_file)
        
        if os.path.exists(output_path):
            return output_path
        
        return None
    
    def cleanup_old_files(self):
        """古いファイルを削除"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=self.retention_minutes)
        
        # アップロードフォルダのクリーンアップ
        self._cleanup_directory(self.upload_folder, cutoff_time)
        
        # 一時フォルダのクリーンアップ
        self._cleanup_directory(self.temp_folder, cutoff_time)
    
    def _cleanup_directory(self, directory, cutoff_time):
        """指定ディレクトリの古いファイルを削除"""
        if not os.path.exists(directory):
            return
        
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            # ファイルの最終更新時刻を取得
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                
                if mtime < cutoff_time:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            except Exception:
                # エラーが発生した場合はスキップ
                pass
    
    def _save_metadata(self, file_id, metadata):
        """メタデータを保存"""
        import json
        
        metadata_path = os.path.join(self.upload_folder, file_id, 'metadata.json')
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def get_metadata(self, file_id):
        """メタデータを取得"""
        import json
        
        metadata_path = os.path.join(self.upload_folder, file_id, 'metadata.json')
        
        if not os.path.exists(metadata_path):
            return None
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def delete_file(self, file_id):
        """ファイルと関連データを削除"""
        # アップロードディレクトリを削除
        upload_dir = os.path.join(self.upload_folder, file_id)
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        
        # 関連する一時ファイルも削除
        for file in os.listdir(self.temp_folder):
            if file.startswith(file_id):
                os.remove(os.path.join(self.temp_folder, file))