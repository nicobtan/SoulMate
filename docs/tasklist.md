# デスクトップマスコット開発 タスクリスト

## フェーズ1: 基本的なウィンドウの構築
- [x] Pythonの仮想環境を構築する
- [x] `pywebview` ライブラリをインストールする (`pip install pywebview`)
- [x] `main.py` を作成し、基本的なWebViewウィンドウを表示するコードを記述する
- [x] ウィンドウをフレームレス（枠なし）に設定する
- [x] ウィンドウの背景を透過させる
- [x] ウィンドウを常に最前面に表示する設定を追加する
- [x] HTML側（`index.html`）のCSS/JavaScriptで、ウィンドウ全体をドラッグして移動できる機能を実装する

## フェーズ2: キャラクター表示 (静止画Ver)
- [x] 仮のキャラクター画像 (`images/naya_test.png`) を用意する
- [x] `src/index.html` を修正し、`naya_test.png` を正しく表示する
- [x] TypeScriptビルド環境を整備する (`tsconfig.json` の修正)

## フェーズ3: カスタムコンテキストメニューの実装
- [x] `src/index.html` に、メニューの元となるHTML要素を記述する
- [x] CSSでメニューの見た目を整える
- [x] TypeScript (`src/index.ts`) で右クリックイベントを実装する
- [x] ビルドを実行し、Python連携して「終了」機能が動くことを確認する

## フェーズ4: Live2Dモデルの表示
- [x] Live2D Cubism SDK / PixiJS の導入
- [x] モデルデータの配置 (`dist/models`)
- [x] `index.ts` でのモデルロードと表示処理の実装
- [x] 動作確認（アニメーション、背景透過）

---

## フェーズ5: UI拡張 (チャットインターフェース)
- [x] **レイアウト構築** (HTML/CSS)
    - [x] 画面分割: [キャラ(500x500)] + [チャット]
    - [x] **デザイン調整**:
        - [x] キャラクター枠の完全透過
        - [x] キャラクターの拡大表示 (Zoomed Default)
    - [x] **チャット表示ボタン**の実装:
        - [x] キャラクター枠右上に配置
        - [x] アクティブ時(チャット表示中)は緑色に変更
    - [x] チャットログエリアの実装 (右側, トグル式)
    - [x] メッセージ入力欄の実装
- [x] **設定画面の実装** (独立ウィンドウ)
    - [x] フォントサイズ設定機能
    - [x] 背景透明度設定機能
    - [x] 設定画面の独立ウィンドウ化
- [x] **操作機能の実装** (TypeScript)
    - [x] `Ctrl` + ホイールでの Live2D モデル拡大縮小ロジック
    - [x] チャットログのテキスト選択・コピー機能
    - [ ] **通知・強調表示機能**
        - [ ] 未読メッセージ管理ロジック
        - [ ] 新着時のスタイル変更 (CSS animation)
- [ ] **双方向通信**
    - [ ] Python (PyWebView) - JavaScript間の双方向通信 (文字データ受渡)

## フェーズ6: "Brain" の実装 (Gemini API) [完了]
- [x] Gemini APIキーのセキュアな管理 (ConfigManager)
- [x] チャットボットロジックの実装
    - [x] ユーザー入力の受け取り
    - [x] AIEngineの実装 (`google-generativeai`)
    - [x] APIからの応答取得と表示
    - [x] モデル自動修復機能 (非推奨モデルからの移行)

## フェーズ7: 知能強化 (RAG & ペルソナロジック)
- [x] **AIエンジン改修 (`src/ai_engine.py`)** -> *(完了)*
    - [x] `SoulMateProfile` (TS風) プロンプト構築ロジックの実装
    - [x] 音声用出力制約 ("絵文字/記号禁止", "短文") の適用
- [x] **ペルソナ・プロファイル管理** -> *(完了)*
    - [x] `test_persona/default.yaml` 作成
    - [x] `src/persona_manager.py` 実装 (YAMLロード)
    - [x] `main.py` & `src/settings.ts` 連携
- [ ] **モデル切り替えロジックの実装**
    - [ ] 通常会話: `gemini-2.5-flash-lite`
    - [ ] 複雑な相談: `gemini-3.0-preview`
- [x] **記憶システム (RAG)**
    - [x] `logs/chat_history.jsonl` への永続化
    - [x] `chromadb` の統合と検索ロジック
    - [x] 検証（スクリプト実行とロジック確認済み）

