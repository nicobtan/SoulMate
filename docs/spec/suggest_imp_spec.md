# サジェスト機能拡張・高精度化 実装仕様書

## 1. 概要
ユーザーがキーボード入力を行わずに、クリックだけで「ギャルゲー」のように会話を深く、あるいは広く展開できるインターフェースを構築する。
既存の3枠から **10枠** に拡張し、文脈読解に基づいた多彩な返答パターン（同意、反論、質問など）を提示することで、ユーザー体験を「読む」から「選んで進める」へ昇華させる。

## 2. アーキテクチャ変更方針
バグの混入を防ぐため、サジェスト生成ロジックを既存の `AIEngine` から切り出し、独立したサービスクラスとして実装する。

* **新規作成**: `src/services/suggestion_engine.py`
    * **責務**: 会話履歴、ユーザープロファイル、MindVault情報を入力とし、最適な「ユーザーの返答候補」を10個生成する。
* **変更**: `src/api/chat_api.py`
    * `AIEngine` の応答生成後、`SuggestionEngine` を呼び出してリストを上書き/マージするフローを追加。
* **変更**: フロントエンド (`index.html`, `renderer.ts`)
    * 10個のボタンを綺麗に表示するためのグリッドレイアウト（2行x5列、またはスクロール）の実装。

## 3. サジェストの構成 (全10枠)

サジェストは以下の固定枠と変動枠で構成する。

### A. 固定ナビゲーション (2枠)
| 枠No | ラベル例 | 意図 (Intent) |
| :--- | :--- | :--- |
| **01** | **もっと詳しく教えて / 続けて** | **[深掘り]** 現在の話題を継続させる。 |
| **02** | **他の話題について / 話を変える** | **[転換]** 全く別の話題へ移行する。 |

### B. 文脈連動ダイナミック枠 (8枠)
AIは直前の会話とユーザーの思想（MindVault/Profile）を分析し、以下のカテゴリに当てはまる返答を生成する。

| 枠No | カテゴリ | プロンプト指示内容 |
| :--- | :--- | :--- |
| **03** | **同意・共感** | 相手の意見に強く賛同し、肯定的な感情を示す。 |
| **04** | **質問・インタラクション** | 相手の発言に対して、具体的な疑問を投げかける。 |
| **05** | **ツッコミ・ジョーク** | 相手のボケや甘えに対して、親しみを込めてツッコミを入れる。 |
| **06** | **意見伺い** | 「〇〇（ペルソナ名）はどう思う？」と相手の主観を求める。 |
| **07** | **反論・議論 (Debate)** | **あえて衝突する。** 相手の意見に対し、論理的または感情的な反対意見を述べる。 |
| **08** | **否定的意見の要求** | 自分の考えの穴を探してもらう（例：「私の考え、どこかおかしい？」）。 |
| **09** | **MindVault連携** | ユーザーの「過去の関心事」や「思想」に基づいた、ニッチな視点からの発言。 |
| **10** | **ランダム/カオス** | 予測不可能な、少し突飛だが面白い返し。 |

## 4. データ連携 (MindVault & User Profile)
サジェストの精度を高めるため、生成時のプロンプトに以下のコンテキストを注入する。

* **User Ideology (思想):** ユーザーが好む議論のスタイル（論理的、感情的、哲学的）や、過去に示した価値観。
* **MindVault (記憶):** ユーザーが「好き」と言っていたキーワードや、まだ未消化のトピック。

## 5. 実装ステップ

### Step 1: バックエンド (Python)
1.  `src/services/suggestion_engine.py` を作成。
2.  Geminiへのプロンプト設計（JSONモード強制）。
    * Input: `Conversation History`, `User Profile`, `MindVault Summary`
    * Output Schema: `List[String]` (Exactly 8 dynamic items)
3.  `ChatApi` での統合。
    * メインの会話生成 (`AIEngine`) とは非同期、または並列で実行し、レスポンスに結合する。

### Step 2: フロントエンド (TypeScript/HTML)
1.  `index.html` の `#suggestions-container` のCSSを修正。
    * FlexboxからGrid (2 columns on mobile / 5 columns on desktop, or scrollable flex) へ変更。
2.  `src/managers/ui_manager.ts` (または `renderer.ts`) の描画ロジック修正。
    * 配列が10個来ても崩れないようにする。
    * カテゴリごとに色分け（例：反論は少し赤みがかったボタンなど）ができるとなお良い。

## 6. プロンプト案 (SuggestionEngine用)

```text
[Role]
You are a specialized UI assistant generating "Response Candidates" for a "Galge" (Dating Sim) interface.
The user wants to progress the conversation by clicking buttons, not typing.

[Context]
- Persona: {persona_name} (Tone: {persona_tone})
- User Profile: {user_profile}
- Conversation History:
{history_summary}

[Task]
Generate exactly 8 dynamic response options for the USER to say next, based on the categories below.
Ensure the tone matches the User's personality (from profile).

[Categories]
1. Agreement (Positive)
2. Question (Deep Dive)
3. Tsukkomi (Playful/Teasing)
4. Ask Persona's Opinion ("What do you think?")
5. Debate/Counter-argument (Critical thinking)
6. Request Criticism ("Critique my view")
7. Personal Interest (Based on "{mindvault_topic}")
8. Unexpected/Funny

[Output Format]
JSON Array of Strings. Example:
[
  "なるほど、それは一理あるね",
  "具体的にはどういうこと？",
  "またそうやって誤魔化す！w",
  "〇〇ちゃんはどう思うの？",
  "でも、リスクについてはどう考える？",
  "私の考え、甘いかな？",
  "それってRustの所有権概念に似てるかも",
  "いきなりだけどお腹すいた"
]