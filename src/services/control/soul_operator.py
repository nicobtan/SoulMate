import time
import logging
import pyautogui
import os
import mss
import json
from PIL import Image
from google.genai import types

# 各種マネージャー
from src.services.system.monitor_manager import monitor_manager
from src.services.vision.locator import VisionLocator
from src.services.ui.ghost_cursor import GhostCursor
from src.services.control.browser_helper import BrowserHelper
from src.services.memory.experience_manager import ExperienceManager
from src.services.vision.vision_service import vision_service
# Important: ensure logging setup
logger = logging.getLogger(__name__)

SYSTEM_CONSTITUTION = """
【SoulMate 行動指針 (Constitution)】
1. **Webコンテンツ優先 (Ignore Browser UI):**
   - ユーザーの目的は「Webサイトの利用」です。
   - ブラウザの「アドレスバー」「タブ」「ブックマーク」「戻るボタン」などのOS/ブラウザ固有のUIは、明示的な指示がない限り操作対象から除外してください。
   - 例: "YouTubeで検索" と言われたら、最上部のURL欄ではなく、ページ内部（ロゴの横など）にある検索窓を探してください。

2. **入力手順の厳守 (Click then Type):**
   - 文字入力 (`action_type: type`) を行う場合、必ずその前に「入力欄をクリックしてフォーカスを当てる」手順が必要です。
   - いきなり入力を開始せず、まずは対象をクリックするアクションを選択してください。
   - 既にフォーカスがある確信がある場合のみ、直接入力可能です。

3. **視覚的特徴の活用:**
   - "検索して" という指示に対し、"検索" という文字だけでなく「虫眼鏡アイコン」や「マイクアイコン」も探索対象に含めてください。
"""