## フェーズ7.5: UI改善と可観測性 [完了]
- [x] **メイン画面UIのレイアウト変更**
    - [x] **チャットボタン移動**: 画面右下に移動 (緑色)
    - [x] **デバッグログ表示機能**:
        - [x] ログ表示ボタン追加 (右下, 黄色)
        - [x] システムログ表示エリアの実装 (左側に展開, ウィンドウ位置自動調整)
    - [x] **時計表示**: 左下にデザインされた時計を追加 (配置調整済)
    - [x] **ステータスバー**: キャラクター腰付近にAIの状態を表示 (配置調整済)

## フェーズ8: 音声と動き (TTS & Motion) [完了]
- [x] **Google Cloud TTS API 導入**
    - [x] ライブラリ導入 (`google-cloud-texttospeech`)
    - [x] 認証情報の設定 (GOOGLE_APPLICATION_CREDENTIALS)
    - [x] `src/tts_engine.py` 実装 (パラメータ: `Neural2-B`, `pitch=2.0`, `rate=1.1`)
- [x] **設定画面の拡張**
    - [x] 音声選択機能 (Neural2-B, Standard-A/B 等のドロップダウン)
- [x] **音声再生 & リップシンク**
    - [x] Python: 音声データ生成 -> frontendへ送信 (base64 or file)
    - [x] Frontend: `AudioContext` + `AnalyserNode` によるリップシンク (`ParamMouthOpenY`)
- [x] **感情表現モーション**
    - [x] AI応答からの感情タグ検出とLive2Dモーション連携

## フェーズ9: 能動的アクション & ニュース分析 (Active Intellect) [完了]
- [x] **News Collector (情報収集)**
    - [x] `feedparser` 導入とRSSリスト定義
    - [x] 定期実行スクリプト (バックグラウンド処理) の実装
- [x] **アナリストエンジン (Gemini 3.0 Preview)**
    - [x] 記事テキストを読み込み、`NewsTopic` 形式に変換するプロンプト実装
    - [x] 分析結果を一時メモリ (`current_news_cache`) に保存 (Direct Push 実装済み)
- [x] **能動的対話トリガー**
    - [x] アイドル状態(無操作)を検知するタイマーの実装
    - [x] トリガー発動時、`short_hook` を使ってAIから話しかける処理
    - [x] 詳細解説フロー: ユーザーが興味を示した場合、`summary` を読み上げる分岐処理

## フェーズ9.5: UI/UXの洗練 (Polishing)
- [x] **チャット入力欄の改善**
    - [x] `textarea` 化による複数行入力対応
    - [x] `Shift+Enter` で改行、`Enter` で送信のロジック実装
- [x] **ログ表示のクリーンアップ**
    - [x] 起動時のデバッグメッセージ削除
    - [x] **タイムスタンプ追加**: メッセージに `HH:MM` を表示
- [x] **スタイリング調整**
    - [x] 送信ボタンのサイズ縮小 (30px)
    - [x] 初期ステータスを "Idle" に変更
- [x] **リップシンク調整 (v2.0)**
    - [x] Lerp (線形補間) によるスムージング処理
    - [x] 感度調整 (RMS Like ロジック)

## フェーズ10: 外部連携 (Googleカレンダー)
- [x] **ライブラリの導入** (`google-api-python-client` 等)
- [x] **バックエンド実装** (`src/calendar_manager.py`)
    - [x] OAuth 2.0 認証フロー
    - [x] `get_upcoming_events` の実装
- [x] **チャット連携** (`main.py`)
    - [x] スケジュール取得ロジック (キーワード検知)
    - [x] **カレンダーを開くコマンド** (`[ACTION:OPEN_CALENDAR]`)
    - [x] **予定追加コマンド** (`[ACTION:ADD_EVENT]`)
- [x] **検証**
    - [x] ブラウザ起動テスト
    - [x] スケジュール応答テスト

## フェーズ11: ソースコードのリファクタリング
- [x] **モジュール構造化**
    - [x] `src/core`, `src/services`, `src/api` の作成
    - [x] サービスの移動とインポート修正
- [x] **APIロジックの分割**
    - [x] API Mixinの作成 (`WindowApi`, `SettingsApi`, `ChatApi`)
    - [x] `main.py` の書き換えと Mixin の継承

