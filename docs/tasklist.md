# デスクトップマスコット開発 タスクリスト

## フェーズ1: 基本的なウィンドウの構築 [完了]
- [x] Pythonの仮想環境を構築する
- [x] `pywebview` ライブラリをインストールする (`pip install pywebview`)
- [x] `main.py` を作成し、基本的なWebViewウィンドウを表示するコードを記述する
- [x] ウィンドウをフレームレス（枠なし）に設定する
- [x] ウィンドウの背景を透過させる
- [x] ウィンドウを常に最前面に表示する設定を追加する
- [x] HTML側（`index.html`）のCSS/JavaScriptで、ウィンドウ全体をドラッグして移動できる機能を実装する

## フェーズ2: キャラクター表示 (静止画Ver) [完了]
- [x] 仮のキャラクター画像 (`images/naya_test.png`) を用意する
- [x] `src/index.html` を修正し、`naya_test.png` を正しく表示する
- [x] TypeScriptビルド環境を整備する (`tsconfig.json` の修正)

## フェーズ3: カスタムコンテキストメニューの実装 [完了]
- [x] `src/index.html` に、メニューの元となるHTML要素を記述する
- [x] CSSでメニューの見た目を整える
- [x] TypeScript (`src/index.ts`) で右クリックイベントを実装する
- [x] ビルドを実行し、Python連携して「終了」機能が動くことを確認する

## フェーズ4: Live2Dモデルの表示 [完了]
- [x] Live2D Cubism SDK / PixiJS の導入
- [x] モデルデータの配置 (`dist/models`)
- [x] `index.ts` でのモデルロードと表示処理の実装
- [x] 動作確認（アニメーション、背景透過）

---

## フェーズ5: UI拡張 (チャットインターフェース) [完了]
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

## フェーズ7: 知能強化 (RAG & ペルソナロジック) [完了]
- [x] **AIエンジン改修 (`src/ai_engine.py`)**
    - [x] `SoulMateProfile` (TS風) プロンプト構築ロジックの実装
    - [x] 音声用出力制約 ("絵文字/記号禁止", "短文") の適用
- [x] **ペルソナ・プロファイル管理**
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

## フェーズ9.5: UI/UXの洗練 (Polishing) [完了]
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

## フェーズ10: 外部連携 (Googleカレンダー) [完了]
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

## フェーズ11: ソースコードのリファクタリング [完了]
- [x] **モジュール構造化**
    - [x] `src/core`, `src/services`, `src/api` の作成
    - [x] サービスの移動とインポート修正
- [x] **APIロジックの分割**
    - [x] API Mixinの作成 (`WindowApi`, `SettingsApi`, `ChatApi`)
    - [x] `main.py` の書き換えと Mixin の継承

## フェーズ12: 設定画面の刷新 (システマチックUI) [完了]
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

## フェーズ17: リモートアクセス (スマホ対応/Webサーバー化) [完了]
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

## フェーズ18: モバイルUI最適化 (Pixel 7a) [完了]
- [x] **レスポンシブデザイン**
    - [x] Viewport Metaタグの追加
    - [x] モバイル用CSSメディアクエリ (< 768px)
    - [x] 縦型レイアウト (キャラ上部、チャット下部)
    - [x] タッチ最適化された入力欄とボタン
    - [x] **新機能**: 強制会話(✨) & サジェスト切替(💡) ボタン (z-indexと配置修正)
- [x] **検証**
    - [x] デスクトップ回帰テスト
    - [x] ボタン操作性の修正 (Server JSONロジック + CSS修正)
    - [x] **UI調整**: ボタンサイズの統一、設定ロジック (閉じるボタン/モバイル表示)
- [x] **モバイルレイアウト修正:**
    - [x] キャラクター全画面表示 (100vh) & 白い隙間の削除
    - [x] **分割画面レイアウト:** 2階建てフレックスボックス (キャラ上 / チャット下)
    - [x] 堅牢なリサイズ処理 (モバイルでの自動中央寄せ)
    - [x] モバイルトラブルシューティング用のデバッグログ

## フェーズ19: モバイル没入感向上 (添い寝への道) [未着手]
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

## フェーズ20: ペルソナシステムのリファクタリング (YAML分離) [完了]
*ペルソナ定義（データ）とAIロジック（コード）の完全分離*

- [x] **ファイル構造とデータ**
    - [x] `personas/` ディレクトリ作成
    - [x] `default.yaml` (既存プロンプトの移行)
    - [x] `lena.yaml` (サンプルペルソナ作成)
