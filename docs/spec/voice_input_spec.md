# Voice Input Specification (Desktop)

**Phase:** 19 (Desktop Implementation)
**Status:** Draft
**Last Updated:** 2026-01-04

## 1. 概要
SoulMateのデスクトップ版において、ユーザーの音声を認識してテキスト化し、チャット入力欄に自動入力する機能を実装する。
誤認識を考慮し、音声認識結果は即時送信せず、**「入力欄への挿入（Confirmation）」**というフローを採用する。これにより、ユーザーは送信前に誤字を手修正できる。

## 2. 技術スタック選定

### 2.1 音声認識エンジン (STT)
* **採用技術:** **Faster-Whisper** (Local Execution)
    * **選定理由:**
        * **高精度:** OpenAIのWhisperモデルを使用するため、日本語の認識精度が非常に高い。
        * **ローカル完結:** 音声データが外部に送信されず、プライバシーが保護される。
        * **GPU活用:** SoulMateプロジェクトの方針（RTX 50シリーズ対応など）と合致し、GPUがある場合は爆速で動作する。
        * **CPU対応:** `int8` 量子化により、CPUのみでも実用的な速度で動作可能。
    * **ライブラリ:** `faster-whisper`

### 2.2 録音・デバイス制御
* **録音ライブラリ:** `PyAudio`
    * マイクデバイスの列挙、ストリーム録音に使用。
* **ホットキー制御:** `keyboard`
    * グローバルホットキーの検知に使用（ウィンドウが非アクティブでもマイクON/OFFを可能にするため）。

## 3. UI/UX フロー

### 3.1 ユーザー体験フロー
1.  **録音開始**:
    * ユーザーが「マイクボタン」をクリック、または「設定されたホットキー（例: `Right Ctrl`）」を押下。
    * **UI変化**: マイクボタンが「録音中（赤色/波形アニメーション）」に変化。
    * **SE**: 「ピコン」という開始音（オプション）。
2.  **発話**:
    * ユーザーがマイクに向かって話す。
3.  **録音終了**:
    * ボタンを再度クリック、またはホットキーを離す（Push-to-Talk設定時）。
    * **UI変化**: 「認識中...（くるくるアイコン）」を表示。
4.  **テキスト化 & 挿入**:
    * バックエンドで音声認識が完了すると、結果のテキストがフロントエンドに送信される。
    * **チャット入力欄 (`#chat-input`) にテキストが挿入** される。
    * *既存の入力がある場合*: 末尾にスペースを空けて追記する。
5.  **確認 & 送信**:
    * ユーザーが内容を目視確認。誤字があれば手動で修正。
    * `Enter` キーまたは送信ボタンで送信。

### 3.2 画面デザイン
* **メイン画面**:
    * **マイクボタン**: 入力エリア (`#input-area`) の左端、または送信ボタンの横に配置。
    * **ステータス表示**:
        * ⚪ 待機中 (Default)
        * 🔴 録音中 (Recording)
        * 🟡 処理中 (Processing)
* **設定画面 (`settings.html`)**:
    * **Voice Input** タブを新設。

## 4. 設定項目仕様 (`settings.html`)

| 項目名 | UI要素 | 説明 | Config Key |
| :--- | :--- | :--- | :--- |
| **入力デバイス** | セレクトボックス | `PyAudio` で取得したマイクデバイス一覧を表示。 | `audio_input_device_index` |
| **認識モデル** | セレクトボックス | `tiny`, `base`, `small`, `medium`, `large-v3`。<br>※推奨: `base` または `small`。GPUありなら `large` も可。 | `stt_model_size` |
| **演算精度** | セレクトボックス | `int8` (CPU/軽量), `float16` (GPU推奨)。 | `stt_compute_type` |
| **ホットキー** | キー入力フォーム | マイクON/OFFを切り替えるキー。<br>例: `ctrl+space`, `right_ctrl`, `f12`。 | `voice_input_hotkey` |
| **入力モード** | ラジオボタン | **Toggle** (1回押して開始/終了) / **Push-to-Talk** (押している間だけ録音)。 | `voice_input_mode` |

## 5. データフロー & アーキテクチャ

```mermaid
sequenceDiagram
    participant User
    participant Frontend (JS)
    participant Backend (Api Mixin)
    participant VoiceInputManager
    participant FasterWhisper

    User->>Frontend: マイクボタン押下 (or Hotkey)
    Frontend->>Backend: start_recording()
    Backend->>VoiceInputManager: ストリーム録音開始 (PyAudio)
    User->>VoiceInputManager: [音声データ]
    
    User->>Frontend: 停止操作
    Frontend->>Backend: stop_recording()
    Backend->>VoiceInputManager: 録音停止 -> 一時WAV保存
    VoiceInputManager->>FasterWhisper: transcribe(wav_path)
    FasterWhisper-->>VoiceInputManager: テキスト ("こんにちは")
    VoiceInputManager-->>Backend: Result String
    Backend-->>Frontend: on_speech_recognized("こんにちは")
    Frontend->>Frontend: DOM操作: #chat-input.value += "こんにちは"