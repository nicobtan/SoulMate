import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ResourceManager:
    """ペルソナやユーザープロファイルを読み込むリソース管理クラス"""
    def __init__(self, base_dir=None):
        self.base_dir = base_dir if base_dir else os.getcwd()

    def load_yaml(self, rel_path):
        """YAMLファイルを安全に読み込む"""
        try:
            # パス結合 (src/static/... を想定。設定に合わせて調整してください)
            # settings/personas/ などの可能性もあるため、柔軟に
            full_path = os.path.join(self.base_dir, rel_path)
            
            # ファイルが見つからない場合のフォールバック
            if not os.path.exists(full_path):
                # settings/personas/配下かも？
                alt_path = os.path.join(self.base_dir, "settings", "personas", os.path.basename(rel_path))
                if os.path.exists(alt_path):
                    full_path = alt_path
                else:
                    # settings/配下かも？ (user_profile.yamlなど)
                    alt_path_2 = os.path.join(self.base_dir, "settings", os.path.basename(rel_path))
                    if os.path.exists(alt_path_2):
                        full_path = alt_path_2

            if not os.path.exists(full_path):
                logger.warning(f"File not found: {rel_path}")
                return {}
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"YAML Load Error ({rel_path}): {e}")
            return {}

    def get_persona_system_prompt(self, filename="lena.yaml"):
        # ファイル名のみが渡された場合を想定してパスを探す
        data = self.load_yaml(filename)
        return data.get('system_prompt', '')

    def get_user_profile_str(self, filename="user_profile.yaml"):
        data = self.load_yaml(filename)
        if data:
            return yaml.dump(data, allow_unicode=True, default_flow_style=False)
        return "Not set"