## フェーズ12: 設定画面の刷新 (システマチックUI)
- [x] **独立ウィンドウ化**
    - [x] モーダルを廃止し `webview.create_window` を使用 (`src/settings.html`)
    - [x] タブ式インターフェース (基本設定, AI, 音声, 連携)
- [x] **ロジック更新**
    - [x] `ConfigManager.update()` の実装
    - [x] リアルタイムな見た目の更新 (不透明度/フォント)
    - [x] UIへのカレンダー認証統合

## フェーズ13: UI/UX改善 (Suggestion Chips & Active Talk) [完了]
- [x] **能動的アクション (Active Talk)**
    - [x] 手動トリガーボタン (✨) 実装
    - [x] 自動発話タイマー (設定スライダー) 実装
    - [x] バックエンド: `ActiveEngine` によるプッシュ通知
- [x] **サジェストチップ (Cheat Button)**
    - [x] 💡ボタンとポップアップリスト実装
    - [x] AI応答のJSONパースと候補表示
- [x] **検証済み**

## フェーズ17: リモートアクセス (スマホ対応/Webサーバー化) [実装完了]
- [x] **サーバー実装 (`server.py`)** (FastAPI)
    - [x] `pip install fastapi uvicorn python-multipart`
    - [x] REST API構築 (`/api/chat`, `/api/calendar`)
    - [x] StaticFiles (`dist/`) の配信
- [x] **フロントエンド通信アダプター (`src/api_client.ts`)**
    - [x] `ApiClient` クラス作成 (Strategy Pattern)
    - [x] 環境判定 (Desktop vs Web)
    - [x] 通信ロジックの抽象化 (Native Bridge vs Fetch)
- [x] **フロントエンド統合**
    - [x] `index.ts` のブリッジ呼び出しを `api` クラス経由に変更
- [x] **検証**
    - [x] サーバー起動確認
    - [x] 実機(スマホ)ブラウザからのアクセス (`http://192.168.0.2:8000`)
    - [x] 音声再生の動作確認

## Phase 18: Mobile UI Optimization (Pixel 7a) [完了]
- [x] **Responsive Design**
    - [x] Add Viewport Meta Tag
    - [x] CSS Media Queries for Mobile (< 768px)
    - [x] Vertical Layout (Character Top, Chat Bottom)
    - [x] Touch-optimized Inputs & Buttons
    - [x] **New Features**: Force Talk (✨) & Suggestion Toggle (💡) Buttons (Fixed z-index & position)
- [x] **Verification**
    - [x] Desktop Regression Test
    - [x] Button Interactivity Fix (Server JSON logic + CSS fixes)
    - [x] **UI Polish**: Unified Button Sizes, Settings Logic (Close/Mobile Visibility)
- [x] **Mobile Layout Fixes:**
    - [x] Character Fullscreen (100vh) & White Gap Removal
    - [x] **Split Screen Layout:** 2-Story Flexbox (Char Top / Chat Bottom)
    - [x] Robust Resize Logic (Auto-center on Mobile)
    - [x] Debug Logging for Mobile Troubleshooting

## Phase 19: Mobile Immersion (添い寝への道)
*スマホ体験を深化させ、物理的な距離をゼロにする試み*

- [ ] **🎵 音声のスマホ転送 (Streaming Audio)**
    - [ ] 音声データのバイナリ転送ロジック (Server -> Client)
    - [ ] Web Audio API によるブラウザ再生実装
    - [ ] 自動再生ポリシー (Auto-play Policy) の回避策実装
- [ ] **🎤 こちらの声も届ける (Voice Input)**
    - [ ] HTTPS化 (マイクアクセスに必須) or ローカルプロキシ設定
    - [ ] Web Speech API / AudioRecorder の実装
    - [ ] 音声データのServer送信とWhisper連携 (STT)
- [ ] **🧠 知能のさらなる強化 (Memory & Vision)**
    - [ ] 画像アップロード機能の実装 (Camera API)
    - [ ] Gemini Vision (Multimodal) への画像送信
    - [ ] 想い出(長期記憶)の強化とコンテキスト反映

## Phase 20: Persona System Refactoring (YAML Separation) [完了]
*ペルソナ定義（データ）とAIロジック（コード）の完全分離*

- [x] **File Structure & Data**
    - [x] `personas/` ディレクトリ作成
    - [x] `default.yaml` (既存プロンプトの移行)
    - [x] `lena.yaml` (サンプルペルソナ作成)
