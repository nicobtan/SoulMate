# SoulMate System Architecture (v0.3)

## 1. Overview
SoulMateは、デスクトップ上でユーザーと対話する「アクティブなAIパートナー」です。
**Gemini API (Native JSON Mode)** を脳として使用し、**Pywebview** (Chromium) でGUIを描画、**Live2D** でキャラクターを表現します。
Pythonのバックエンドがサーバーとして機能し、JavaScriptのフロントエンドと連携して動作します。

## 2. Core Components

### Backend (Python 3.12+)
*   **`main.py`**: エントリーポイント。`webview.create_window` でウィンドウを生成し、`Api` クラスをJSに公開します。
*   **`src/services/ai_engine.py`**: AIロジックの中枢。
    *   **Reasoning**: `gemini-3-flash-preview` を使用して応答を生成。
    *   **TTS**: `gemini-2.5-flash-preview-tts` (またはVoiceService) で音声を生成。
    *   **Output Mode**: **Native JSON Mode** (`response_schema`) により、堅牢なJSON形式で応答を取得します（旧TOON正規表現パースは廃止）。
*   **`src/api/chat_api.py`**: フロントエンドとのブリッジ。
    *   `chat(message)`: ユーザー入力を受け取り、AIエンジンに渡して結果を返します。
    *   `chat_with_vision(mode)`: スクリーンショットまたはクリップボード画像を取得してAIに送ります。
    *   `initialize_persona()`: 起動時にペルソナとユーザープロファイルをロードします。
*   **`src/services/resource_manager.py`**: YAMLファイル（ペルソナ、プロファイル）の読み込みを担当。
*   **`src/services/db_manager.py`**: `sqlite3` によるチャット履歴の永続化。

### Frontend (TypeScript / Vanilla JS)
*   **`src/index.ts`**: フロントエンドのエントリーポイント。
*   **`src/managers/chat_manager.ts`**: チャットUIの制御。メッセージの表示、履歴のロード、自動スクロールなどを担当。
*   **`src/managers/live2d_manager.ts`**: Live2Dモデルの読み込み、モーション再生（感情による表情変化）を担当。

## 3. Data Flow

### Chat Request
1.  **User Input**: フロントエンドで入力 -> `window.pywebview.api.chat(msg)`
2.  **Processing**: `ChatApi.chat()` -> `AIEngine.generate_response()`
3.  **AI Generation**:
    *   Gemini APIへリクエスト送信 (User Message + Context)
    *   レスポンス受信 -> **Native JSON Decode** (Geminiが保証されたJSONを返却)
    *   `response`, `emotion`, `suggestions` を抽出
4.  **TTS**: 生成されたテキストを音声変換 -> `.wav` ファイル保存
5.  **Response**: フロントエンドへJSON返却 `{ text, audio, emotion, suggestions }`
6.  **Rendering**:
    *   メッセージ表示 (Markdown -> HTML)
    *   音声再生 (Backend Server)
    *   Live2Dモーション再生 (Emotionに合わせて変化)

## 4. Key Improvements (v0.3)
*   **Gemini Native JSON Mode**: 出力スキーマ強制により、パースエラーやJSON構文エラーを根絶。
*   **Dual Model Architecture**: 思考モデル(Gemini 3)とTTSモデル(Gemini 2.5)を分離し、処理速度と品質を最適化。
*   **Vision Integration (v2)**: 右クリックによるクリップボード画像送信に対応し、"Win+Shift+S" との連携フローを確立。
*   **Functional Priority**: 情報検索要求に対してGoogle検索を優先使用するルールをSystem Promptに統合。

## 5. Directory Structure
```
SoulMate/
├── main.py                 # Entry Point
├── dist/                   # Compiled Frontend Assets
├── src/
│   ├── api/                # Python API Mixins (Frontend Bridge)
│   ├── services/           # Service Modules (Refactored v0.5)
│   │   ├── core/           # Core Logic (AI, Active, User, Persona)
│   │   ├── voice/          # Audio I/O (TTS, STT, VoiceService)
│   │   ├── vision/         # Visual Perception (VisionService)
│   │   ├── memory/         # Long-term Memory (DB, History, Mind)
│   │   ├── content/        # Content Gen (Bubbles, Topics, Diary)
│   │   └── external/       # Integrations (Google, Dify)
│   ├── managers/           # TypeScript Managers (Frontend)
│   └── index.ts            # Frontend Entry
├── docs/                   # Documentation
└── memory/                 # Chat Logs (SQLite & JSONL)
```
