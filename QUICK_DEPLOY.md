# 🚀 最速デプロイ手順（5分で完了）

## ステップ1: GitHubにアップロード（2分）

1. **GitHubにログイン**
   - https://github.com にアクセス
   - ログイン（アカウントがない場合は作成）

2. **新しいリポジトリを作成**
   - 右上の「+」→「New repository」をクリック
   - Repository name: `band-part-key-app`
   - Public を選択
   - 「Create repository」をクリック

3. **コードをプッシュ**
   以下のコマンドをターミナルで実行：
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/band-part-key-app.git
   git branch -M main
   git push -u origin main
   ```
   ※ YOUR_USERNAMEをあなたのGitHubユーザー名に置き換えてください

## ステップ2: Railway.appでデプロイ（3分）

1. **Railway.appにアクセス**
   - https://railway.app を開く
   - 「Login with GitHub」でログイン

2. **新プロジェクト作成**
   - 「New Project」をクリック
   - 「Deploy from GitHub repo」を選択
   - `band-part-key-app`リポジトリを選択

3. **環境変数の設定**
   - プロジェクトが作成されたら「Variables」タブをクリック
   - 「+ New Variable」をクリック
   - 以下を追加：
     - Name: `SECRET_KEY`  
       Value: `my-super-secret-key-12345`
     - Name: `FLASK_ENV`  
       Value: `production`

4. **デプロイ完了を待つ**
   - 自動的にビルドが始まります
   - 約2-3分でデプロイ完了
   - 「Settings」タブでURLを確認

## ✅ 完了！

あなたのアプリが公開されました！
URLは以下のような形式になります：
`https://band-part-key-app-production.up.railway.app`

## 📱 動作確認

1. URLにアクセス
2. PDFファイルをアップロード
3. 4小節/8小節モードを試す

## 🎉 おめでとうございます！

Webサービスの公開が完了しました。
友達や仲間と共有してください！

---

## トラブルシューティング

### ビルドエラーが出る場合
- Dockerfileが正しくコミットされているか確認
- requirements.txtが正しいか確認

### アクセスできない場合
- Railwayのログを確認
- 環境変数が正しく設定されているか確認

### PDFが処理されない場合
- 50MB以下のPDFか確認
- Railwayのメモリ使用量を確認