- [x] **バックエンド実装**
    - [x] `src/persona_manager.py` 実装 (YAML Loader)
    - [x] `src/ai_engine.py` リファクタリング (ハードコードされたプロンプトの削除)
    - [x] `main.py` 統合 (起動時の読み込み & 切り替えロジック)
    - [x] APIエンドポイント実装 (`/api/personas`, `/api/persona/change`)
- [x] **フロントエンド統合**
    - [x] Settings UI: ペルソナ選択ドロップダウンの実装
    - [x] APIつなぎ込み (`get_persona_list`, `change_persona`)

## フェーズ21: v0.2.0 安定性修正 (Mobile & Desktop) [完了]
- [x] **モバイルUI修正**
    - [x] 分割画面レイアウト (2階建て): キャラ(上) + チャット(下)
    - [x] キャラクターのレジューム/リサイズロジック (振動修正)
    - [x] ボタンの配置とスペーシング調整
- [x] **デスクトップ修正**
    - [x] 設定ウィンドウの `RecursionError` 修正 (APIプロパティ隠蔽)
    - [x] `get_persona_list` APIメソッド不一致の修正
    - [x] キャラクター拡大/リサイズ安定性の修正 (`internalModel.height` 使用)

## フェーズ22: ソウルバブル（Soul Bubble）システム実装 [完了]
- [x] **フロントエンド実装**
    - [x] `src/index.html` への `#soul-bubble` DOM要素追加
    - [x] CSSアニメーション実装 (浮遊, ホバー)
    - [x] `src/soul_bubble.ts` ロジッククラスの作成
    - [x] `src/index.ts` との統合
- [x] **バックエンド実装**
    - [x] `src/api/bubble_api.py` 作成 (アクション処理)
    - [x] `src/services/bubble_service.py` 作成 (ロジックサポート)
    - [x] `main.py` への統合
- [x] **検証**
    - [x] 浮遊アニメーションのテスト (起動時の自動注入)
    - [x] ホバーインタラクションのテスト (拡大/プレビュー)
    - [x] クリックアクションのテスト (Python APIトリガー)

## フェーズ23: 複数バブル & 高度なインタラクション [完了]
- [x] **フロントエンド・リファクタリング**
    - [x] `src/index.html`: 単一バブルを `#soul-bubble-container` に置換
    - [x] `src/soul_bubble.ts`: `SoulBubbleManager` へのリファクタリング
    - [x] クリックによる拡大インタラクションの実装
    - [x] CSS: 複数バブルのスタッキングロジック
- [x] **バックエンド更新**
    - [x] `main.py`: 複数バブルの生成テスト

## フェーズ24: ソウルバブルの調整 (話題同期とデザイン) [完了]
- [x] **話題同期機能**
    - [x] `src/services/bubble_service.py`: 実際のニュースや話題に基づいたテキスト・アクションID生成
    - [x] **スマート強制会話の実装**: `force_talk` が `user_profile.yaml` を利用
    - [x] クリック時に関連する話題で会話を開始
    - [x] **安定性修正**: `BubbleService` の生成間隔制限と動的設定のリファクタリング
- [x] **デザインの洗練**
    - [x] **アイコンデザイン**: テキストからSVG/画像アイコンへの置換（基本実装完了）
    - [x] **アニメーション**: 浮遊・出現・消失の動きの微調整

## フェーズ25: ユーザープロファイル連携 (Context Injection) [完了]
- [x] **データ構造**
    - [x] `user_profile.yaml` の作成
    - [x] YAML解析用 `src/services/user_manager.py` の作成
- [x] **バックエンド統合**
    - [x] `UserManager` を `server.py` と `main.py` に統合
    - [x] プロファイルデータを `system_prompt` に注入
- [x] **検証**
    - [x] AIがユーザープロファイル（仕事、趣味）に言及するかのテスト

## フェーズ26: ユーザープロファイル編集UI (設定画面統合) [完了]
- [x] **バックエンド実装 (API)**
    - [x] `src/services/user_manager.py`: YAML読み書きメソッドの実装
    - [x] `src/api/user_api.py`: フロントエンド用API Mixinの作成
    - [x] `main.py` & `server.py`: API Mixinの統合
- [x] **フロントエンド実装 (UI)**
    - [x] `src/settings.html`: 「User」タブの追加
    - [x] YAML編集用エリアと保存ボタンの実装
    - [x] バリデーション（YAML構文チェック）
- [x] **検証**
    - [x] 設定画面からの変更が即座にAIの反応に反映されるか確認

