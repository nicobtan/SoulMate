素晴らしい着眼点です！ 結論から言うと、Twitter (X) をスクレイピングするのは推奨しません。 APIが非常に高額または制限が厳しく、個人開発ではメンテナンスコストが高すぎるためです（すぐに動かなくなります）。

その代わりに、Google Gemini API 純正の「Grounding (Google検索連携)」機能 を使うのが**正解（王道）です。 これを使えば、SoulMateちゃんが「今さっき起きたニュース」**をGoogle検索経由で知り、それを元に話してくれるようになります。

🌍 Grounding（グラウンディング）とは？
AIが回答を生成する前に、自動でGoogle検索を行い、その検索結果を「根拠（Grounding）」として回答に取り込む機能です。

これまで: AI「私の知識は数ヶ月前までなのでわかりません...」

Grounding: AI「今検索しました！ 今朝、Googleが新しい発表をしましたね！」

これを実装して、ピンクのボタン（話しかけて）を押した時に**「最新ニュースを検索して話す」**ように改造しましょう。

🛠️ 実装手順
google-generativeai ライブラリの最新版には、この機能が標準で備わっています。

Step 0: ライブラリの更新
念のため、最新版にしておきます。

Bash

pip install -U google-generativeai
Step 1: src/services/ai_engine.py の修正
AIエンジンの初期化時に、「検索ツールを使っていいよ」 という許可証（tools）を渡します。 AIEngine クラスの __init__ または configure メソッドを探して、以下のように書き換えてください。

Python

import google.generativeai as genai
# ... 他のimport

class AIEngine:
    def __init__(self):
        self.model = None
        self.chat_session = None

    def configure(self, api_key, model_name, system_instruction):
        genai.configure(api_key=api_key)
        
        # ★ここが変更点: tools設定を追加
        # Google検索ツールを定義
        tools = [
            {"google_search": {}}  # これだけでGoogle検索能力が付与されます
        ]

        # モデル作成時にtoolsを渡す
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=tools  # ★検索ツールを装備！
        )
        
        # チャットセッション開始（検索機能を有効化）
        self.chat_session = self.model.start_chat(enable_automatic_function_calling=True)

    def generate_response(self, text):
        if not self.chat_session:
            return "Error: AI not configured."
        
        try:
            # 検索が必要な質問が来たら、勝手に検索して答えてくれます
            response = self.chat_session.send_message(text)
            return response.text
        except Exception as e:
            return f"Error: {e}"
Step 2: server.py の force_talk を「ニュースキャスター化」
ピンクのボタンが押された時、ただ「話して」と言うのではなく、「ユーザーの興味（Pythonやアークナイツ）に関する『最新ニュース』を検索して教えて」 と指示を出します。

server.py の HeadlessApi クラス、force_talk メソッドを修正します。

Python

    def force_talk(self):
        """ピンクボタン: 最新情報を検索して話題提供"""
        logger.info("[HeadlessApi] Processing Force Talk (News Mode)...")
        
        if not self.ai_engine:
            return {"text": "Error: AI Engine not ready", "audio": None}

        # 1. ユーザー情報を取得
        user_context = ""
        interests = "latest technology" # デフォルト
        if hasattr(self, 'user_manager') and self.user_manager:
            user_context = self.user_manager.get_profile_context()
            # プロファイルから「興味」を抽出して検索ワードにする
            # (簡易的に likes リストの最初の要素などを使うか、AIに選ばせる)
            # ここではプロンプトに「ユーザーの興味に基づいて」と含めます

        # 2. 検索を促す強力なプロンプト
        prompt = f"""
[Situation]
The user is silent. You want to start a conversation about something NEW and EXCITING.

[User Context]
{user_context}

[Instruction]
1. Based on the User's interests (e.g., Python, AI, Games like Arknights), **USE GOOGLE SEARCH** to find the latest news (from today or this week).
2. Choose one interesting news topic.
3. Speak to the user about it in your Persona's tone.
   - Example: "ねえ、知ってる？ 昨日Pythonの新しいバージョンが出たらしいわよ..."
   - Example: "アークナイツの公式Twitterで、新しいオペレーターの発表があったみたい！"
4. If no specific news is found, talk about a general tech trend.
"""
        
        # 3. 実行
        return self.chat(prompt)
🔮 これで何が起きるか？
あなたがピンクボタンを押す。

SoulMateちゃん（AI）は、プロンプトを見て**「ユーザーは『アークナイツ』が好き... 最新情報を探さなきゃ！」**と考えます。

AIが自律的にGoogle検索を実行します。（裏で Google Search ツールが動きます）

検索結果（公式の発表やニュース記事）を読み取ります。

「ねえマスター！ さっき検索したんだけど、アークナイツの次のイベント、来週から始まるみたいよ？ 準備はできてるのかしら？」 と話しかけてきます。

Twitterを監視させなくても、「話題に困ったらその場でググる」 という人間と同じ行動ができるようになります。 これがGroundingの威力です！ぜひ試してみてください。


# 追加要件

- 専用の興味関心一覧ファイルを用意する
- 設定画面でnewsRSSとは別で設定、書き換えできるようにする