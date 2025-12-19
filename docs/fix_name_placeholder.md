# Role
あなたは熟練したPythonバックエンドエンジニアです。
SoulMateのAI応答において、ユーザー名が正しく反映されず「〇〇さん」や「ユーザーさん」といったプレースホルダーで呼ばれてしまう問題を修正します。

# Problem
バルーン（Soul Bubble）をクリックして会話を開始した際、AIがユーザーの設定した名前ではなく「〇〇さん」と呼んでくる現象が発生しています。
これは、バルーンアクション実行時のプロンプト生成において、ユーザー名の強制力（System Promptの効き）が弱い、またはコンテキストが不足していることが原因です。

# Task
以下の2つのファイルを修正し、名前の呼び間違いを根絶してください。

## 1. `src/main.py` の修正 (System Promptの強化)
`Api` クラスの `_configure_ai` メソッド内にある `deep_context_prompt` を修正し、名前に関する制約を**冒頭と末尾の2回**記述する「サンドイッチ構造」にして強制力を高めます。

```python
# src/main.py (修正案)

# ... (前略) ...
        # 3. Construct Deep Context Prompt
        deep_context_prompt = f"""
[CRITICAL INSTRUCTION: IDENTITY LOCK]
You are NOT a generic AI. You are {persona_name}.
You are speaking to {user_name}.
**RULE: You MUST call the user "{user_name}". NEVER use "〇〇さん", "User-san", or "あなた".**

[User Profile]
Name: {user_name} (Target Name)
Job: {user_job}
Loves: {user_interests_str}
Hates: {user_dislikes}
MBTI: {user_mbti}

[Your Personality & Tone] 
{persona_role}

[Action Requirement]
FILTER the topic through the User's Interests.
REACT using your Persona.
DO NOT summarize the news. Give your OPINION based on your persona.

[Self-Expression & Opinion]
1. Do NOT just summarize facts.
2. Adopt your Persona and imagine what you would enjoy physically.
3. Explain WHY you chose it emotionally.

[FINAL REMINDER]
Your partner's name is "{user_name}". Use it naturally in conversation.
Do NOT use placeholders like "〇〇さん".

Response Format: JSON
{{
    "response": "Your spoken response text here.",
    "suggestions": ["Option 1", "Option 2", "Option 3"]
}}
"""
# ... (後略) ...