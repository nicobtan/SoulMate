# コマンド・スクリプト一覧

SoulMateプロジェクトで使用する主要なコマンドとスクリプトのまとめです。

## 🚀 起動 (Startup)

### アプリケーション起動 (通常)
WebサーバーとGUI(pywebview)を同時に起動します。
PowerShellの場合は `.\` をつけて実行してください。
```bat
.\run.bat
```
(Command Promptなら `run.bat` だけでOK)

または
```bash
python main.py
```

### サーバーのみ起動 (開発・スマホ連携用)
GUIを起動せず、Webサーバー(FastAPI)のみを起動します。
既存のPythonプロセスを停止してから起動するため、ポート競合の解消にも役立ちます。
```bat
.\server_start.bat
```
または
```bash
python server.py
```

## 🛠️ 環境構築・更新 (Setup & Update)

### Pythonライブラリのインストール
`requirements.txt` に記載された依存関係をインストールします。
```bash
pip install -r requirements.txt
```

### Node.jsライブラリのインストール
フロントエンド開発に必要なパッケージをインストールします。
```bash
npm install
```

## 📦 ビルド (Build)

### フロントエンドのビルド
TypeScriptをコンパイルし、HTML/CSSなどを `dist` フォルダに出力します。
画面表示がおかしい場合や、TypeScriptを変更した後は必ず実行してください。
```bash
npm run build
```

## 🔧 ユーティリティ (Utility)

### 音声合成テスト
TTSの動作確認を行います。
```bash
python tts_test.py
```

### フィラー音声生成
待機時の相槌モーションと音声を生成・更新します。
```bash
python generate_fillers.py
```
