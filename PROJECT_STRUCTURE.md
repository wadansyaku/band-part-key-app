# Project Structure - Band Part Key App

## Overview
Band Part Key Appは、バンドスコアのPDFから特定のパート（ボーカル、キーボード等）を抽出するWebアプリケーションです。

## Directory Structure

```
band_part_key_app/
├── app.py                    # メインのFlaskアプリケーション
├── config.py                 # 開発環境設定
├── config_production.py      # 本番環境設定
├── requirements.txt          # Pythonパッケージ依存関係
├── Dockerfile               # Dockerコンテナ設定
├── railway.json             # Railway.appデプロイ設定
├── score_presets.json       # 楽譜タイプのプリセット定義
│
├── core/                    # コア機能モジュール
│   ├── __init__.py
│   ├── pdf_processor.py     # 基本的なPDF処理
│   ├── pdf_type_detector.py # PDFタイプ自動検出
│   ├── final_smart_extractor.py # 最終スマート抽出器（メイン）
│   ├── measure_based_extractor.py # 小節ベース抽出
│   ├── chord_extractor.py   # コード記号抽出
│   ├── instrument_detector.py # 楽器位置検出
│   └── [その他の抽出器...]
│
├── utils/                   # ユーティリティモジュール
│   ├── __init__.py
│   ├── file_handler.py      # ファイル操作ユーティリティ
│   └── logger.py            # ロギング設定
│
├── static/                  # 静的ファイル
│   ├── css/
│   │   └── style.css        # アプリケーションスタイル
│   ├── js/
│   │   └── app.js           # フロントエンドJavaScript
│   └── img/                 # 画像ファイル
│
├── templates/               # HTMLテンプレート
│   ├── index.html           # メインページ
│   └── visual_setup.html    # ビジュアル設定ページ
│
├── tests/                   # テストファイル
│   └── *.py                 # 各種テスト
│
├── docs/                    # ドキュメント
│   ├── README.md
│   ├── USAGE.md             # 使用方法
│   └── DEPLOYMENT.md        # デプロイ手順
│
├── outputs/                 # 出力管理（Gitから除外）
│   ├── extracted_scores/    # 抽出されたPDF
│   ├── logs/                # 処理ログ
│   └── management.py        # 出力管理スクリプト
│
├── archive/                 # アーカイブ（Gitから除外）
│   └── test_scripts/        # 開発時のテストスクリプト
│
├── uploads/                 # アップロードファイル（一時）
├── temp/                    # 一時ファイル
├── input_example/          # サンプル入力（Gitから除外）
│
├── .gitignore              # Git除外設定
├── .env.example            # 環境変数のテンプレート
└── PROJECT_STRUCTURE.md    # このファイル
```

## Key Components

### 1. Core Extractors
- **final_smart_extractor.py**: メインの抽出器。4小節固定でボーカル（コード・メロディ・歌詞一体）とキーボードを抽出
- **pdf_type_detector.py**: PDFが画像ベースかテキストベースかを自動検出
- **chord_extractor.py**: Em, F, G7などのコード記号を正確に抽出

### 2. Web Application
- **app.py**: Flask Webアプリケーション
- **templates/index.html**: シンプル化されたUI（自動検出・スマート抽出・4小節固定）
- **static/js/app.js**: フロントエンドロジック

### 3. Configuration
- **config.py**: 開発環境設定
- **config_production.py**: Railway.app用の本番環境設定
- **.env.example**: 環境変数のテンプレート

### 4. Output Management
- **outputs/**: 抽出されたPDFを管理（著作権保護のためGitから除外）
- タイムスタンプ付きファイル名で保存
- 管理スクリプトで一覧表示・クリーンアップ可能

## Security & Privacy

### 機密情報保護
- SECRET_KEYは環境変数で管理
- .envファイルはGitから除外
- デフォルト値は開発環境のみ

### 著作権保護
- PDFファイル、画像ファイルは全てGitから除外
- outputs/ディレクトリは完全に除外
- input_example/もGitから除外

## Development Guidelines

### コーディング規約
- Python: PEP 8準拠
- 日本語コメントOK（ただし英語推奨）
- エラーハンドリングを適切に実装

### テスト
- テストファイルはarchive/に移動済み
- 新機能追加時はテストを作成

### デプロイ
- Railway.appでの自動デプロイ対応
- Dockerfileで環境を標準化
- config_production.pyで本番環境設定

## Usage

1. **ローカル開発**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

2. **PDFアップロード**
   - ブラウザで http://localhost:5000 にアクセス
   - PDFをアップロード
   - 自動で4小節ごとに抽出

3. **出力確認**
   ```bash
   python outputs/management.py
   ```

## Notes

- 最新の実装では自動検出・スマート抽出・4小節固定がデフォルト
- ボーカルパートはコード・メロディ・歌詞を一体化
- 日本語の文字化けを避けるため、英語表記を使用（"Measures"など）