## フェーズ27: UI Polishing (操作性とデザインの改善) [完了]
- [x] **ドラッグ操作の制限**
    - [x] 画面全体 (`body`) のドラッグ無効化とテキスト選択の許可
    - [x] `#character-area` のみドラッグ可能に設定
- [x] **Soul Bubble 調整**
    - [x] **位置**: 全体的な表示位置の上方修正
    - [x] **スタイル**: アイコンサイズ縮小、非展開時のセンタリング調整

## フェーズ28: 安定性向上とバグ修正 [完了]
- [x] **UIインタラクション修正**
    - [x] システムログパネルのテキスト選択・コピー許可
    - [x] Settings UIのHTML構造エラー修正 (タブレイアウト崩れ)
- [x] **システム安定性**
    - [x] 設定読み込み時の競合状態 (Race Condition) 修正
- [x] **AIコンテキストロジック**
    - [x] 時間帯（Morning/Daytime/Night）の明示的なコンテキスト注入

## フェーズ29: Grounding実装 (Google検索連携) [完了]
- [x] **ライブラリ更新**
    - [x] `pip install google-genai` (新SDK)
- [x] **データ & バックエンド**
    - [x] `search_topics.yaml` & `InterestManager` 作成
    - [x] `src/api/settings_api.py` への読み書きAPI追加
- [x] **AIエンジン更新**
    - [x] `src/services/ai_engine.py` で Google Search Tool を有効化
- [x] **設定画面 UI**
    - [x] `src/settings.html` への検索トピック編集エリア追加
- [x] **フロー統合**
    - [x] `force_talk` でのトピック選択と検索指示プロンプトの実装

## フェーズ30: スマートコンテキスト & バブル知能 [完了]
- [x] **バブルロジックのリファクタリング**
    - [x] `BubbleService` をランダムから文脈認識型に変更
    - [x] **時間帯認識**: Morning/Daytime/Evening/Night/Midnight
    - [x] **カレンダー認識**: 曜日（月曜/金曜/週末）と季節（春夏秋冬）
- [x] **パーソナライズ注入**
    - [x] `UserManager` 連携による興味分野の反映
- [x] **アクションのGrounding**
    - [x] バブルクリック時のGoogle検索指示機能

## フェーズ31: プロジェクト構造と記憶基盤 [完了]
- [x] **プロジェクト構造の最適化**
    - [x] `settings/` ディレクトリ作成と設定ファイルの移動
    - [x] パス参照の更新 (`ConfigManager` 等)
- [x] **長期記憶の基盤**
    - [x] `memory/` ディレクトリと `learned_facts.yaml` 作成
    - [x] `MemoryService` の実装 (事実抽出・保存・コンテキスト結合)
    - [x] `server.py` システムプロンプトへの統合

## フェーズ31.5: UI/UX 修正 [完了]
- [x] **設定ウィンドウ修正**:
    - [x] サイズ800x700への変更とリサイズ許可
    - [x] サイドバーのドラッグ領域追加
    - [x] タブ式インターフェースの復旧（オーバーレイ廃止）
- [x] **ゴミ箱ゾーン (Trash Zone) 修正**:
    - [x] `#trash-zone` の追加とCSS調整
    - [x] ドラッグ＆ドロップイベントのハンドリング
    - [x] バネ戻り効果の実装
    - [x] 削除ロジックの実装
- [x] **ビジュアル**:
    - [x] ドラッグ時の視覚フィードバック（スケール、Z-Index）

## フェーズ32: ソウルバブル ドラッグ＆ドロップ (詳細化) [完了]
- [x] **フロントエンド実装**
    - [x] `#trash-zone` 実装
    - [x] `SoulBubble` クラスへのD&Dロジック追加
    - [x] ドロップによる削除トリガーの実装
- [x] **ビジュアル**
    - [x] ドラッグ中のフィードバック
    - [x] ゴミ箱のフェードイン/アウト
    - [x] 発見（Discovery）バブルのスタイル調整（紫）
- [x] **検証**
    - [x] ドラッグ、ドロップ削除、削除後の自動補充確認

## フェーズ33: チャット履歴UI [完了]
- [x] **バックエンド実装**
    - [x] `get_history(limit)` APIの実装
    - [x] `/api/history` エンドポイント
- [x] **フロントエンド実装**
    - [x] 履歴ボタン (📖) の追加
    - [x] 左パネルのリファクタリング（デバッグ/履歴モード切り替え）
    - [x] パネル切り替えロジックの実装
