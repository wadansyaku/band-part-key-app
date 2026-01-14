import os
from datetime import timedelta

class Config:
    """アプリケーション設定"""
    
    # 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
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

    # AIレイアウト解析設定
    AI_API_KEY = os.environ.get('AI_API_KEY')
    AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1/responses')
    AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4o-mini')
    AI_CONFIDENCE_THRESHOLD = float(os.environ.get('AI_CONFIDENCE_THRESHOLD', 0.6))
    AI_IMAGE_DPI = int(os.environ.get('AI_IMAGE_DPI', 200))
    AI_MAX_PAGES = int(os.environ.get('AI_MAX_PAGES', 10))
    AI_REQUEST_TIMEOUT = int(os.environ.get('AI_REQUEST_TIMEOUT', 60))
    
    @staticmethod
    def init_app(app):
        """アプリケーション初期化時の処理"""
        # 必要なディレクトリを作成
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.TEMP_FOLDER, exist_ok=True)