- [x] **Backend Implementation**
    - [x] `src/persona_manager.py` 実装 (YAML Loader)
    - [x] `src/ai_engine.py` Refactoring (Remove hardcoded prompt)
    - [x] `main.py` Integration (Startup load & Switch logic)
    - [x] API Endpoints Implementation (`/api/personas`, `/api/persona/change`)
- [x] **Frontend Integration**
    - [x] Settings UI: ペルソナ選択ドロップダウンの実装
    - [x] APIつなぎ込み (`get_persona_list`, `change_persona`)

## Phase 21: v0.2.0 Stability Fixes (Mobile & Desktop) [完了]
- [x] **Mobile UI Fixes**
    - [x] Split Screen Layout (2-Story): キャラ(上) + チャット(下)
    - [x] Character Resume/Resize Logic (oscillation fix)
    - [x] Button Layout & Spacing
- [x] **Desktop Fixes**
    - [x] Settings Window `RecursionError` fix (API property hiding)
    - [x] `get_persona_list` API method mismatch fix
    - [x] Character Zoom/Resize Stability fix (`internalModel.height` usage)


## Phase 22: Soul Bubble System Implementation
- [x] **Frontend Implementation**
    - [x] Add `#soul-bubble` DOM elements to `src/index.html`
    - [x] Implement CSS animations (Floating, Hover)
    - [x] Create `src/soul_bubble.ts` logic class
    - [x] Integrate with `src/index.ts`
- [x] **Backend Implementation**
    - [x] Create `src/api/bubble_api.py` (Actions)
    - [x] Create `src/services/bubble_service.py` (Logic support)
    - [x] Integrate into `main.py`
- [x] **Verification**
    - [x] Test Floating Animation (Auto-inject on startup)
    - [x] Test Hover Interaction (Expand/Preview)
    - [x] Test Click Action (Trigger Python API)

## Phase 23: Multiple Bubbles & Advanced Interaction
- [x] **Frontend Refactor**
    - [x] `src/index.html`: Replace single bubble with `#soul-bubble-container`
    - [x] `src/soul_bubble.ts`: Refactor to `SoulBubbleManager`
    - [x] Implement Click-to-Expand Interaction
    - [x] CSS: Multiple bubble stacking logic
- [x] **Backend Update**
    - [x] `main.py`: Test spawning multiple bubbles

## Phase 24: Soul Bubble Refinements (話題同期とデザイン) [完了]
- [x] **話題同期機能 (Topic Coordination)**
    - [x] `src/services/bubble_service.py`: 実際のニュースや話題に基づいてバブルのテキストとアクションIDを生成する。
    - [x] **Smart Force Talk Implementation** (Added): `force_talk` uses `user_profile.yaml`.
    - [x] クリック時にその話題についての会話が始まるようにする。 (Completed in Phase 30)
    - [x] **Stability Fixes**: Refactored `BubbleService` for interval limits & dynamic settings.
- [x] **デザインの洗練 (Design Polish)**
    - [x] **アイコンデザイン**: テキストアイコンを適切なSVGまたは画像アイコンに置き換える。 (Basic Implementation Done)
    - [x] **アニメーション**: 浮遊や出現・消失の動きを微調整する。 (Verified)

## Phase 25: ユーザープロファイル連携 (Context Injection)
- [x] **データ構造 (Data Structure)**
    - [x] `user_profile.yaml` の作成 (ユーザー対応済み)
    - [x] YAML解析用の `src/services/user_manager.py` を作成
- [x] **バックエンド統合 (Backend Integration)**
    - [x] `UserManager` を `server.py` と `main.py` に統合
    - [x] プロファイルデータを `system_prompt` に注入
- [x] **検証 (Verification)**
    - [x] AIがユーザープロファイル（仕事、趣味）に言及するか会話テストを行う

## Phase 26: ユーザープロファイル編集UI (Settings Integration)
- [x] **バックエンド実装 (API)**
    - [x] `src/services/user_manager.py`: YAML読み書きメソッド (`get_raw_yaml`, `save_raw_yaml`) の追加
    - [x] `src/api/user_api.py`: フロントエンド向けAPI Mixinの作成
    - [x] `main.py` & `server.py`: API Mixinの統合
- [x] **フロントエンド実装 (UI)**
    - [x] `src/settings.html`: 「User」タブの追加
    - [x] YAML編集用テキストエリアと保存ボタンの実装
    - [x] バリデーション（YAML構文チェック）
- [x] **検証**
    - [x] 設定画面からプロファイルを変更し、即座にAIの反応が変わるか確認