- [x] **検証**
    - [x] パネル切り替え、JSONLからの履歴読み込み確認
    - [x] システマチックなデザイン調整

## フェーズ34: 音楽プレイヤー制御 (停止/速度) [完了]
- [x] **サービス実装**
    - [x] `src/services/audio_manager.ts` (Singleton)
- [x] **UI実装**
    - [x] `#audio-player` (停止/速度ボタン) とミニプレイヤーCSS
- [x] **ロジック統合**
    - [x] `playAudioWithLipSync` との連携
    - [x] イベントバインディング
- [x] **検証**
    - [x] 再生制御（停止、速度変更）確認

## フェーズ35: セッション復元 (会話再開) [完了]
- [x] **バックエンド実装**
    - [x] `src/services/history_manager.py`: `chat_history.jsonl` 読み込みロジック (直近30件)
    - [x] `/api/history/restore` エンドポイント
- [x] **フロントエンド実装**
    - [x] `api.restore_history()` 実装と初期化時の呼び出し
    - [x] ログレンダリング（TTSなし）と「前回セッション」区切り線の表示
- [x] **デバッグ & 修正**
    - [x] `pywebviewready` 待機処理
    - [x] パス解決の修正 (Desktop)
- [x] **機能強化: 手動リフレッシュ**
    - [x] コンテキストメニューの実装 (履歴復元 / 設定 / 終了)
    - [x] `HistoryManager` のパス解決ロジック修正 (`memory/`優先)
    - [x] `server.py` でのJSONクリーンアップ強化

## フェーズ36: UI安定性修正 (デスクトップレイアウト) [完了]
- [x] **デスクトップレイアウト修正**
    - [x] キャラクターエリアの固定サイズ化 (500px, 縮小防止)
    - [x] ゴミ箱ゾーンの位置調整

## フェーズ37: 視覚機能統合 & プロンプト修正 (Desktop) [完了]
- [x] **視覚機能の実装 (Vision)**
    - [x] Backend (`server.py`): `chat_with_vision(mode)` 実装 (`PIL.ImageGrab`)
    - [x] Frontend: カメラボタンのロジック実装 (左=画面, 右=クリップボード)
    - [x] API Bridge: `mode` 対応
- [x] **AI人格プロンプトの修正**
    - [x] System Prompt: "簡潔に" 制約の緩和（詳細な応答を許可）

## フェーズ38: 視覚機能デバッグ & UI調整 (Desktop) [完了]
- [x] **Visionモード修正 (競合解消)**
    - [x] `ai_engine.py`: `generate_response` ロジックリファクタリング
    - [x] **ステートレスリクエスト**: 画像入力時は `generate_content` (Toolsなし) を使用
    - [x] **プロンプト上書き**: Visionモード時に「画像が見えている」旨を明示
    - [x] **JSONパース**: 会話的プレフィックスを除去するRegex抽出の実装
- [x] **UIレイアウト調整**
    - [x] ボタンの縦積み配置 (Suggest💡 / Vision 📷)
    - [x] 時計の左下配置、右側ボタン群の右下配置
    - [x] **初期化修正**: 起動時の500x500ウィンドウサイズ強制
    - [x] **コンテキストメニュー修正**: Visionボタン上の右クリックイベント伝播防止

## フェーズ39: VOICEVOX統合 [完了 / 保留]
- [x] **バックエンドサービス**
    - [x] `src/services/voice_service.py`: ローカルVOICEVOXアプリ (port 50021) 連携 (現在は無効化/Gemini優先)
    - [ ] **追加実装**: ローカルTTS (SBV2) の完全実装は保留
- [x] **フロントエンド設定**
    - [x] 設定画面: TTSプロバイダ選択 (UI実装済み)

## フェーズ40: Gemini 2.5 TTS統合 [完了]
- [x] **バックエンド実装**
    - [x] `src/services/voice_service.py`: `_generate_gemini_audio` 実装 (google-genai SDK)
    - [x] **モデル更新**: `gemini-2.5-flash-preview-tts` (Flash 2.5) 採用
    - [x] **堅牢性**: WAVヘッダーラッパー (Raw PCM -> WAV) とURLエンコード実装
- [x] **フロントエンド設定**
    - [x] 設定画面: "Gemini 2.5 Flash TTS (Preview)" オプション追加
    - [x] ボイスリスト更新 (Kore, Puck, Fenrir等)
- [x] **UI調整**
    - [x] **ウィンドウレイヤー**: 設定ウィンドウの最前面固定 (`on_top=True`)

