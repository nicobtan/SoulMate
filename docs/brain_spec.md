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
```

### ② サンプル対話集 (Few-Shot Examples)
**File:** `data/few_shot.json` -> (Runtime) -> `const DialogueSamples`

```typescript
// u = User, a = SoulMate
const DialogueSamples = [
  { u: "疲れた", a: "あらあら、お疲れ様です。少し休憩しましょうか。" },
  { u: "バグが直らない", a: "焦らないで。一度深呼吸して整理しましょう。" },
  { u: "最新のニュースは？", a: "気になる記事がありましたよ。リンクを開きましょうか？" }
];
```

### ③ ニュース収集・分析システム (The Analyst)
**Model:** `gemini-3.0-preview`
外部RSS等から収集した記事を、以下の形式で要約・構造化してメモリに格納する。

```typescript
interface NewsTopic {
  title: string;
  source_url: string;
  summary: string;       // 記事の要約 (3.0 Previewが生成)
  short_hook: string;    // ユーザーへの話題振り用の短い一言 (30文字以内)
  relevance: string;     // なぜユーザーに関連があるかの理由
}
```

### ④ 音声・動作仕様 (Voice & Motion)
**Engine:** Google Cloud Text-to-Speech API
**Library:** `google-cloud-texttospeech`

音声設定は `settings.json` に保存し、以下のパラメータでAPIを呼び出す。

```python
# Voice Configuration Structure
voice_settings = {
    # Voice Selection (Timbre)
    "language_code": "ja-JP",
    "name": "ja-JP-Neural2-B",  # Recommended: Female/Neural2 (Soft & Motherly)
    "ssml_gender": "FEMALE",

    # Audio Configuration (Acting)
    "audio_encoding": "MP3",
    "pitch": 2.0,             # +2.0: Cuter, younger tone
    "speaking_rate": 1.1      # 1.1: Brighter, faster tempo
}
```

**Recommended Voices:**
- **ja-JP-Neural2-B** (First Choice): Gentle, natural, motherly.
- **ja-JP-Standard-A**: Anime-like, cute but slightly robotic.
- **ja-JP-Standard-B**: Calm, newscaster-like.

**Motion Triggering:**
Response text will be analyzed for emotion tags (e.g. `[happy]`) or sentiment to trigger Live2D motions.
- `[happy]` -> Smile Motion
- `[angry]` -> Angry Motion
- `[sad]` -> Sad Motion

---

## 5. Active Intellect (能動的知性)

ユーザーの入力を待つだけでなく、外部情報や時間経過をトリガーに**自分から話しかける機能**。

### ① Active Engine Architecture
**File:** `src/services/active_engine.py` (Background Thread)

1.  **Idle Monitoring**:
    *   最後の会話からの経過時間を監視。
    *   例: 30分間操作がない場合 -> 「何か手伝えることはない？」
2.  **External Information (News/Weather)**:
    *   定期的にRSSフィード (`NewsCollector`) をチェック。
    *   新しい重要ニュースがあれば、`Analyst Persona` で要約し、話題としてストック。
3.  **Push Notification**:
    *   BackendからFrontendの関数 (`receiveMessage`) を呼び出し、発話を行う。

### ② News Collector & Analyst
**Source:** RSS Feeds (Yahoo, Zenn, etc.)
**Model:** `gemini-2.0-flash-exp` (Thinking/Summarization)

**Flow:**
1.  **Fetch**: RSSから最新記事を取得。
2.  **Filter**: ユーザーの興味（IT, AI, 科学など）に基づきフィルタリング。
3.  **Summarize (Analyst)**:
    *   「ユーザーに話すための短い要約」を生成。
    *   フック（導入）: 「ねえねえ、こんなニュース見た？」
4.  **Action**: ユーザーが反応したら詳細を話す。

---

## 6. System Actions & Integrations (Action Commands)

SoulMateは、AIによる会話だけでなく、特定のコマンドタグを出力することでシステム機能を実行する。
`src/api/chat_api.py` がこれをパースし、実行する。

### ① コマンド定義

| コマンド形式 | 意味 | 実行内容 |
| --- | --- | --- |
| `[ACTION:OPEN_CALENDAR]` | カレンダーを開く | ブラウザで Google Calendar を開く |
| `[ACTION:ADD_EVENT|Summary|Time]` | 予定を追加する | Google Calendar に予定を登録する |

### ② 動作フロー

1.  **Intent Detection**: ユーザーの発言から「予定」「カレンダー」を検知。
2.  **Prompt Engineering**: AIに対し「カレンダーを開いて」と言われたら **必ず** `[ACTION:OPEN_CALENDAR]` とだけ出力するよう指示 (`src/services/ai_engine.py`)。
3.  **Parsing**: Python側でAIのレスポンスを受け取り、タグが含まれていれば即座に実行。
4.  **Feedback**: 実行後、UI側で「カレンダーを開きました」等の完了メッセージを表示（または上書き）する。

これにより、「会話だけして何もしない」というハルシネーションを防ぐ。
