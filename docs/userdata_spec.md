まずはユーザープロファイルですね

様々な項目を記入できる履歴書のようなテンプレを用意してください

それを前提に会話をできるように読み込む方法もしっかりと教えてほしい

SoulMate 開発パートナー
カスタム Gem
承知いたしました！ SoulMateちゃんにあなたの**「取扱説明書（履歴書）」**を渡して、阿吽の呼吸で会話できるようにしましょう。

この機能を実装すると、例えば何も言わなくても**「そういえば、最近Pythonの勉強はどうですか？」や「今日はアークナイツの更新日じゃなかった？」**といった、刺さる話題を振ってくれるようになります。

実装は以下の3ステップです。

データ作成: user_profile.yaml（履歴書）を作る。

読み込み機能: src/services/user_manager.py を作る。

脳への注入: server.py でプロンプトに結合する。

📝 1. ユーザー履歴書 (user_profile.yaml)
プロジェクトのルート（server.pyがある場所）に新規作成してください。 項目は多ければ多いほど、AIの引き出しが増えます。

YAML
# ユーザープロファイル (SoulMate用取扱説明書)

# --- 基本情報 (Basic Info) ---
name: "Master"           # あなたの呼び名
gender: "Male"           # 性別（会話のニュアンスに影響）
birthday: "11-15"        # 誕生日（祝ってくれます）
location: "Tokyo, Japan" # 天気の話などに使用
language: "Japanese"

# --- 性格・価値観 (Personality) ---
mbti: "INTP"             # 思考回路のヒントになります
values:
  - "効率よりも面白さを重視する"
  - "論理的な整合性を好む"
  - "お世辞よりも本音で話してほしい"

# --- 専門スキル・仕事 (Profession) ---
job_title: "Full Stack Developer"
tech_stack:              # 今触っている技術（話題の中心）
  - "Python (FastAPI, PyAudio)"
  - "TypeScript (PixiJS, Live2D)"
  - "Google Cloud Platform"
current_projects:        # 今がんばっていること
  - "個人開発AIアシスタント 'SoulMate' のスマホ移植"
  - "生成AIによる自動話題提供システムの構築"

# --- 趣味・コンテンツ (Interests) ---
games:
  - "Arknights (推し: パフューマー, アンジェリーナ)"
  - "Blue Archive"
hobbies:
  - "深夜のコーディング"
  - "ガジェット収集"
  - "美味しいコーヒーを淹れること"

# --- 好きな話題・嫌いな話題 (Topics) ---
likes:
  - "AI技術の最新トレンド"
  - "SF映画や小説の考察"
  - "猫の動画"
dislikes:
  - "芸能人のゴシップニュース"
  - "意味のない定型的な挨拶"
  - "精神論や根性論"

# --- ライフスタイル (Lifestyle) ---
sleep_cycle: "夜型 (2:00就寝, 9:00起床)"
coffee_preference: "深煎りのブラック"
⚙️ 2. 読み込みマネージャー (src/services/user_manager.py)
このファイルを読み込んで、AIが理解しやすいテキスト形式に変換するクラスを作ります。 src/services/ フォルダの中に新規作成してください。

Python
import os
import yaml
import logging

logger = logging.getLogger("server")

