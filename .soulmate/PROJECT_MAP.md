# PROJECT_MAP.md

## 概要
SoulMateは、ユーザーのデスクトップに常駐し、Live2Dモデルを通じて能動的にコミュニケーションを行うAIエージェントアプリです。
`pywebview` と `FastAPI` を組み合わせ、フロントエンドは `Vanilla TypeScript` を用いたアーキテクチャで構成されています。

## ディレクトリ構造と役割

### 🚀 ルートディレクトリ
- **`main.py`**: アプリケーションのエントリーポイント (`pywebview` を起動し、GUIとして実行)。
- **`server.py`**: FastAPIサーバーのエントリーポイント (バックエンドAPIとして独立動作も可能)。

### 💻 `src/` (ソースコード中核)
フロントエンドとバックエンドのコードが混在していますが、主に以下のように分かれています。

#### バックエンド (Python)
- **/api**: `pywebview` 経由でフロントエンドから呼び出される API Mixin クラス (`chat_api.py`, `voice_api.py` 等)。
- **/core**: システムのコアロジック (`config_manager.py`, `response_parser.py` 等)。
- **/routers**: FastAPI 用のルーター定義 (`chat.py`, `settings.py` 等)。
- **/services**: ドメインごとのビジネスロジック (`content`, `control`, `memory`, `voice`, `vision` など細分化されています)。
- **/utils**: 汎用ユーティリティ (`time_utils.py` 等)。

#### フロントエンド (TypeScript / HTML / CSS)
- **`index.html`, `settings.html`, `history.html`**: UIのエントリーポイント。
- **`index.ts`, `settings.ts`, `history.ts`**: 各画面のメインスクリプト。
- **/managers**: TypeScript側のコアロジック (`chat_manager.ts`, `live2d_manager.ts`, `ui_manager.ts` 等)。
- **/css**: スタイルシート (`style.css`, `mobile.css`)。
- **/types**: TypeScriptの型定義ファイル。

### 📁 その他の主要ディレクトリ
- **/settings**: 設定ファイル (`user_profile.yaml`, `MindVault.md`, `quick_messages.json` 等)。エージェントのプロンプトや知識ベース。
- **/profiles**: キャラクターのプロフィール定義 (`characters.json` 等)。
- **/assets**: 音声のフィラー(`thinking_02.wav` 等)やカーソルなどのアセット。
- **/docs**: プロジェクトのドキュメント、仕様書、タスクリスト (`docs/spec/`, `docs/prompt/` 等)。
- **/Live2D**: Live2Dのモデルデータ (`naya`, `fav_usaneko_alwb` 等)。
- **/gui**: ウィンドウやGUI制御ロジック (`controller.py` 等)。
- **/tests**: テストコード。
- **/tools**: 開発用・デバッグ用のスクリプト群。
- **/.soulmate**: エージェント自身のためのメタ知識とルール定義 (`GEMINI.md`, `MANAGEMENT_STRATEGY.md` 等)。
