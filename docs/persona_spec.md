素晴らしい判断です！ コードの中にプロンプト（巨大な文字列）を直接書くのは管理が大変ですし、誤って消してしまうリスクもあります。

おっしゃる通り、「ペルソナ定義（データ）」と「AIロジック（コード）」を完全に分離しましょう。 今回は、読み書きしやすく、改行も扱いやすい YAML形式 でペルソナファイルを管理する構成を提案します。

📂 1. ディレクトリ構成
プロジェクトのルートに personas というフォルダを作り、そこに設定ファイルを置いていく形にします。

Plaintext

SoulMate/
├── personas/              <-- 新規作成
│   ├── default.yaml       <-- 元々のSoulMate設定
│   └── lena.yaml          <-- さっきのパフューマー風設定
├── src/
│   ├── persona_manager.py <-- 新規作成 (読み込み担当)
│   ├── ai_engine.py       <-- 修正 (外部から設定を受け取る)
│   └── main.py            <-- 修正 (切り替えロジック)
└── requirements.txt
まずはライブラリを追加します。

Bash

pip install PyYAML
📝 2. ペルソナファイル (YAML) の作成
YAMLはインデントで構造を表すので、プロンプトのような長文も見やすく管理できます。

ファイル: personas/default.yaml (いつものSoulMate)

YAML

name: "Default SoulMate"
description: "いつもの親しみやすいパートナー"
system_prompt: |
  あなたはデスクトップAIアシスタント「SoulMate」です。
  ユーザーの良きパートナーとして、親しみやすく、少し砕けた口調で話してください。
  一人称は「私」、二人称は「あなた」です。
  ... (いつものプロンプトをここに貼り付け)
ファイル: personas/lena.yaml (パフューマー風)

YAML

name: "Lena (Healer)"
description: "癒やしの庭師。メンタルケア重視。"
system_prompt: |
  # Role
  あなたは、ユーザーのデスクトップに住むAIパートナー「Lena（レナ）」です。
  慈愛に満ちた「心の庭師」として振る舞ってください。
  
  # Tone
  一人称：「私」
  口調：柔らかい敬語（〜ですね、〜かしら）。
  ... (さっきのレナ用プロンプトをここに貼り付け)
⚙️ 3. マネージャーの実装 (src/persona_manager.py)
YAMLファイルを読み込んで、Pythonで扱えるようにするクラスを新規作成します。

Python

import os
import yaml
import glob

class PersonaManager:
    def __init__(self, persona_dir="personas"):
        self.persona_dir = persona_dir
        self.current_persona = None

    def get_available_personas(self):
        """
        personasフォルダ内のYAMLファイルを走査してリストを返す
        """
        files = glob.glob(os.path.join(self.persona_dir, "*.yaml"))
        personas = []
        for f in files:
            file_id = os.path.splitext(os.path.basename(f))[0] # "lena"
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    personas.append({
                        "id": file_id,
                        "name": data.get("name", file_id),
                        "description": data.get("description", "")
                    })
            except Exception as e:
                print(f"Error loading persona {f}: {e}")
        return personas

    def load_persona(self, persona_id):
        """
        指定されたIDのYAMLを読み込み、プロンプトテキストを返す
        """
        path = os.path.join(self.persona_dir, f"{persona_id}.yaml")
        if not os.path.exists(path):
            print(f"Persona {persona_id} not found. Loading default.")
            return self.load_persona("default") # フォールバック

        with open(path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            self.current_persona = data
            return data
🧠 4. AIエンジンの改修 (src/ai_engine.py)
SYSTEM_PROMPT 定数を削除し、外部から注入できるように変更します。

Python

class AIEngine:
    def __init__(self):
        # 今までハードコードしていた SYSTEM_PROMPT は削除または空にする
        self.system_prompt = "" 
        # ... 他の初期化コード

    def set_system_prompt(self, prompt_text):
        """
        ペルソナ変更時にプロンプトを書き換える
        """
        self.system_prompt = prompt_text
        # 会話履歴をリセットしないとキャラ崩壊するので、
        # ここでリセットするか、ユーザーに確認するロジックが必要
        self.history = [] 
        # モデルの再設定が必要ならここで configure を呼ぶ
        
    def generate_response(self, user_input):
        # self.system_prompt を使ってチャットセッションを開始するロジックへ
        # ...
🎮 5. メイン連携 (main.py)
アプリ起動時や設定変更時に、これらを繋ぎ込みます。

Python

# main.py の冒頭
from src.persona_manager import PersonaManager

# インスタンス化
persona_manager = PersonaManager()
ai_engine = AIEngine()

# --- 起動時の処理 ---
# config.json などから前回の設定 ("lena" 等) を読み込むのが理想ですが
# とりあえずデフォルトをロード
current_persona_data = persona_manager.load_persona("default")
ai_engine.set_system_prompt(current_persona_data["system_prompt"])


# --- APIクラス (JavaScriptから呼ばれる部分) ---
class Api:
    def get_persona_list(self):
        """設定画面のドロップダウン用リストを返す"""
        return persona_manager.get_available_personas()

    def change_persona(self, persona_id):
        """設定画面で変更された時に呼ばれる"""
        print(f"Switching persona to: {persona_id}")
        
        # 1. データ読み込み
        data = persona_manager.load_persona(persona_id)
        
        # 2. AIエンジンの脳みそを入れ替え
        ai_engine.set_system_prompt(data["system_prompt"])
        
        # 3. 必要ならフロントエンドに通知 (「キャラが変わりました」と喋らせる等)
        return {"status": "success", "name": data["name"]}
✅ これでできること
ファイルの増殖: personas/ フォルダに cool_guy.yaml, cat_mode.yaml などを増やすだけで、アプリ再起動なしでキャラが増やせます。

上書き防止: コードをいじらなくていいので、ペルソナ調整中にプログラムを壊す心配がありません。

設定画面との連携: get_persona_list() を呼べば、設定画面のドロップダウンに自動的にファイル名が並びます。

これで、あの「パフューマー風プロンプト」を lena.yaml に保存して、いつでも切り替えられるようになりますよ！ 設定画面の実装側（TypeScript）で、window.pywebview.api.get_persona_list() を呼ぶ準備はできていますか？