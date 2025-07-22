# Quick Start Guide

## 1. 最速で試す（5秒）

```bash
# 最終スマート抽出器のテスト実行
python test_final_smart_extractor.py
```

出力ファイルは `outputs/extracted_scores/` に保存されます。

## 2. Webアプリとして起動（1分）

```bash
# 依存関係をインストール
pip install -r requirements.txt

# アプリケーションを起動
python app.py

# ブラウザで開く
# http://localhost:5000
```

## 3. 基本的な使い方

1. **PDFをアップロード**
   - ドラッグ&ドロップまたはファイル選択
   - 最大50MBまで対応

2. **自動処理**
   - PDFタイプを自動検出
   - 4小節固定でスマート抽出
   - ボーカル（コード・メロディ・歌詞一体）とキーボードを分離

3. **ダウンロード**
   - 処理完了後、自動でダウンロード開始
   - ファイルは `outputs/extracted_scores/` にも保存

## 4. 出力管理

```bash
# 抽出済みファイルの一覧表示
python outputs/management.py
```

## 5. トラブルシューティング

- **文字化け**: 日本語表記は英語に変更済み（"小節"→"Measures"）
- **エラー**: `logs/`ディレクトリのログを確認
- **容量**: 50MB以上のPDFは分割してアップロード