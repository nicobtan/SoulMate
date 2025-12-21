# SoulMate System Architecture (v0.2.1)

## 1. Overview
SoulMateは、デスクトップ上でユーザーと対話する「アクティブなAIパートナー」です。
**Gemini API** を脳として使用し、**Pywebview** (Chromium) でGUIを描画、**Live2D** でキャラクターを表現します。
Pythonのバックエンドがサーバーとして機能し、JavaScriptのフロントエンドと連携して動作します。

## 2. Core Components

### Backend (Python 3.12+)
*   **`main.py`**: エントリーポイント。`webview.create_window` でウィンドウを生成し、`Api` クラスをJSに公開します。
*   **`src/services/ai_engine.py`**: AIロジックの中枢。
    *   **Reasoning**: `gemini-3-flash-preview` を使用して応答を生成。
    *   **TTS**: `gemini-2.5-flash-preview-tts` (またはVoiceService) で音声を生成。
    *   **Parsing**: 生のテキストレスポンスからTOON形式 (`text:`, `emotion:`) を正規表現で抽出します。
*   **`src/api/chat_api.py`**: フロントエンドとのブリッジ。
    *   `chat(message)`: ユーザー入力を受け取り、AIエンジンに渡して結果を返します。
    *   `initialize_persona()`: 起動時にペルソナとユーザープロファイルをロードします。
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
    *   レスポンス受信 -> 正規表現パース (Implicit Text Mode)
    *   `text`, `emotion`, `suggestions` を抽出
4.  **TTS**: 生成されたテキストを音声変換 -> `.wav` ファイル保存
5.  **Response**: フロントエンドへJSON返却 `{ text, audio, emotion, suggestions }`
6.  **Rendering**:
    *   メッセージ表示 (Markdown -> HTML)
    *   音声再生 (Backend Server)
    *   Live2Dモーション再生 (Emotionに合わせて変化)

## 4. Key Improvements (Current State)
*   **Dual Model Architecture**: 思考モデル(Gemini 3)とTTSモデル(Gemini 2.5)を分離し、処理速度と品質を最適化。
*   **Robust Parsing (Implicit Text Mode)**: `text:` ラベルが欠落しても、メタデータ (`emotion:` 等) を避けて本文を抽出するロジックを実装済み。
*   **Functional Priority**: (※ロールバックにより現在は未実装。再実装予定)

## 5. Directory Structure
```
SoulMate/
├── main.py                 # Entry Point
├── dist/                   # Compiled Frontend Assets
├── src/
│   ├── api/                # Python API Mixins
│   ├── services/           # Business Logic (AI, DB, Voice)
│   ├── managers/           # TypeScript Managers (Frontend)
│   └── index.ts            # Frontend Entry
├── docs/                   # Documentation
└── memory/                 # Chat Logs (SQLite & JSONL)
```
