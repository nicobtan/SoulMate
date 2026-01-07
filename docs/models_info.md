# SoulMate AI Model Usage / モデル使用状況一覧

SoulMateアプリケーション内で使用されているAIモデルと、それぞれの役割をまとめています。

## 1. Core AI (会話・思考)
| Role | Model ID | Description | Source |
| :--- | :--- | :--- | :--- |
| **Reasoning Engine**<br>(推論・会話) | `gemini-3-flash-preview` | 会話の生成、感情分析、ツール判定、全体的な思考を担うメインエンジン。 | `src/services/ai_engine.py`<br>`src/services/active_engine.py` |
| **Learned Facts**<br>(長期記憶オブザーバー) | `gemini-2.0-flash-exp` | **非同期処理**。会話終了後にバックグラウンドで会話ログを分析し、ユーザーの好みや事実を抽出して保存する。ツール利用（Function Calling）に強いモデルを採用。 | `src/services/ai_engine.py` |

## 2. Voice & Vision (音声・視覚)
| Role | Model ID | Description | Source |
| :--- | :--- | :--- | :--- |
| **TTS (Expressive)**<br>(音声合成) | `gemini-2.5-flash-preview-tts` | 感情表現豊かな音声合成を行う。音声のみの生成に使用。 | `src/services/voice_service.py` |
| **STT (Voice Input)**<br>(音声認識) | `faster-whisper (base)` | **ローカル実行**。ユーザーの音声を高速にテキスト化する。CUDA(GPU)利用時は `float16`、CPU時は `int8` で動作。 | `src/services/voice_input_manager.py` |
| **Local Vision**<br>(画面認識) | `google/paligemma-3b-mix-224` | **ローカル実行 (PaliGemma)**。ユーザーの画面（スクリーンショット）をキャプション（テキスト）化するために使用。軽量で高速。 | `src/services/vision_service.py` |
| **Video Reasoning**<br>(YouTube/Native Vision) | `gemini-3-flash-preview` | 動画ファイルや画像の詳細なコンテキスト理解には、Geminiのネイティブマルチモーダル機能を使用。 | `src/services/ai_engine.py` |

## 3. Sub-Systems (サブシステム)
| Role | Model ID | Description | Source |
| :--- | :--- | :--- | :--- |
| **MindVault Sync**<br>(Google Docs分析) | `gemini-3-flash-preview` | Google Docsのメモを解析し、哲学・引用・感情に分類して長期記憶(MindVault)に同期する。 | `src/services/docs_sync_service.py` |
| **Diary Generator**<br>(日記生成) | `gemini-3-flash-preview` | 昨日の会話ログを読み込み、SoulMate視点での日記を生成する。 | `src/services/diary_generator.py` |
| **Dify Integration**<br>(外部ワークフロー) | *External (Dify)* | 外部のDifyワークフロー（Note記事検索など）を実行。モデルはDify側で設定。 | `src/services/dify_client.py` |

---

## 補足
*   **Gemini 3 Flash Preview**: 高速かつ高度な推論能力を持つため、リアルタイム性が求められる会話や、大量のテキスト処理（日記、ドキュメント同期）に採用しています。
*   **Gemini 2.5 Flash Lite / Pro**: 旧構成で使われていましたが、現在は主に `3-flash` へ移行済みです。TTSのみ `2.5` 系を使用しています。
*   **PaliGemma**: プライバシーと速度を考慮し、画面の常時監視（Proactive Vision）の一次処理はローカルモデルで行っています。
