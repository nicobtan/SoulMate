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