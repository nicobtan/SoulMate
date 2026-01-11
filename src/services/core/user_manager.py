import os
import yaml
import logging

logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self, profile_path="settings/user_profile.yaml"):
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
        name = self.profile_data.get('name', 'User')
        context += f"- Name: {name}\n"
        
        if 'gender' in self.profile_data:
            context += f"- Gender: {self.profile_data['gender']}\n"
            
        if 'birthday' in self.profile_data:
            context += f"- Birthday: {self.profile_data['birthday']}\n"
            
        if 'location' in self.profile_data:
            context += f"- Location: {self.profile_data['location']}\n"
        
        # 性格・価値観
        if 'mbti' in self.profile_data:
             context += f"- MBTI: {self.profile_data['mbti']}\n"
             
        if 'values' in self.profile_data and self.profile_data['values']:
             context += f"- Values: {', '.join(self.profile_data['values'])}\n"

        # 仕事・プロジェクト（重要なので詳しく）
        if 'job_title' in self.profile_data:
             context += f"- Job Title: {self.profile_data['job_title']}\n"

        if 'tech_stack' in self.profile_data and self.profile_data['tech_stack']:
            tech = ", ".join(self.profile_data['tech_stack'])
            context += f"- Tech Stack: {tech}\n"
        
        if 'current_projects' in self.profile_data and self.profile_data['current_projects']:
            projects = self.profile_data['current_projects']
            context += f"- CURRENTLY WORKING ON: {', '.join(projects)}\n"

        # 趣味（話題の種）
        if 'games' in self.profile_data and self.profile_data['games']:
            context += f"- Favorite Games: {', '.join(self.profile_data['games'])}\n"
        
        if 'hobbies' in self.profile_data and self.profile_data['hobbies']:
             context += f"- Hobbies: {', '.join(self.profile_data['hobbies'])}\n"
        
        if 'likes' in self.profile_data and self.profile_data['likes']:
            context += f"- Interests/Topics: {', '.join(self.profile_data['likes'])}\n"
            
        # 嫌いな話題（ガードレール）
        if 'dislikes' in self.profile_data and self.profile_data['dislikes']:
            context += f"- DO NOT TALK ABOUT: {', '.join(self.profile_data['dislikes'])}\n"
            
        # ライフスタイル
        if 'sleep_cycle' in self.profile_data:
             context += f"- Sleep Cycle: {self.profile_data['sleep_cycle']}\n"

        return context

    def get_raw_profile(self):
        """プロファイルファイルの生テキストを返す"""
        if not os.path.exists(self.profile_path):
            return ""
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read raw profile: {e}")
            raise e

    def save_raw_profile(self, yaml_content):
        """YAMLテキストを保存し、データをリロードする"""
        try:
            # バリデーション: YAMLとして正しいかチェック
            # 正しくなければエラー送出 (ロードはしない)
            data = yaml.safe_load(yaml_content)
            
            with open(self.profile_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            # 再読み込み
            self.profile_data = data
            logger.info("User profile updated via raw input.")
            return True
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML content: {e}")
            raise Exception(f"YAML Syntax Error: {e}")
        except Exception as e:
            logger.error(f"Failed to save raw profile: {e}")
            raise e
