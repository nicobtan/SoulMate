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

## フェーズ13: 能動的アクションUI (Soul Bubble)
- [ ] **UI実装 (HTML/CSS)**
    - [ ] `soul-bubble` コンポーネント作成 (Floating Animation)
    - [ ] ホバー展開ロジック & スタイリング (Blue/Green/Pink/Orange)
- [ ] **フロントエンドロジック (TypeScript)**
    - [ ] `showSoulBubble` 関数定義
    - [ ] クリックイベントハンドラ (`trigger_bubble_action`)
- [ ] **バックエンド連携 (Python)**
    - [ ] `WindowApi.trigger_bubble` 実装
    - [ ] ニュース分析やシステム監視との連携テスト
## フェーズ14: 自動返答 (Auto Response System) [新規]
- [ ] **バックエンド実装 (API)**
    - [ ] `src/ai_engine.py`: JSONモードでの応答生成プロンプト修正
    - [ ] `src/api/chat_api.py`: レスポンスパース処理 & 固定サジェスト追加ロジック
- [ ] **フロントエンド実装 (UI)**
    - [ ] `src/index.html`: サジェストチップ表示エリア (`#suggestion-area`) の追加
    - [ ] `src/index.ts`: チップ生成・更新ロジック (`updateSuggestions`)
    - [ ] `src/index.ts`: チップクリック時の送信イベント処理