## Phase 27: UI Polishing (操作性とデザインの改善)
- [x] **ドラッグ操作の制限 (Window Drag)**
    - [x] 画面全体 (`body`) のドラッグを無効化し、テキスト選択を可能にする。
    - [x] `#character-area` のみをドラッグ可能にする。
- [x] **Soul Bubble 調整**
    - [x] **位置**: 全体的に表示位置を上に上げる。
    - [x] **スタイル**: アイコンサイズを縮小し、非展開時のセンタリング（gapの除去）を行う。

## Phase 28: Stability & Bug Fixes (安定性向上とバグ修正)
- [x] **UI Interaction Fixes**
    - [x] システムログパネルのテキスト選択・コピーを許可 (`user-select: text`)
    - [x] Settings UIのHTML構造エラー修正 (タブレイアウト崩れ解消)
- [x] **System Stability**
    - [x] 設定読み込みのRace Condition修正 (`pywebviewready` 待機)
- [x] **AI Context Logic**
    - [x] 時間帯（Morning/Daytime/Night）を明示的にコンテキスト注入し、挨拶の食い違いを解消

## Phase 29: Grounding Implementation (Google検索連携) [完了]
- [x] **Library Update**
    - [x] `pip install google-genai` (New SDK)
- [x] **Data & Backend**
    - [x] `search_topics.yaml` & `InterestManager` の作成
    - [x] `src/api/settings_api.py` に読み書きAPIを追加
- [x] **AI Engine Update**
    - [x] `src/services/ai_engine.py` で `tools=[{'google_search': {}}]` を有効化
- [x] **Settings UI**
    - [x] `src/settings.html` に検索トピック編集エリアを追加
- [x] **Flow Integration**
    - [x] `force_talk` (main.py) でトピックを選択し、検索指示プロンプトを生成する実装

## Phase 30: Smart Context & Bubble Intelligence [完了]
- [x] **Bubble Logic Refactoring**
    - [x] `BubbleService` をリファクタリングし、ランダムではなくコンテキスト認識型に変更
    - [x] **時間帯認識 (Time Awareness)**: Morning/Daytime/Evening/Night/Midnight の判定ロジック
    - [x] **カレンダー認識**: 曜日（月曜/金曜/週末）と季節（春夏秋冬）の認識
- [x] **Personalization Injection**
    - [x] `UserManager` と連携し、ユーザーの興味（`user_profile.yaml`）をバルーン話題に反映
- [x] **Action Grounding**
    - [x] バルーンクリック時に、その話題についてGoogle検索を行うようAIに指示する機能

## Phase 31: Project Structure & Memory Foundation [完了]
- [x] **Project Structure Optimization**
    - [x] Create `settings/` directory for config separation.
    - [x] Move `config.json`, `user_profile.yaml`, `personas/` to `settings/`.
    - [x] Update paths in `ConfigManager`, `UserManager`, `PersonaManager`, `TTSEngine`.
- [x] **Long-term Memory Foundation**
    - [x] Create `memory/` directory and `learned_facts.yaml`.
    - [x] Implement `MemoryService` with logic to extract/save facts and combine contexts.
    - [x] Integrate Memory context into `server.py` System Prompt.

## Phase 31.5: UI/UX Fixes [完了]
- [x] **Settings Window Fixes**:
    - [x] Resize to 800x700 and enable resizing.
    - [x] Add drag region to sidebar.
    - [x] Restore "Tabbed" interface by opening proper `settings.html` window (switched from legacy overlay).
- [x] **Trash Zone Fix**:
    - [x] Add `#trash-zone` to `index.html` with visible CSS.n by default)
    - [x] Update `SoulBubble` (TS) to handle Drag & Drop events
    - [x] Implement spring-back logic (Cancel dismissal)
    - [x] Implement drop-to-delete logic (API Trigger)
- [x] **Visuals**
    - [x] Dragging visual feedback (Scale, Z-Index)

## Phase 32: Soul Bubble Drag & Drop (Refinements) [完了]
- [x] **Frontend Implementation**
    - [x] Add `#trash-zone` to `index.html` (Hidden by default)
    - [x] Update `SoulBubble` (TS) to handle Drag & Drop events
    - [x] Implement spring-back logic (Cancel dismissal)
    - [x] Implement drop-to-delete logic (API Trigger)
