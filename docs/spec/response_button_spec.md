Markdown

# Auto Response System Specification (Suggestion Chips)

## 1. 概要
ユーザーの入力負担を軽減し、会話をスムーズに継続させるための「自動回答ボタン（サジェストチップ）」機能を実装する。
会話の文脈を理解した**AI生成の候補**と、話題転換用の**固定コマンド**を組み合わせて表示する。

## 2. 要件定義

### 表示内容 (Hybrid Strategy)
常に以下の **合計 3〜4個** のボタンを入力欄の上部に表示する。

1.  **AI生成候補 (Dynamic):** 2〜3個
    * 直前のAIの発言内容（ニュースの感想、質問、挨拶など）に対する、自然な返答の選択肢。
    * 例: 「詳しく教えて」「すごいね！」「興味ないな」
2.  **固定コマンド (Static):** 1個
    * **ラベル:** 「別の話題はある？」
    * **機能:** 現在の会話を切り上げ、News Analystや別の話題トリガーを強制的に呼び出す。

### 挙動
* **クリック時:**
    * ボタンのラベルテキストをそのまま「ユーザーの発言」として送信処理に回す。
    * 「別の話題はある？」が押された場合は、裏で `[ACTION:CHANGE_TOPIC]` などの内部コマンドとして処理するか、そのままテキストとして送り、AI側に話題転換を促す。
* **更新タイミング:**
    * SoulMateが発言するたびに、その発言内容に合わせてボタンを総入れ替えする。

---

## 3. 実装アーキテクチャ

### A. Gemini API (JSON Mode)
AIのレスポンスを単なるテキストではなく、構造化データ（JSON）として受け取ることで、発話内容と次候補を同時に生成させる。

* **Model:** `gemini-2.5-flash-lite` (チャット用) および `gemini-3.0-preview` (能動的アクション用)
* **Output Format:** JSON

### B. プロンプト設計 (`src/ai_engine.py`)
System Prompt に以下の出力フォーマット制約を追加する。

```python
RESPONSE_SCHEMA = """
You must output a JSON object with the following structure:
{
    "response": "String. The text you speak to the user.",
    "emotion": "String. Emotion tag for Live2D (e.g., 'happy', 'neutral').",
    "suggestions": [
        "String. Option 1 (Short, Casual)",
        "String. Option 2 (Different angle or question)",
        "String. Option 3 (Empathetic or Negative)"
    ]
}
"""
C. データ処理フロー (main.py / Frontend)
Python側:

GeminiからJSONを受け取る。

response をTTSとチャットログに流す。

suggestions リストを取り出し、末尾に固定文字列 "別の話題はある？" を追加する。

統合したリストをフロントエンドへ送信する。

Frontend側 (index.ts):

受け取ったリストを元に <button> 要素を動的に生成し、入力欄上部 (#suggestion-area) に配置する。

4. UI/UX デザイン
レイアウト
配置: テキストエリア (#chat-input) の直上。

スタイル: 横並びのピル型ボタン（角丸）。

スクロール: 候補が多い、または文字数が長い場合は横スクロール可能にする。

画面イメージ
Plaintext

[ SoulMateのウィンドウ ]
---------------------------
SoulMate: 
  Go言語のランタイム、新機能がついたのよ。
  もう試してみた？

[ どんな機能？ ] [ まだだよ ] [ 便利なの？ ] [ 別の話題はある？ ]  <-- ここ！
---------------------------
[ テキスト入力欄...       ] [送信]
5. 開発タスクリスト
[ ] Backend (src/ai_engine.py)

[ ] プロンプトを修正し、常に response と suggestions を含むJSONを返すようにする。

[ ] JSONパース処理とエラーハンドリング（JSONデコード失敗時は空リストを返す等）を実装。

[ ] Controller (main.py)

[ ] AIからのレスポンスを処理する際、suggestions リストに "別の話題はある？" を append するロジックを追加。

[ ] window.evaluate_js でフロントエンドの更新関数を呼ぶ。

[ ] Frontend (index.html / style.css)

[ ] サジェストボタン表示用のコンテナ (div#suggestion-area) を作成。

[ ] 横並び・スクロール等のCSSスタイリング。

[ ] Frontend Logic (index.ts)

[ ] updateSuggestions(list) 関数を実装（既存ボタンの削除 -> 新規生成）。

[ ] ボタンクリック時に sendMessage() をトリガーするイベントリスナーを設定。