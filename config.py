import os
from datetime import timedelta

class Config:
    """アプリケーション設定"""
    
    # 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', True)
    
    # ファイルアップロード設定
    UPLOAD_FOLDER = 'uploads'
    TEMP_FOLDER = 'temp'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # セッション設定
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # Celery設定
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # CORS設定
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5000']
    
    # ファイル保持期間（分）
    FILE_RETENTION_MINUTES = 60
    
    # PDF処理設定
    PDF_DPI = 300  # PDF画像変換時のDPI
    PREVIEW_DPI = 150  # プレビュー用の低解像度DPI
    
    @staticmethod
    def init_app(app):
        """アプリケーション初期化時の処理"""
        # 必要なディレクトリを作成
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.TEMP_FOLDER, exist_ok=True)