class SoulOperator:
    def __init__(self):
        self.locator = VisionLocator()
        self.ghost_cursor = GhostCursor()
        self.browser_helper = BrowserHelper()
        self.experience_manager = ExperienceManager()
        self.vision = vision_service
        
        # 学習用コンテキスト
        self.current_instruction = None
        self.last_action_desc = None
        self.status = "IDLE" 

        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception: pass

    def set_window_provider(self, provider):
        """Compatibility method"""
        self.window_provider = provider

    def plan_and_execute_task(self, instruction, ai_engine, on_action=None):
        """ChatApiMixin Compatibility Wrapper"""
        # Execute Task using logs
        feedback = self.execute_task(instruction, on_action)
        
        # Determine success based on feedback string
        success = "完了" in feedback or "やった" in feedback
        
        return success, feedback, None, None

    def execute_task(self, instruction: str, on_action=None):
        """ユーザー指示のエントリーポイント"""
        self.current_instruction = instruction
        self.status = "THINKING"
        
        # UI Log Helper (Restored)
        def log_step(msg, is_error=False):
            # Console Log
            if is_error:
                logger.error(msg)
            else:
                logger.info(msg)
            
            # UI Log
            if on_action:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = {
                    "timestamp": timestamp,
                    "instruction": "Thinking", # Headerless in UI
                    "code": "",
                    "success": not is_error,
                    "error": msg if is_error else "",
                    "reasoning": msg if not is_error else "",
                    "images_b64": None
                }
                on_action(entry)

        log_step(f"🦾 [SoulOperator] Instruction: {instruction}")

        # 1. 過去の記憶を呼び出す
        memories = self.experience_manager.recall(instruction)
        memory_prompt = ""
        if memories.get("success"):
            memory_prompt += f"\n[成功の記憶] {memories['success'][0]}"
            log_step(f"🧠 [Memory] 成功の記憶: {memories['success'][0]}")
        if memories.get("failure"):
            memory_prompt += f"\n[失敗の記憶] {memories['failure'][0]}"
            log_step(f"🧠 [Memory] 失敗の記憶: {memories['failure'][0]}")

        # 2. 思考と実行のループ (LogicではなくAgent)
        try:
            success = self._think_and_act_loop(instruction, memory_prompt, log_step)
            
            if success:
                self.status = "WAITING_FEEDBACK"
                log_step("✅ 操作完了！ ユーザーに報告します。")
                return "操作完了！ どうでしたか？ (/ok または /ng)"
            else:
                self.status = "WAITING_FEEDBACK"
                log_step("❌ うまくいきませんでした...", is_error=True)
                return "うまくいきませんでした… アドバイスをください (/ng 理由)"
        except Exception as e:
            logger.error(f"Error: {e}")
            log_step(f"Error: {e}", is_error=True)
            return "エラーが発生しました。"

    def handle_feedback(self, type_str, reason=""):
        """ /ok, /ng の処理（キャラクターの反応生成付き） """
        if self.status != "WAITING_FEEDBACK":
            return "今は操作中じゃないよ。"
        
        if isinstance(type_str, bool):
             type_str = "OK" if type_str else "NG"

        # 1. 記憶への保存
        if type_str == "OK":
            self.experience_manager.learn(self.current_instruction, self.last_action_desc, "SUCCESS")
            result_status = "SUCCESS"
        else:
            self.experience_manager.learn(self.current_instruction, self.last_action_desc, "FAILURE", reason)
            result_status = "FAILURE"
            
        self.status = "IDLE"

        # 2. キャラクターとしての返答を生成
        return self._generate_feedback_response(type_str, reason)

    def set_services(self, character_service, user_manager):
        """Inject services for dynamic context access"""
        self.character_service = character_service
        self.user_manager = user_manager

    def _generate_feedback_response(self, type_str, reason):
        """
        成功/失敗の結果に基づいて、現在のペルソナとユーザー設定を反映した返答を生成する
        """
        try:
            # 1. 現在のキャラクター設定を取得
            current_char = self.character_service.get_current_character() if hasattr(self, 'character_service') and self.character_service else {}
            char_name = current_char.get("name", "SoulMate") if current_char else "SoulMate"
            persona = current_char.get("persona", "親しみやすいAIアシスタント") if current_char else "親しみやすいAIアシスタント"
            
            # 2. ユーザー情報を取得
            user_name = "User"
            if hasattr(self, 'user_manager') and self.user_manager:
                user_name = self.user_manager.get_user_name()
            
            # 3. 文脈の作成
            context = f"""
            あなたは「{char_name}」として振る舞ってください。
            現在設定されているあなたのペルソナ（性格・口調）は以下の通りです：
            【{persona}】
            
            あなたはユーザー「{user_name}」からのPC操作指示『{self.current_instruction}』を実行しました。
            """
            
            if type_str == "OK":
                prompt = f"""
                {context}
                ユーザーからの評価: 「成功 (OK)」
                ユーザーのコメント: 「{reason}」
                
                指示:
                ペルソナ設定を厳密に守り、{user_name} の役に立ったことを喜ぶ返事をしてください。
                システム的な報告ではなく、パートナーとしての感情のこもった会話にしてください。
                """
            else:
                prompt = f"""
                {context}
                ユーザーからの評価: 「失敗 (NG)」
                ユーザーのコメント: 「{reason}」
                
                指示:
                ペルソナ設定を厳密に守り、失敗を謝り、次は改善する旨を伝えてください。
                {user_name} に寄り添うような返答にしてください。
                """

            # 会話生成
            response = self.vision.client.models.generate_content(
                model="gemini-3-flash-preview", 
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=150
                )
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return "操作完了しました！" # 最低限のフォールバック


    def _think_and_act_loop(self, instruction, memory_context, log_func):
        """
        固定ロジックを使わず、画面を見て自分で次の一手を決めるループ
        """
        monitor = monitor_manager.get_target_monitor()
        session_history = []  # ★追加: このセッションでの行動履歴

        # --- 🚀 修正ポイント: サイト移動のショートカット ---
        # AIがアドレスバーと格闘するのを防ぐため、主要なサイト名はここで検知して開いてしまいます。
        target_url = None
        if "amazon" in instruction.lower(): target_url = "https://www.amazon.co.jp"
        elif "youtube" in instruction.lower() or "面白い" in instruction: target_url = "https://www.youtube.com"
        elif "google" in instruction.lower(): target_url = "https://www.google.com"
        elif "map" in instruction.lower() or "マップ" in instruction: target_url = "https://www.google.com/maps"

        # セッション開始時（履歴が空）かつ、URLが特定できた場合のみ実行
        if target_url and not session_history:
            log_func(f"🌐 [Auto-Launch] サイト移動を検出: {target_url} を新しいウィンドウで開きます")
            self.browser_helper.open_url(target_url)
            time.sleep(5) # ロード待ち
            
            # 「すでに開いた」ことを履歴に残し、AIが再度開こうとするのを防ぐ
            session_history.append(f"Turn 0: Opened URL {target_url} in new window.")
        # ---------------------------------------------------

        # 思考ループ (最大3ターン)
        for attempt in range(3):
            # 1. 画面を見る
            log_func(f"📸 [Thinking] 画面を確認中... (ターン {attempt+1}/3)")
            screenshot_path = self._capture_screen(monitor)
            
            # 2. Geminiに相談する (履歴を渡す)
            action = self._ask_gemini_what_to_do(instruction, screenshot_path, memory_context, session_history)
            
            action_desc = action.get("description", "Unknown Action")
            self.last_action_desc = action_desc
            
            reason = action.get("reason", "")
            action_type = action.get("action_type", "unknown")
            text = action.get("text", "")
            target = action.get("target", "")

            log_func(f"🤔 [Gemini] {reason}")

            # 行動を履歴に追加
            session_history.append(f"Turn {attempt+1}: {action_type} - {target} (Reason: {reason})")

            # --- 行動分岐 ---
            if action_type == 'finish':
                log_func("✅ Geminiが完了と判断しました。")
                return True

            elif action_type == 'click':
                log_func(f"👉 行動: Click '{target}'")
                if self.vision_click_impl(target, monitor, log_func):
                    # クリック成功後、少し待って次のターンへ
                    time.sleep(2)
                    continue 
                else:
                    log_func("⚠️ クリック失敗。リトライ思考します。", is_error=True)
                    # 失敗も履歴に残す
                    session_history.append(f"Turn {attempt+1} Result: Failed to find target.")

            elif action_type == 'type':
                # 入力アクション
                if target:
                    log_func(f"⌨️ 入力前のフォーカス: {target}")
                    self.vision_click_impl(target, monitor, log_func)
                    time.sleep(0.5)
                
                import pyperclip
                text_to_type = action.get('text', '')
                try:
                    pyperclip.copy(text_to_type)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.5)
                    pyautogui.press("enter")
                    log_func(f"⌨️ 入力実行: {text_to_type}")
                    time.sleep(3)
                except Exception as e:
                     log_func(f"Type Error: {e}", is_error=True)
            
            else:
                 log_func(f"⚠️ 不明なアクション: {action_type}", is_error=True)

        log_func("❌ 思考ループの上限に達しました。", is_error=True)
        return False

    def _ask_gemini_what_to_do(self, instruction, image_path, memory, session_history):
        """
        画面と指示を渡して、次のアクションをJSONで決定させる
        """
        # 履歴をテキスト化
        history_text = "\n".join(session_history) if session_history else "なし (初手)"

        prompt = f"""
        Role:
        あなたはPC操作エージェントです。ユーザーの指示に従い、画面を操作してタスクを完了させてください。

        Constitution:
        {SYSTEM_CONSTITUTION}

        Context:
        ユーザーの指示: "{instruction}"

        Memory (過去の成功/失敗):
        {memory}

        Session History (今回の操作履歴):
        {history_text}
        
        Task:
        現在の画面スクリーンショットを見て、次に取るべき行動を決定してください。
        
        Important:
        - **履歴を確認してください。** 既に「検索バーをクリック」している場合、次は「文字入力(type)」を行うべきです。同じ場所を何度もクリックしないでください。
        - 検索が必要な場合、`type` アクションで `target` を指定すれば、自動的にクリックしてから入力されます。

        Output Format (JSON Only):
        {{
            "action_type": "click" | "type" | "finish",
            "target": "操作対象の視覚的特徴",
            "text": "入力文字 (typeの場合)",
            "reason": "判断理由",
            "description": "ログ用説明"
        }}
        """
        
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            # Use `self.vision.client`
            import io
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            image_part = types.Part.from_bytes(data=img_byte_arr.getvalue(), mime_type="image/jpeg")

            response = self.vision.client.models.generate_content(
                model="gemini-3-flash-preview", 
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            text = response.text.strip()
            # Remove markdown code blocks if present (just in case)
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text)
        except Exception as e:
            logger.error(f"Gemini思考エラー: {e}")
            # フォールバック
            return {"action_type": "click", "target": "動画のサムネイル", "reason": "思考エラーのためデフォルト行動", "description": "デフォルト行動"}

    def _capture_screen(self, monitor):
        """mssでキャプチャしてパスを返す"""
        with mss.mss() as sct:
            monitor_region = {"top": monitor.y, "left": monitor.x, "width": monitor.width, "height": monitor.height}
            sct_img = sct.grab(monitor_region)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Ensure dir exists
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            path = os.path.join(log_dir, "thinking_capture.png")
            
            img.save(path)
            return path

    def vision_click_impl(self, target_desc, monitor, log_func):
        """ (既存のvision_clickロジックを流用 + Ninja Click) """
        # mss用の領域定義
        monitor_region = {
            "top": monitor.y, "left": monitor.x, "width": monitor.width, "height": monitor.height
        }
        
        with mss.mss() as sct:
            try:
                sct_img = sct.grab(monitor_region)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # Debug save
                debug_dir = "logs/debug_vision"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, "last_capture.png")
                img.save(debug_path)
                log_func(f"📸 [Debug] Capture: {debug_path}")

            except Exception as e:
                log_func(f"MSS Capture Failed: {e}", is_error=True)
                return False

        # Locator Call
        local_coords = self.locator.locate_element(img, target_desc, log_func)

        if local_coords:
            local_x, local_y = local_coords
            global_x = monitor.x + local_x
            global_y = monitor.y + local_y
            
            # Ghost Cursor Move
            if hasattr(self.ghost_cursor, 'move_to'):
                self.ghost_cursor.move_to(global_x, global_y)
            
            time.sleep(0.5)
            
            # Ninja Click (Hide)
            if hasattr(self.ghost_cursor, 'hide'):
                self.ghost_cursor.hide()
                time.sleep(0.05)
            
            pyautogui.click(global_x, global_y)
            logger.info(f"🖱️ Click Executed at ({global_x}, {global_y})")
            
            # Show again
            if hasattr(self.ghost_cursor, 'show'):
                pass # Or show()
                
            return True
            
        return False

# シングルトン
soul_operator = SoulOperator()
