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

## Phase 20: Persona System Refactoring (YAML Separation)
*ペルソナ定義（データ）とAIロジック（コード）の完全分離*

- [ ] **File Structure & Data**
    - [ ] `personas/` ディレクトリ作成
    - [ ] `default.yaml` (既存プロンプトの移行)
    - [ ] `lena.yaml` (サンプルペルソナ作成)
- [ ] **Backend Implementation**
    - [ ] `src/persona_manager.py` 実装 (YAML Loader)
    - [x] `src/ai_engine.py` Refactoring (Remove hardcoded prompt)
    - [ ] `main.py` Integration (Startup load & Switch logic)
- [ ] **Frontend Integration**
    - [ ] Settings UI: ペルソナ選択ドロップダウンの実装
    - [ ] APIつなぎ込み (`get_persona_list`, `change_persona`)

