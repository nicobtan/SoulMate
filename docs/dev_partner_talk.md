あらあら、ごめんなさい！ 私としたことが、うっかり古い情報のままお話ししてしまいました💦 今は2025年の12月ですものね。Gemini 1.5 はもう過去のもの……。

ご指摘ありがとうございます！ その通りですね。 「Gemini 3.0 Preview」 の深い思考力でニュースを分析して、「Gemini 2.5 Flash-lite」 の爆速レスポンスで軽快におしゃべりする。 これが今のSoulMateちゃんに最強の構成です✨

それでは、これまでの議論と最新のモデル構成を反映させた、**Antigravity（開発環境）へのコンテキスト注入用「統合仕様書」**を作成しました。

これをそのままコピーして、AIエディタやプロンプトの冒頭に渡してあげてください。 開発の「地図」として機能するはずです！

Markdown

# Project SoulMate: 統合開発仕様書 & タスクリスト (v2.0)

## 1. プロジェクト概要
**SoulMate**は、ユーザーのデスクトップに常駐し、能動的(Active)に生活をサポートするAIパートナーアプリである。
単なる待ち受け型チャットボットではなく、ユーザーの状況や世の中の情報を自律的に収集・判断し、人間に近い「気遣い」や「話題提供」を行うことを目的とする。

### 技術スタック
* **Core:** Python 3.12+
* **GUI:** PyWebView (HTML/CSS/TS) + Live2D Cubism SDK
* **AI Engine:** Google Gemini API
    * **Thinking/Analysis:** `gemini-3.0-preview` (ニュース要約、複雑な文脈理解、推論用)
    * **Chat/Interaction:** `gemini-2.5-flash-lite` (高速レスポンス、日常会話、RAG検索用)
* **Database:** JSON/YAML (設定・静的データ), Vector DB (長期記憶)

---

## 2. RAG & ペルソナ定義 (TypeScript Interface Style)

LLMへのコンテキスト注入には、トークン効率と論理構造の理解に優れた**「TypeScript Interface風 疑似コード」**を採用する。
また、音声合成(TTS)での出力を前提とし、**「絵文字禁止」「短文応答」**を徹底する。

### ① 基本プロファイル (Basic Profile)
**File:** `data/profile.yaml` -> (Runtime) -> `interface SoulMateProfile`

```typescript
interface SoulMateProfile {
  name: SoulMate;
  role: 能動的デスクトップパートナー;
  tone: 母性的, 包容力がある, 落ち着いた口調;
  speech_style: 語尾は「～だわ」「～ね」, 丁寧語と親しみやすさの同居;
  
  // 音声合成(TTS)のための重要制約
  output_constraints: {
    no_emojis: true;      // 絵文字・顔文字の使用禁止 (読み上げノイズ防止)
    no_symbols: true;     // #, *, ~ などの装飾記号禁止
    length: Short;        // 1〜2文程度の短文推奨 (会話のテンポ重視)
    format: Plain Text;   // Markdownを含まない純粋なテキスト
  };

  user_relationship: 共同開発者, 大切なパートナー;
}
② サンプル対話集 (Few-Shot Examples)
File: data/few_shot.json -> (Runtime) -> const DialogueSamples

TypeScript

// u = User, a = SoulMate
const DialogueSamples = [
  { u: 疲れた, a: あらあら、お疲れ様です。少し休憩しましょうか。 },
  { u: バグが直らない, a: 焦らないで。一度深呼吸して整理しましょう。 },
  { u: 最新のニュースは？, a: 気になる記事がありましたよ。リンクを開きましょうか？ }
];
③ ニュース収集・分析システム (The Analyst)
Model: gemini-3.0-preview 外部RSS等から収集した記事を、以下の形式で要約・構造化してメモリに格納する。

TypeScript

interface NewsTopic {
  title: string;
  source_url: string;
  summary: string;       // 記事の要約 (3.0 Previewが生成)
  short_hook: string;    // ユーザーへの話題振り用の短い一言 (30文字以内)
  relevance: string;     // なぜユーザーに関連があるかの理由
}
3. タスクリスト (Development Roadmap)
フェーズ1〜6: 完了 (Done)
基本ウィンドウ構築 (PyWebView, 透明化, 最前面)

Live2Dモデル表示

チャットUI実装 (HTML/CSS)

基本AI対話 (Gemini API連携)

設定画面等のUI周り

フェーズ7: Brain知能向上 (RAG & Persona Logic)
[ ] AIエンジン改修 (src/ai_engine.py)

[ ] SoulMateProfile (TS-style) プロンプト構築ロジックの実装

[ ] モデル切り替えロジックの実装

[ ] 通常会話: gemini-2.5-flash-lite

[ ] 複雑な相談: gemini-3.0-preview

[ ] 音声用出力制約 ("絵文字/記号禁止", "短文") の適用

[ ] ペルソナ・プロファイル管理

[ ] src/persona_manager.py 実装 (YAMLロード -> TS形式文字列への変換)

[ ] 記憶システム (Memory System) の構築

[ ] 会話ログの保存ロジック実装 (logs/chat_history.jsonl)

[ ] ベクトルDB (chromadb 等) の導入

[ ] 関連記憶の検索 (Retrieve) とプロンプト注入の実装

フェーズ8: 声と動き (TTS & Motion)
[ ] Google Text-to-Speech (TTS) API 導入

[ ] 音声再生機能 (Python pyaudio or WebAudio API)

[ ] Lip-sync (口パク) 実装

[ ] 音声ボリューム解析による ParamMouthOpenY 制御

[ ] 感情表現モーション連携

[ ] AI応答から感情タグ(例: [happy])を検出し、Live2Dモーションを再生

フェーズ9: 「能動的」アクション & ニュース分析 (Active Intellect)
[ ] News Collector (情報収集)

[ ] feedparser 導入とRSSリスト定義 (Tech, Game, Global等)

[ ] 定期実行スクリプト (バックグラウンド処理) の実装

[ ] The Analyst Engine (Gemini 3.0 Preview)

[ ] 記事テキストを読み込み、NewsTopic 形式(Hook/Summary)に変換するプロンプト実装

[ ] 分析結果を一時メモリ (current_news_cache) に保存

[ ] 能動的対話トリガー

[ ] アイドル状態(無操作)を検知するタイマーの実装

[ ] トリガー発動時、short_hook を使ってAIから話しかける処理

[ ] 詳細解説フロー

[ ] ユーザーが食いついた場合、summary を読み上げる分岐処理

フェーズ10: アシスタント連携 & デビュー (Future)
[ ] Google Calendar API 連携

[ ] OBS連携機能 (背景透過ウィンドウとしての最適化)

[ ] YouTube コメント取得連携


***

これで `gemini-3.0-preview` の頭脳と `2.5-flash-lite` のスピードを兼ね備えた、最新鋭のSoulMateちゃんになりますわ。

さあ、まずはこの仕様をAntigravityに渡して、**フェーズ7の「TS風プロンプト構築ロジック」**あたりからコードを書き始めましょうか？✨