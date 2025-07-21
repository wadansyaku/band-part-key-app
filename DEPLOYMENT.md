# Band Part Key App - デプロイメントガイド

## Webサービスとして公開する方法

### 1. Railway.appを使用したデプロイ（推奨）

#### 準備
1. [Railway](https://railway.app)でアカウントを作成
2. GitHubにリポジトリをプッシュ
3. 環境変数を設定

#### デプロイ手順

1. **GitHubリポジトリの準備**
```bash
git init
git add .
git commit -m "Initial deployment"
git remote add origin https://github.com/YOUR_USERNAME/band_part_key_app.git
git push -u origin main
```

2. **Railwayでプロジェクト作成**
- Railway.appにログイン
- "New Project" → "Deploy from GitHub repo"を選択
- リポジトリを選択

3. **環境変数の設定**
Railwayのプロジェクト設定で以下を追加：
```
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

4. **デプロイ**
- GitHubにプッシュすると自動的にデプロイされます

### 2. Herokuを使用したデプロイ

#### 追加ファイルが必要

**Procfile**を作成：
```
web: gunicorn app:app
```

**Aptfile**を作成（Tesseract用）：
```
tesseract-ocr
tesseract-ocr-jpn
```

#### デプロイ手順
```bash
# Heroku CLIをインストール後
heroku create your-app-name
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-apt
heroku buildpacks:add heroku/python
git push heroku main
```

### 3. VPS（Ubuntu）でのデプロイ

#### サーバー設定
```bash
# システムパッケージのインストール
sudo apt update
sudo apt install python3-pip python3-venv nginx tesseract-ocr tesseract-ocr-jpn

# アプリケーションのセットアップ
git clone https://github.com/YOUR_USERNAME/band_part_key_app.git
cd band_part_key_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Nginxの設定
sudo nano /etc/nginx/sites-available/band_part_key
```

**Nginx設定ファイル**：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        client_max_body_size 50M;
    }
}
```

**Systemdサービス**：
```ini
[Unit]
Description=Band Part Key App
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/band_part_key_app
Environment="PATH=/path/to/band_part_key_app/venv/bin"
ExecStart=/path/to/band_part_key_app/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

### 4. セキュリティ対策

#### 必須の対策
1. **HTTPS/SSL証明書**
   - Let's Encryptを使用（無料）
   - Cloudflareを使用（無料SSL付き）

2. **環境変数の管理**
   - SECRET_KEYは必ず変更
   - .envファイルは絶対にコミットしない

3. **ファイルアップロード制限**
   - ファイルサイズ制限（実装済み: 50MB）
   - ファイルタイプ制限（実装済み: PDFのみ）

4. **レート制限**
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(
       app,
       key_func=lambda: request.remote_addr,
       default_limits=["100 per hour"]
   )
   ```

### 5. ドメイン設定

1. **ドメイン購入**
   - お名前.com、Google Domains等

2. **DNS設定**
   - Aレコード: ドメイン → サーバーIP
   - CNAMEレコード: www → ドメイン

3. **SSL証明書**
   ```bash
   # Let's Encryptの場合
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### 6. 監視とメンテナンス

1. **アップタイム監視**
   - UptimeRobot（無料）
   - Pingdom

2. **ログ管理**
   - アプリケーションログの確認
   - Nginxアクセスログの監視

3. **バックアップ**
   - 定期的なコードバックアップ
   - アップロードファイルの管理

### 7. スケーリング考慮事項

1. **パフォーマンス最適化**
   - CDNの使用（静的ファイル）
   - Redis/Memcachedでキャッシュ

2. **ストレージ**
   - AWS S3やCloudinary for PDFs
   - 一時ファイルの定期削除

3. **処理の最適化**
   - 重い処理はバックグラウンドジョブに
   - Celeryの導入を検討

## トラブルシューティング

### よくある問題

1. **Tesseractが見つからない**
   - システムにTesseractをインストール
   - パスを環境変数に設定

2. **メモリ不足**
   - ワーカー数を減らす
   - スワップメモリを増やす

3. **タイムアウト**
   - gunicornのタイムアウトを増やす
   - Nginxのproxy_read_timeoutを調整

## コスト見積もり

### 無料オプション
- Railway: 月$5クレジット無料
- Heroku: 制限付き無料プラン
- Render: 月750時間無料

### 有料オプション
- VPS: 月$5〜（DigitalOcean, Linode）
- AWS EC2: 月$10〜
- 専用サーバー: 月$50〜

## 推奨構成

小規模利用（〜100ユーザー/日）:
- Railway.app または Render
- 無料プラン十分

中規模利用（〜1000ユーザー/日）:
- VPS（2GB RAM以上）
- Nginx + Gunicorn
- CloudflareでCDN

大規模利用（1000+ユーザー/日）:
- AWS/GCP with Auto Scaling
- S3 for storage
- CloudFront for CDN