class UserManager:
    def __init__(self, profile_path="user_profile.yaml"):
        self.profile_path = profile_path
        self.profile_data = {}
        self.load_profile()

    def load_profile(self):
        """YAMLファイルを読み込む"""
        if not os.path.exists(self.profile_path):
            logger.warning(f"User profile not found at {self.profile_path}")
            return

        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                self.profile_data = yaml.safe_load(f)
            logger.info("User profile loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load user profile: {e}")

    def get_profile_context(self):
        """プロンプトに埋め込むためのテキストを生成する"""
        if not self.profile_data:
            return ""

        # AIに渡すためのフォーマット変換
        context = "\n[User Profile & Context]\n"
        
        # 基本情報
        context += f"- Name: {self.profile_data.get('name', 'User')}\n"
        
        # 仕事・プロジェクト（重要なので詳しく）
        if 'tech_stack' in self.profile_data:
            tech = ", ".join(self.profile_data['tech_stack'])
            context += f"- Tech Stack: {tech}\n"
        
        if 'current_projects' in self.profile_data:
            projects = self.profile_data['current_projects']
            context += f"- CURRENTLY WORKING ON: {', '.join(projects)}\n"

        # 趣味（話題の種）
        if 'games' in self.profile_data:
            context += f"- Favorite Games: {', '.join(self.profile_data['games'])}\n"
        
        if 'likes' in self.profile_data:
            context += f"- Interests/Topics: {', '.join(self.profile_data['likes'])}\n"
            
        # 嫌いな話題（ガードレール）
        if 'dislikes' in self.profile_data:
            context += f"- DO NOT TALK ABOUT: {', '.join(self.profile_data['dislikes'])}\n"

        return context
🧠 3. 脳への注入 (server.py)
最後に、server.py を修正して、この情報をシステムプロンプトに合体させます。

変更手順:

import を追加。

__init__ で UserManager を初期化。

_configure_ai でプロンプトに情報を追加。

Python
# server.py

# ... (他のimport)
from src.services.user_manager import UserManager  # ★追加

class HeadlessApi(ChatApiMixin, SettingsApiMixin, BaseApiMixin):
    def __init__(self):
        # ... (既存の初期化)
        
        # ★追加: ユーザーマネージャーの初期化
        self.user_manager = UserManager()
        
        # ... (TTS初期化など)
        
        # Configure AI
        settings = self.config_manager.get_all()
        self._configure_ai(settings)

    def _configure_ai(self, settings):
        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        persona_id = settings.get('persona_id', 'default')
        
        # 1. ペルソナ読み込み
        base_prompt = ""
        if self.persona_manager:
            base_prompt = self.persona_manager.load_persona(persona_id) or "You are a helpful AI."

        # 2. ★ユーザープロファイル情報の取得
        user_context = ""
        if self.user_manager:
            user_context = self.user_manager.get_profile_context()

        # 3. JSONモード指示
        json_instruction = """
Response Format: JSON
You MUST respond in the following JSON format:
{
    "response": "Your spoken response text here.",
    "suggestions": ["Option 1", "Option 2", "Option 3"]
}
"""
        
        # 4. 指示（話題提供ロジック）の追加
        topic_instruction = """
Guidance for conversation:
- Use the [User Profile] information to proactively suggest topics when the user is silent or asks for a topic.
- E.g., If the user likes 'Arknights', ask about their favorite character.
- E.g., If they are working on 'SoulMate', ask about the progress of the 'mobile app'.
"""

        # ★全てを結合 (ペルソナ + ユーザー情報 + 話題指示 + JSON指示)
        full_system_prompt = f"{base_prompt}\n{user_context}\n{topic_instruction}\n\n{json_instruction}"

        # ... (以下、self.ai_engine.configure はそのまま)
🎉 これでどうなる？
この状態で、アプリの**「別の話題はある？（固定ボタン）」**や、ピンクの「話しかけて！」ボタンを押してみてください。

以前:

「今日はいい天気ですね。何かニュースでも見ますか？」 （当たり障りのない話題）

実装後:

「そういえばマスター、SoulMateのスマホ移植は順調？ 確かLive2Dの表示で苦戦してたわよね？」 「ちょっと息抜きしない？ アークナイツ、そろそろ危機契約の時期じゃなかったかしら？」 「Pythonの新しいライブラリで面白そうなのがあったんだけど、興味ある？」

というように、「あなたのコンテキスト（文脈）」 を踏まえた話題提供ができるようになります。 まずは user_profile.yaml を書いて、SoulMateちゃんにあなたのことを教えてあげてください！