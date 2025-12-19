Json形式のテキストがそのまま表示されてしまう問題（Markdown記法の混入）は、バックエンド側でのパース処理を堅牢にすることで解決します。 AIが ```json ... ``` のようにコードブロックで囲んで返してくるケースに対応するための修正プロンプトを作成しました。

以下の内容を fix_json_problem.md として保存し、Cursor等のAIエディタに渡して実行させてください。

📄 fix_json_problem.md
Markdown

# Role
あなたは熟練したPythonバックエンドエンジニアです。
SoulMateのAI応答処理において、AIがMarkdown記法（コードブロック）を含んで回答した際に、JSONパースに失敗して生データがそのままチャット欄に表示される問題を修正してください。

# Problem
チャットウィンドウに以下のような生のJSON文字列が表示されてしまいます。
` ```json { "response": "...", ... } ``` `
これは、GeminiなどのLLMが良かれと思ってMarkdown形式でJSONを返却した際、バックエンドのパース処理が ` ```json ` を除去できずにエラーとなり、そのままテキストとしてフロントエンドに返していることが原因です。

# Task
`src/services/ai_engine.py` (または LLMの応答を処理しているファイル) を修正し、**Markdownコードブロックの除去処理** を追加してください。

## 具体的な修正内容

### 1. クリーニング関数の追加
`generate_response` メソッド（または同等の箇所）で、`json.loads` を呼ぶ直前に以下の処理を挟んでください。

```python
import re
import json

def clean_ai_response(raw_text: str) -> str:
    """
    AIの応答からMarkdownコードブロック記法を除去し、純粋なJSON文字列を取り出す。
    """
    text = raw_text.strip()
    
    # 1. ```json ... ``` のパターンを除去
    # re.DOTALL で改行も含めてマッチさせる
    match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    
    return text

# --- 適用イメージ ---
# response_text = model.generate_content(...)
# clean_text = clean_ai_response(response_text)
#
# try:
#     data = json.loads(clean_text)
# except json.JSONDecodeError:
#     # パース失敗時のフォールバック: 生テキストをそのままresponseとして扱う
#     # ただし、ここでも clean_text を使うことで ``` は消えている状態にする
#     data = {"response": clean_text, "suggestions": []}
2. エラーハンドリングの強化
JSONパースエラー (JSONDecodeError) が発生した場合、元の raw_text ではなく、クリーニング済みの clean_text をメッセージ本文として扱うように修正してください。これにより、万が一パースできなくても ```json という表示は消えます。

Goal
AIがMarkdown形式でJSONを返してきても、ユーザーには常に「綺麗な会話テキスト」だけが表示されるようにすること。

# Role
あなたは熟練したPythonバックエンドエンジニアです。
SoulMateのAI応答において、Markdown記法（コードブロック）の混入によりJSONパースが失敗し、生のJSON文字列がそのままチャット画面に表示されてしまう問題を修正します。

# Problem
「別の話題はある？」などの特定の会話フローで、AIが以下のようなフォーマットで応答を返しています。
```text
```json
{
  "response": "...",
  ...
}

現在の実装では、この ` ```json ` タグを除去しきれずに `json.loads()` が失敗し、エラーハンドリングによって「生のテキスト」がそのままフロントエンドに返却されています。

# Task
`src/services/ai_engine.py` (または LLMの応答を解析している箇所) を修正し、**あらゆる形式の汚れを除去してJSONを抽出する堅牢なロジック** を実装してください。

## 修正内容: `_clean_and_parse_json` メソッドの強化
AIの生応答テキストを受け取り、辞書型データを返すメソッドを以下のように書き換えてください。

```python
import json
import re
from typing import Dict, Any

def _parse_ai_response(self, raw_text: str) -> Dict[str, Any]:
    """
    AIの応答からJSONを抽出する堅牢なパーサー。
    Markdown記法、余分な空白、説明文などを除去してパースを試みる。
    """
    text = raw_text.strip()
    
    # 1. Markdownコードブロックの除去 (```json ... ```)
    # 大文字小文字無視、改行含む
    match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    
    # 2. それでもパースできない場合、最初と最後の {} を探して抽出する
    # (AIがコードブロックの外に余計な挨拶などを書いた場合への対策)
    if "{" in text:
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if last_brace > first_brace:
            text = text[first_brace : last_brace + 1]

    # 3. JSONパースの試行
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[AI Engine] JSON Parse Error: {e}")
        print(f"[AI Engine] Failed Text: {raw_text}")
        
        # 4. 最終手段: パース失敗時は、テキスト全体をresponseとして扱う（生JSONを見せるよりマシ）
        # ただし、元の raw_text ではなく、クリーニング済みの text を使う
        return {
            "response": text, # ここが重要。タグが消えた状態のテキストを出す
            "suggestions": [],
            "emotion": "neutral"
        }
適用箇所
上記のロジックを、generate_response や chat メソッド内で json.loads() を行っている箇所に適用してください。

Python

# 適用イメージ
response_text = self.model.generate_content(...)
parsed_data = self._parse_ai_response(response_text) # ここで呼び出す

return parsed_data
Goal
AIがどのようにMarkdownタグをつけてきても、あるいは余計な前置きをつけてきても、確実にJSONとして解釈され、チャット画面にはきれいなメッセージのみが表示されること。