- [x] **Visuals**
    - [x] Dragging visual feedback (Scale, Z-Index)
    - [x] Trash Zone fade-in/out
    - [x] Discovery Bubble Styling (Purple)
- [x] **Verification**
    - [x] Test dragging bubbles
    - [x] Test dismissal on drop
    - [x] Verify auto-refill logic after dismissal

## Phase 33: Chat History UI [新規] [完了]
- [x] **Backend Implementation**
    - [x] `src/api/chat_api.py`: Implement `get_history(limit)` in Mixin.
    - [x] `server.py`: Add `/api/history` endpoint.
    - [x] `src/api_client.ts`: Implement `get_history` bridge.
- [x] **Frontend Implementation**
    - [x] `src/index.html`: Add History Button (📖) to System Panel (Bottom-Left).
    - [x] `src/index.html`: Refactor Left Panel to support History Mode.
    - [x] `src/index.ts`: Implement Panel Toggle Logic (Debug <-> History).
- [x] **Verification**
    - [x] Toggle Panel -> Verify logs loaded from JSONL.
    - [x] Switch between Debug/History modes.
    - [x] Verify styling (Systematic Design).
    - [x] Verify styling (Systematic Design).

## Phase 34: Audio Player Control (Stop/Speed) [新規] [完了]
- [x] **Service Implementation**
    - [x] `src/services/audio_manager.ts`: Singleton AudioManager with Stop/Speed logic.
- [x] **UI Implementation**
    - [x] `src/index.html`: Add `#audio-player` (Review Stop/Speed buttons).
    - [x] `src/index.html`: CSS for Mini Player (Float above input).
- [x] **Logic Integration**
    - [x] `src/index.ts`: Integrate `AudioManager` with `playAudioWithLipSync`.
    - [x] `src/index.ts`: Bind UI events (Stop, Speed Toggle).
- [x] **Verification**
    - [x] Play long audio -> Stop -> Confirm silence & lip stop.
    - [x] Play audio -> Change Speed -> Confirm rate change.

## Phase 35: Session Restore (Resume Conversation) [On Hold]
- [x] **Backend Implementation**
    - [x] `src/services/history_manager.py`: Create logic to read `chat_history.jsonl` (Limit 30).
    - [x] `server.py`: Add `/api/history/restore` endpoint.
- [x] **Frontend Implementation**
    - [x] `src/api_client.ts`: Add `restore_history()` method.
    - [x] `src/index.ts`: Call `restore_history()` on logic init.
    - [x] `src/index.ts`: Render logs without TTS triggers.
    - [x] `src/index.ts`: Add `--- Last Session ---` divider.
- [x] **Debugging & Desktop Fixes**
    - [x] `main.py`: Add `restore_history` and `debug_log`.
    - [x] `src/index.ts`: Wait for `pywebviewready` event.
    - [x] `src/services/history_manager.py`: Fix path resolution (Desktop).
- [x] **Enhancement: Manual Refresh**
    - [x] `index.html`: Add Context Menu structure.
    - [x] `index.ts`: Implement Right-Click Logic.
    - [x] Fix: Separate menus for Character (Settings/Exit) and Log (Restore).
    - [x] Fix: Resolve `temp_history` error in backend.
    - [x] Debug: Added JSON dump logging for restore data validation.
    - [x] Refactor: `HistoryManager` now uses `memory/` dir with `logs/` fallback and fixed parsing logic.
    - [x] Fix: Implemented aggressive JSON cleanup in `server.py` to remove markdown leakage.


## Phase 36: UI Stability Fixes (Desktop Layout) [完了]
- [x] **Desktop Layout Fixes**
    - [x] `#character-area` fixed size (500px !important, no-shrink) to prevent layout shifts.
    - [x] `#trash-zone` positioning (Inside character area, top: 10px, left: 10px) to prevent clipping.

## Phase 37: Vision Integration & Prompt Fix (Desktop) [完了]
- [x] **視覚機能の実装 (Vision)**
    - [x] Backend (`server.py`): `chat_with_vision(mode)` implementation using `PIL.ImageGrab`.
    - [x] Frontend (`index.ts`): Camera Button Logic (Left Click: Screen, Right Click: Clipboard).
    - [x] API Bridge (`api_client.ts`): Updated interface to support `mode`.
- [x] **AI人格プロンプトの修正**
    - [x] System Prompt (`server.py`): "Keep it concise" constraint relaxed to allow detailed responses when requested.