## フェーズ41: 安定性向上 & リファクタリング (バブル & API) [完了]
- [x] **ソウルバブルのリファクタリング (ロジック統一)**
    - [x] **Frontend**: 手動バルーン生成（💭ボタン）を `SoulBubbleManager` に統合。
        - [x] 自動消滅タイマーの廃止（永続化）。
        - [x] システム生成バルーンとのデザイン/挙動の統一。
    - [x] **Backend**: 手動バルーンのステート管理 (`register_manual_bubble`)。
        - [x] クリック時のアクションID (`MANUAL_...`) を正常に処理するロジック追加。
- [x] **クリティカルなバグ修正**
    - [x] **Crash Fix**: `Api` クラス（Desktop/Server）の依存関係注入 (`self.services`) 漏れによる `AttributeError` を修正。
    - [x] **JSON Serialization**: `datetime` オブジェクトが返却された際の `TypeError` を修正 (`isoformat()` 変換)。
    - [x] **Startup Stability**: `pywebview` 初期化競合 (`showSoulBubble is not defined`) の解消確認。

## フェーズ42: Gemini TTS & RAG 安定性対応 [完了]
- [x] **RAGログの修正 (RAG Logging Fixes)**
    - [x] **フロントエンド 405エラー修正**: `src/index.ts` のログ送信を `console.log` (Bridge転送) に変更しエラーを解消。
    - [x] **データ伝播ロジック修正**: `ChatApiMixin` (Desktop) および `server.py` (Server) で `grounding_info` をレスポンスに含めるよう修正。
    - [x] **検証**: RAGタブに検索クエリとソースURLが表示されることを確認。
- [x] **Gemini TTS 400エラー修正**
    - [x] **原因特定**: Gemini TTSモデルがテキスト生成を試みて `INVALID_ARGUMENT` になっていた問題を特定。
    - [x] **修正適用**: `voice_service.py` のconfigに `response_modalities=["AUDIO"]` を追加し、音声出力のみを強制。
- [x] **自我検索副作用の緩和 (Opinion Priority)**
    - [x] **システムプロンプト修正**: ユーザーの質問が「好み」に関する場合、検索結果よりも自我（ペルソナ）を優先して感情的に答えるよう指示を追加。
- [x] **Deep Context Integration (Amnesia Fix)**
    - [x] **main.py修正**: ユーザープロファイル(YAML)の生データをシステムプロンプトに動的注入し、記憶喪失を防ぐロジックを実装。
    - [x] **active_engine.py修正**: 能動発話時もユーザーの趣味嗜好（Lovesなど）を参照するようコンテキスト指示を強化。
    - [x] **chat_api.py修正**: `chat` メソッド実行時に `user_manager.get_profile_context()` を都度呼び出し、会話コンテキストに動的に注入する修正を追加（完全な記憶喪失対策）。

## フェーズ43: バブル & RAG 回帰修正 [完了]
- [x] **手動バブル修正 (Regession Fix)**
    - [x] **原因**: AIEngine改修時のレスポンス形式変更(Dict化)により、BubbleServiceが誤作動。
    - [x] **Frontend**: `spawn-balloon-btn` のイベント設定漏れを修正。
    - [x] **Backend**: `api.generate_bubble` エンドポイントを新設し、`get_smart_bubble` (文脈認識生成) を呼び出すよう修正。
    - [x] **機能復旧**: 固定バブルではなく、文脈に沿ったスマートバブルが生成されるようにロジックを復元。
- [x] **Active Engine 修正**
    - [x] **Crash Fix**: `ActiveEngine` が依存する `generate_proactive_message` メソッドを `AIEngine` に実装。

## フェーズ44: 履歴機能強化 (History v3) [完了]
- [x] **管理機能の実装**
    - [x] **お気に入り機能**: `is_favorite` カラム追加、★ボタン、フィルター実装
    - [x] **検索機能**: タイトルとメッセージ内容のキーワード検索
    - [x] **削除機能**: セッションとログの完全削除
- [x] **UI/UX**
    - [x] 独立ウィンドウでのサイドバー検索バー、フィルターボタン
    - [x] 削除確認ダイアログ

## フェーズ45: タイトル生成 & ログ品質向上 [完了]
- [x] **タイトル自動生成ロジック改善**
    - [x] 直近10件の会話を使用するように変更 (Recency Priority)
    - [x] 不要なシステムプレフィックス (`[Grounding Instruction]`, `[Situation]`) の除去
- [x] **ログクリーニング**
    - [x] 起動時のマイグレーション処理による汚染ログの削除
