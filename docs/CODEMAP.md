# CODEMAP

## アプリケーションの流れ（現状）

### フロントエンド
- `templates/index_v3.html` がメイン画面を提供します。UI はアップロード→解析→抽出の順に進行します。 
- `static/js/app_v2.js` がAPI通信と画面更新を担当します。アップロード、解析結果表示、抽出開始、ダウンロードまでを制御します。 

### バックエンドのエントリポイント
- `app.py`
  - `/` : メインページを表示。
  - `/api/upload` : PDFをアップロードし、`uploads/<file_id>/` に保存。
  - `/api/analyze/<file_id>` : ページ数取得とPDFタイプ検出。
  - `/api/extract` : 高速抽出（FinalSmartExtractorV17Accurate）またはAI精度モードの抽出を実行。
  - `/api/download/<output_id>` : 抽出結果PDFをダウンロード。
  - `/api/preview/<file_id>/<page_num>` : PDFページのプレビュー画像を生成。
  - `/api/ai-layout/<file_id>/<page_num>` : AIレイアウト推定を取得。
  - `/api/cleanup` : 古いファイルのクリーンアップ。

### 主要モジュール
- `core/pdf_processor.py`
  - PDFのページ数取得、ページ抽出、プレビュー画像生成、PDF結合を提供。
- `core/pdf_type_detector.py`
  - テキスト/画像ベースのPDF判定と推奨設定の算出。
- `core/final_smart_extractor_v17_accurate.py`
  - 既存の高速抽出（ボーカル+キーボード）パイプライン。
- `core/ai_layout_extractor.py`
  - AI精度モードのレイアウト推定・bboxクロップ合成。
- `utils/file_handler.py`
  - アップロードファイル保存、メタデータ管理、古いファイルの削除。

### データフロー（高速抽出）
1. `/api/upload` でPDFを保存。
2. `/api/analyze` でページ数とPDFタイプを取得。
3. `/api/extract` で `FinalSmartExtractorV17Accurate.extract_smart_final()` を実行。
4. 抽出PDFは `temp/` にコピーされ、`/api/download` から取得。

## AI精度モード（概要）
- PDFページを画像化し、AIでパート領域のbboxを推定。
- bboxに基づいてクロップしたPDFを合成。
- 失敗時は既存高速抽出へフォールバック。
- AIプレビュー用にbboxオーバーレイとマージンスライダーを提供。
