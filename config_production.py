import os
from datetime import timedelta

class ProductionConfig:
    """本番環境用の設定"""
    
    # 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32).hex())
    DEBUG = False
    TESTING = False
    
    # アップロード設定
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    TEMP_FOLDER = os.environ.get('TEMP_FOLDER', 'temp')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # セッション設定
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', 'sessions')
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SECURE = True  # HTTPS必須
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # CORS設定（必要に応じてドメインを制限）
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # ファイルクリーンアップ設定
    CLEANUP_INTERVAL = 3600  # 1時間
    FILE_RETENTION_HOURS = 1  # 1時間後に削除
    FILE_RETENTION_MINUTES = 60  # 60分後に削除

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
        os.makedirs(ProductionConfig.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(ProductionConfig.TEMP_FOLDER, exist_ok=True)
        os.makedirs(ProductionConfig.SESSION_FILE_DIR, exist_ok=True)
        
        # ログ設定
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler(
                'logs/band_part_key.log',
                maxBytes=10240000,
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Band Part Key App startup')