## フェーズ46: 履歴ウィンドウの洗練と手動制御 (History v4 & UI Refactor) [完了]
- [x] **手動セッション管理の実装**
    - [x] 「保存（タイトル確定）」ボタンの実装
    - [x] 「新規会話開始」ボタンの実装
    - [x] バックエンド API (`manual_save_session`, `start_new_session`) の追加
- [x] **UI/UX の抜本的刷新**
    - [x] トップコントロールパネル（保存/新規/検索）の配置
    - [x] 2カラムレイアウト（左：リスト、右：詳細）への変更
    - [x] モダンでシステマチックなデザインへのブラッシュアップ
- [x] **安定性・型安全性の向上**
    - [x] TypeScript の型定義 (`src/types.d.ts`) の更新とビルドエラーの解消
    - [x] API 呼び出しのタイミング制御 (`api_client.ts`, `history.ts`) の改善

## フェーズ47: モダンな視覚機能フロー (Modern Vision Flow) [完了]
- [x] **プレビュー機能の実装**
    - [x] スクリーンショットを即座に送信せず、サムネイルとして表示するフローの構築
    - [x] フロントエンド UI (`#attachment-preview-area`) の追加
    - [x] 添付解除ボタンの追加
- [x] **バックエンド連携の強化**
    - [x] `take_screenshot_for_preview` API の新設
    - [x] `chat` メソッドの拡張 (マルチモーダル対応: テキスト + 画像データ)
- [x] **UI/UX の洗練**
    - [x] 送信ボタン押下時に画像とテキストをセットで送信するロジック
    - [x] TypeScript 型定義の更新とビルドエラーの解消

## フェーズ48: TOON形式の導入 (TOON Standard Implementation) [Cancelled / Replaced]
- **理由**: 正規表現パースの限界と、Gemini Native JSON Mode の登場によるアーキテクチャ刷新のため。
- [x] ~~**フォーマットの刷新**~~
    - [x] ~~通信形式をJSONからTOON (Token-Oriented Object Notation) へ変更~~
- [x] ~~**堅牢なパースロジック**~~
    - [x] ~~`AIEngine` への正規表現ベースのTOONパーサー実装~~

## フェーズ49 〜 64: [Rolled Back / Skipped]
- **注記**: TOON形式の最適化や実験的機能の実装が行われましたが、システム安定化のための「大規模ロールバック (v0.2.1)」に伴い、これらの履歴はリセットされました。
- 現在の最新版は **Phase 65 (Native JSON)** 以降となります。

## フェーズ65: Native JSON Outputによる堅牢化 [完了]
- [x] **AI EngineのJSON化 (`ai_engine.py`)**
    - [x] 正規表現によるTOONパース処理の完全撤廃
    - [x] `response_schema` による出力形式の強制 (Gemini Native JSON Mode)
    - [x] 推論モデル(`gemini-3-flash`)とTTSモデル(`gemini-2.5-flash-tts`)の分離構成
- [x] **Chat APIのJSON対応 (`chat_api.py`)**
    - [x] `generate_response` の戻り値(Dict)を直接処理するロジックへの変更
    - [x] 文字列パース処理の削除による安定化

## フェーズ66: UX調整 & 依存関係修復 [完了]
- [x] **起動時設定の最適化**
    - [x] `index.ts`: 起動時のチャットログ自動読み込み(restoreSession)を無効化（「空の状態」で開始）
- [x] **依存関係の修復**
    - [x] `src/services/resource_manager.py` の再作成 (ロールバックで消失していたファイルの復元)

## フェーズ67: Native JSON版リリース (v0.3) [完了]
- [x] **バージョン管理**
    - [x] Git Commit & Push ("v0.3 Native JSON 導入版")

## フェーズ68: Vision機能の実用化 (Clipboard Support) [完了]
- [x] **Visionモードの改善**
    - [x] Backend (`chat_api.py`): `chat_with_vision(mode="capture")` をクリップボード参照(`ImageGrab.grabclipboard`)に変更
    - [x] Frontend (`chat_manager.ts`): 右クリック時に `mode="clipboard"` を正しく送信するように修正
- [x] **UX改善**
    - [x] クリップボードが空の場合、「Win+Shift+S」の使用を促すヒントメッセージを表示
    - [x] プレビューAPI (`take_screenshot_for_preview`) の `mode` 対応

## フェーズ69: Vision機能リリース [完了]
- [x] **バージョン管理**
    - [x] Git Commit & Push ("Vision機能実装完了")

## フェーズ70: MindVault Sync (Docs連携) [完了]
- [x] **Google Docs 認証基盤**
    - [x] `services/google_auth_manager.py`: Docs API Scope の追加