## Phase 38: Vision Debugging & UI Refinement (Desktop) [完了]
- [x] **Vision Mode Fix (Conflict Resolution)**
    - [x] `ai_engine.py`: Refactored `generate_response` logic.
    - [x] **Stateless Request**: Use `generate_content` (Tools=[]) for image input to avoid conflicts.
    - [x] **Prompt Override**: Added strict instruction "You CAN see the image" to Vision mode.
    - [x] **JSON Parsing**: Implemented Regex-based extraction (`_parse_json_response`) to handle conversational precursors.
- [x] **UI Layout Refinement**
    - [x] Vertical Button Stack (Suggestion 💡 / Vision 📷).
    - [x] Clock moved to bottom-left corner for clarity.
    - [x] Right-side buttons (Settings, Debug, History, Toggle) tightened to bottom-right corner.
    - [x] **Initialization Fix**: Force window resize to 500x500 on startup to prevent UI cropping.
    - [x] **Context Menu Fix**: Prevent app context menu on Vision button right-click (`stopPropagation`).

## Phase 39: VOICEVOX Integration (Completed)
- [x] **Backend Service**
    - [x] `src/services/voice_service.py`: Created `VoiceService` to interface with local VOICEVOX app (port 50021).
    - [x] `server.py`: Integrated `VoiceService` and added `tts_provider` logic in `chat()` method.
- [x] **Frontend Configuration**
    - [x] `settings.html`: Enabled TTS Provider selection (Google vs VOICEVOX).
    - [x] `settings.html`: Implemented dynamic voice list loading via `loadVoices()`.
    - [x] `src/api/settings_api.py`: Updated `get_voice_types` to support provider-specific lists.

## Phase 40: Gemini 2.5 TTS Integration (Completed)
- [x] **Backend Implementation**
    - [x] `src/services/voice_service.py`: Add `_generate_gemini_audio` using `google-genai` SDK.
    - [x] **Model Update**: Use `gemini-2.5-flash-preview-tts` (Flash 2.5).
    - [x] **Robustness**: Implement WAV Header Wrapping (Raw PCM -> WAV) & URL Encoding.
- [x] **Frontend Configuration**
    - [x] `settings.html`: Add "Gemini 2.5 Flash TTS (Preview)" option.
    - [x] `src/api/settings_api.py`: Add Gemini voice list (Kore, Puck, Fenrir, etc.).
- [x] **UI Polish**
    - [x] **Window Layering**: Fix Settings Window to always stay on top (`on_top=True`).

## Phase 41: Stability & Refactoring (Soul Bubbles & API) [完了]
- [x] **Soul Bubble Refactoring (Unified Logic)**
    - [x] **Frontend**: 手動バルーン生成（💭ボタン）を `SoulBubbleManager` に統合。
        - [x] 自動消滅タイマーの廃止（永続化）。
        - [x] システム生成バルーンとのデザイン/挙動の統一。
    - [x] **Backend**: 手動バルーンのステート管理 (`register_manual_bubble`)。
        - [x] クリック時のアクションID (`MANUAL_...`) を正常に処理するロジック追加。
- [x] **Critical Bug Fixes**
    - [x] **Crash Fix**: `Api` クラス（Desktop/Server）の依存関係注入 (`self.services`) 漏れによる `AttributeError` を修正。
    - [x] **JSON Serialization**: `datetime` オブジェクトが返却された際の `TypeError` を修正 (`isoformat()` 変換)。
    - [x] **Startup Stability**: `pywebview` 初期化競合 (`showSoulBubble is not defined`) の解消確認。

## Phase 42: Gemini TTS & RAG Stability 対応 [完了]
- [x] **RAGログの修正 (RAG Logging Fixes)**
    - [x] **フロントエンド 405エラー修正**: `src/index.ts` のログ送信を `console.log` (Bridge転送) に変更しエラーを解消。
    - [x] **データ伝播ロジック修正**: `ChatApiMixin` (Desktop) および `server.py` (Server) で `grounding_info` をレスポンスに含めるよう修正。
    - [x] **検証**: RAGタブに検索クエリとソースURLが表示されることを確認。
- [x] **Gemini TTS 400エラー修正**
    - [x] **原因特定**: Gemini TTSモデルがテキスト生成を試みて `INVALID_ARGUMENT` になっていた問題を特定。
    - [x] **修正適用**: `voice_service.py` のconfigに `response_modalities=["AUDIO"]` を追加し、音声出力のみを強制。
