# Python 3.11をベースイメージとして使用
FROM python:3.11-slim

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-jpn \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# Pythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# アップロード用ディレクトリを作成
RUN mkdir -p uploads temp

# ポート番号を環境変数として設定
ENV PORT=8080

# アプリケーションを起動
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app