- [x] **同期ロジック実装 (`docs_memory_sync.py`)**
    - [x] `DocsMemorySync` クラスの作成
    - [x] `fetch_and_split`: ドキュメント取得とマーカー分割
    - [x] `gemini-3-flash-preview` による分析プロンプト設計 (Design済)
    - [x] `analyze_content`: 分析とJSON抽出
    - [x] `update_doc`: 処理済みテキストのアーカイブ処理
- [x] **統合と保存**
    - [x] `memory/mind_vault.jsonl` への保存ロジック
    - [x] `main.py`: 起動時の非同期実行
- [x] **検証**
    - [x] 認証フロー確認
    - [x] 同期・アーカイブ動作確認

## フェーズ71: Conversation Chaos & Serendipity (v0.3.1) [完了]
- [x] **Topic Selectorの実装**
    - [x] `search_topics.yaml` と「カオス（未知のトピック）」を混ぜて提案するロジック
    - [x] Topic Selection Strategy (Comfort 70% / Chaos 30%)
- [x] **UIへの反映**
    - [x] 初期バルーン (Startup/Idle) へのランダムトピック注入
    - [x] 会話サジェスト (Suggestions) への「💡 未知のトピック」強制注入

## フェーズ72: Reliability Fixes (UrlValidator & Anti-Nagging) [完了]
- [x] **URL Hallucination対策**
    - [x] `UrlValidator`: Pythonによる死活監視（Dead Link Pruning）実装
    - [x] System Prompt: "No Guessing", "Grounding Only" の厳格化
- [x] **Repetitive Care抑制**
    - [x] System Prompt: 深夜の健康気遣いを「最初の1回」に制限
    - [x] System Prompt: 知的トピック優先（Context Priority）ルールの追加

## フェーズ73: Observability & Logging (RAG Visibility) [完了]
- [x] **RAG/Grounding ログの可視化**
    - [x] **Backend**: `ai_engine.py` (Grounding Info) と `memory_manager.py` (RAG Hit) にログ出力ロジック追加
    - [x] **Frontend**: `log_manager.ts` を修正し、`sys`, `rag`, `mind` タブへの振り分けロジックを確立
    - [x] **Bug Fix**: Python-JS間の引数順序不一致 (`log_to_debug`) を修正

## フェーズ74: Emotional Balance (Guaranteed Love Slot) [完了]
- [x] **愛の強制枠 (Love Slot)**
    - [x] `AffectionManager`: 甘え・癒やし系アクションの管理クラス作成
    - [x] `ChatApiMixin`: 会話サジェスト処理にて、感情的要素が不足している場合に強制注入するロジック実装
    - [x] **Frontend**: `ui_manager.ts` と `style.css` を更新し、`❤` プレフィックスを持つチップをピンク色で強調表示
- [x] **話題の拡張 (YAML Expansion)**
    - [x] `search_topics.yaml`: カテゴリ分け（技術、歴史、科学、癒やし）と日本語化を実施
    - [x] `InterestManager`: 階層構造化されたYAMLの読み込み（フラット化）に対応

## フェーズ75: Log Visualization 2.0 & Persona Refinement [完了]
- [x] **ログ可視化の強化 (Unified Logs)**
    - [x] **Mind Logs**: `[Mind]` タグによる思考プロセスの可視化とALLタブへの統合
    - [x] **Vision Logs**: `[Vision]` タグによる視覚認識情報のログ出力
    - [x] **RAG Logs**: `[RAG]` タグによる参照ソースの明示
- [x] **ペルソナ & 時間ロジックの刷新**
    - [x] **Active Night Logic**: AM 2:00 までは「没頭タイム」として睡眠勧告を禁止 (`time_utils.py`)
    - [x] **No Lecture Policy**: 聞かれていない講釈を禁止し、短文応答を徹底 (`[CRITICAL: NO LECTURES]`)
    - [x] **Model Upgrade**: `gemini-3.0-flash-preview` への移行と動的コンテキスト注入

## フェーズ76: Log Observability 3.0 & Living Expression
- [x] **Expression Reasoning**: ランダム表情切り替え時に「気まぐれな理由」をログに出力 (`live2d_manager.ts`)
- [x] **Mind Log Deep Dive**: 思考の「根拠・意図」を言語化させるプロンプト調整
- [x] **Vision Log Specifics**: 視覚認識時に「何（オブジェクト/テキスト）」を見たか具体的にログ出力
- [x] **RAG Log Context**: 記憶想起時に「いつの会話か」のタイムスタンプ/コンテキストを表示 (MemoryManager確認要)

