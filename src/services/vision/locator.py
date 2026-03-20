
import logging
import json
import time
from PIL import Image
from google.genai import types
from src.services.vision.vision_service import vision_service

logger = logging.getLogger(__name__)

class VisionLocator:
    """
    [Vision Locator]
    Gemini Vision (Visual Grounding) を使用して、指定されたUI要素の座標を特定するクラスです。
    テキストでの説明（例：「一番右上のボタン」）から、実際の画面上の座標(x, y)を算出します。
    """
    def __init__(self):
        self.vision = vision_service
        # spatial reasoning（空間認識）に優れたモデルを使用
        # gemini-2.5-flash-lite は高速かつVision性能も安定しています
        self.model_name = "gemini-2.5-flash-lite" 

    def locate_element(self, image: Image.Image, target_description: str, log_func=None):
        """
        スクリーンショット画像の中から、指定された説明(target_description)に一致する要素を探し、
        その中心座標（絶対座標）を返します。

        Args:
            image (Image.Image): 探索対象のスクリーンショット（PIL画像）
            target_description (str): 探したい要素の説明（例: "検索ボタン", "赤いバツ印"）
            log_func (callable, optional): UI出力用のログ関数

        Returns:
            tuple (x, y) or None: 見つかった場合は座標のタプル、見つからない場合はNone
        """
        if not self.vision.client:
            msg = "Vision Client not ready. (APIキーが設定されていない可能性があります)"
            logger.error(msg)
            if log_func: log_func(f"❌ [Locator] {msg}")
            return None

        width, height = image.size
        
        # 【修正】プロンプトを強化
        prompt = f"""
# Task
以下のスクリーンショット内で、ユーザーが指定したUI要素 "{target_description}" の中心座標を特定してください。

# Critical Rules (絶対厳守)
1. **ブラウザUIの無視:** - 画面最上部の「アドレスバー(URL欄)」「ブックマークバー」「タブ」「戻るボタン」は **絶対に選択しないでください**。
   - ユーザーはWebページの中身（コンテンツ）を操作したいと考えています。
   
2. **コンテキストの理解:**
   - "検索バー" と言われたら、ブラウザのアドレスバーではなく、**Webサイト内（ロゴの横など）にある検索ボックス** を探してください。
   - "YouTubeの検索" なら、YouTubeロゴの隣にある虫眼鏡アイコン付きの入力欄が正解です。

# Output Format (JSON)
{{
    "found": boolean,
    "x_norm": integer, // 0-1000
    "y_norm": integer, // 0-1000
    "reason": "特定した理由（例: 最上部のアドレスバーを避けて、ページ内の検索窓を選択しました）"
}}
"""
        try:
            # 画像をバイト列に変換（Gemini API送信形式）
            import io
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            image_part = types.Part.from_bytes(data=img_byte_arr.getvalue(), mime_type="image/jpeg")

            # Visionモデルに問い合わせ
            response = self.vision.client.models.generate_content(
                model=self.model_name,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0 # 座標特定なので、創造性は不要（確実性を優先）
                )
            )
            
            data = json.loads(response.text)
            
            # Handle List response (sometimes Gemini returns [{}])
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    msg = "👁️ [Locator] Empty list returned from Vision."
                    logger.warning(msg)
                    if log_func: log_func(msg)
                    return None
            
            if data.get("found"):
                x_norm = data["x_norm"]
                y_norm = data["y_norm"]
                
                # 正規化座標(0-1000)を、実際の画面解像度(例:1920x1080)に変換
                abs_x = int((x_norm / 1000) * width)
                abs_y = int((y_norm / 1000) * height)
                
                # --- Coordinate Clamp check (Image relative) ---
                final_x = max(0, min(abs_x, width - 1))
                final_y = max(0, min(abs_y, height - 1))
                
                if final_x != abs_x or final_y != abs_y:
                    logger.warning(f"⚠️ [Locator] Coordinate Clamp Triggered: ({abs_x}, {abs_y}) -> ({final_x}, {final_y}) (Image: {width}x{height})")
                # ------------------------------
                
                msg = f"👁️ [Locator] 発見: '{target_description}' -> ({final_x}, {final_y}) (Normalize: {x_norm}, {y_norm})"
                logger.info(msg)
                if log_func: log_func(msg)
                return (final_x, final_y)
            else:
                msg = f"👁️ [Locator] 未発見: '{target_description}' 理由: {data.get('reason')}"
                logger.warning(msg)
                if log_func: log_func(msg)
                return None

        except Exception as e:
            logger.error(f"Locator Error: {e}")
            return None
