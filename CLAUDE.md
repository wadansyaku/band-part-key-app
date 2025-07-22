# Claude Code プロジェクト情報

このファイルは、Claude Codeがこのプロジェクトについて理解すべき重要な情報を含んでいます。

## プロジェクト概要

バンドスコアPDFから特定の楽器パート（ボーカル＋キーボード）を抽出するWebアプリケーション。

## 主な問題と解決策

### 1. キーボードパート誤検出問題
- **問題**: キーボードパートがギター/ベース/ボーカルとして誤検出される
- **解決**: V17で実装したギター位置回避ロジック（`final_smart_extractor_v17_accurate.py`）

### 2. 空の出力問題
- **問題**: V15で抽出結果が空になる
- **解決**: V16で`show_pdf_page()`メソッドを使用した実コンテンツ転送を実装

## 現在の状態

- **使用中のエクストラクター**: `FinalSmartExtractorV17Accurate`
- **UI**: `index_v2.html`（改善されたモダンUI）
- **PDFタイプ検出**: 実装済みだが抽出プロセスでは未使用

## テスト方法

1. バンドスコアPDFを以下に配置:
   - `test_scores/originals/` - 通常のスコア
   - `test_scores/problematic/` - 問題のあるスコア

2. バッチテストを実行:
   ```bash
   python scripts/test_batch_extraction.py
   ```

## 注意事項

- オリジナルのバンドスコアPDFは`.gitignore`で除外されており、GitHubにはアップロードされません
- 著作権保護のため、PDFファイルは個人使用の範囲でのみテストしてください

## コマンド

開発時に実行すべきコマンド:
- `python app.py` - アプリケーション起動
- `python scripts/test_batch_extraction.py` - バッチテスト実行

## 重要なファイル

- `core/final_smart_extractor_v17_accurate.py` - 最新のエクストラクター
- `templates/index_v2.html` - 改善されたUI
- `test_scores/README.md` - テストスコアの配置方法