## フェーズ83: Proactive L1 Research (Local Vision & Environment) [完了]
- [x] **環境構築 (Environment)**
    - [x] **Python 3.12**: GPU版 PyTorch (PaliGemma) 対応のため、3.13からダウングレード。
    - [x] **PyTorch Nightly**: RTX 5060 Ti (sm_120) 対応のため導入。
- [x] **ローカル視覚機能 (Local Vision)**
    - [x] `test_vision.py` 作成: PaliGemmaモデルのロードとCPU推論確認 (GPUはドライバ待ち)。

## フェーズ84: RTX 50 Series Support (PyTorch 2.7) [完了]
- [x] **Infrastructure**: Install PyTorch 2.7 Stable (via pip)
- [x] **Verification**: Verify CUDA availability for sm_120 (Seals Broken)
- [x] **Optimization**: Enable GPU inference in `vision_service.py`

## フェーズ85: Proactive Mode Settings UI [完了]
- [x] **Config**: Add `proactive_vision_interval_min` to `config_manager.py`
- [x] **UI**: Add "Proactive" tab to `settings.html`
    - [x] Add Interval Slider (1-60 min)
    - [x] Add "Enable/Disable" toggle (via active mode logic)
- [x] **Backend**: Update `ActiveEngine` to respect config
    - [x] Dynamic update of `vision_interval` via `configure()`

## フェーズ86: Advanced Proactive Settings (Silent & Filters) [完了]
- [x] **Config**: Add `proactive_silent_mode` and `proactive_targets` defaults
- [x] **UI**: Add controls to `settings.html`
    - [x] Silent Mode Checkbox
    - [x] Target Scope Checkboxes (Work, Media, Social, Health)
- [x] **Backend**: Update `ActiveEngine` logic
    - [x] Implement Silent Mode (Skip TTS)
    - [x] Implement Target Filtering in `_perform_vision_scan`

## フェーズ87: Reliability & Quality Fixes [完了]
- [x] **Refactor**: `ResponseParser` の完全分離と堅牢化 (思考漏れ防止)
- [x] **Bug Fix**: `gemini-3-flash-preview` 404エラーの修正 (`main.py` Config Safety)
- [x] **Bug Fix**: Proactive Modeでの英語応答漏れ (Prompt Hardening)
## フェーズ90: MindVault連携 (Docs Sync Core) [完了]
- [x] **認証基盤拡張**
    - [x] `GoogleAuthManager` に Docs API Scope を追加。
- [x] **同期の実装**
    - [x] `DocsSyncService`: 指定されたGoogle Doc ("MindVault") を定期的に取得。
    - [x] **Markdown変換**: ドキュメントの内容をMarkdown形式でローカル (`settings/MindVault.md`) に保存。
    - [x] **アーカイブ処理**: 処理済みの内容はドキュメント内で `### 保存済み` セクションへ移動 (削除せず履歴保持)。

## フェーズ91: Granular Parsing & AI Labeling [完了]
- [x] **データ認識の高度化**
    - [x] `MindLoader`: 箇条書き (`- `) を個別のエントリーとして認識する粒度解析。
    - [x] **Timestamp Parsing**: `[Archived: YYYY-MM-DD]` タグからエントリーの日時を特定。
    - [x] **Category Parsing**: `## ヘッダー` からカテゴリを自動判別。
- [x] **AIラベリング**
    - [x] `BubbleService`: 長文のメモをAI (Gemini) で15文字以内のキャッチーな短いラベルに要約し、バルーンに表示。

## フェーズ92: Bubble UX & Deep Conversation (Polish) [完了]
- [x] **能動的な思考喚起**
    - [x] **Forced Startup**: アプリ起動時、MindVaultに未読メモがあれば必ず1つをバルーンとして出現させる。
    - [x] **Manual Priority**: バルーンボタン（手動）押下時、MindVaultのメモを最優先で表示 (Love > Mind > Normal)。
- [x] **Deep Conversation Mode**
    - [x] **Grounding Off**: MindVault由来のトピックでは検索（Google Search）を**完全無効化**。
    - [x] **Empathy Prompt**: ニュースやトレンドではなく、ユーザーのメモの深層（哲学・感情）に寄り添う専用プロンプトを実装。
- [x] **Visual Feedback**
    - [x] **Purple Style**: MindVault由来のバルーンに専用のアメジスト色（紫）と発光エフェクトを適用し、他と差別化。
