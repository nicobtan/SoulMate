
import logging
from screeninfo import get_monitors

logger = logging.getLogger(__name__)

class MonitorManager:
    """
    [MonitorManager]
    マルチモニター環境において、最も右側にあるモニターを自動特定し、
    AIの活動領域を管理するクラス。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MonitorManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.monitors = []
        self.target_monitor = None
        self._scan_monitors()

    def _scan_monitors(self):
        """全モニター情報を取得し、配置を分析する"""
        try:
            self.monitors = get_monitors()
            logger.info(f"✨ [MonitorManager] 検出されたモニター: {len(self.monitors)}台")
            
            # モニター情報をログに出力（デバッグ用）
            for i, m in enumerate(self.monitors):
                logger.info(f"   📺 Monitor {i}: {m.width}x{m.height} at (x={m.x}, y={m.y}) Primary={m.is_primary}")

            if not self.monitors:
                logger.error("❌ モニターが検出されませんでした。")
                return

            # 戦略: X座標が最も大きい（物理的に一番右にある）モニターを選択
            # 縦置きなどが混在していても、xの値で判断するのが最も確実です。
            rightmost_monitor = max(self.monitors, key=lambda m: m.x)
            
            self.target_monitor = rightmost_monitor
            logger.info(f"🎯 [MonitorManager] ターゲットロックオン: 一番右のモニター (x={self.target_monitor.x})")
            logger.info(f"   📏 エリア: x={self.target_monitor.x}, y={self.target_monitor.y}, w={self.target_monitor.width}, h={self.target_monitor.height}")

        except Exception as e:
            logger.error(f"❌ [MonitorManager] Monitor scan failed: {e}")
            self.monitors = []
            self.target_monitor = None

    def get_target_monitor(self):
        if not self.target_monitor:
            self._scan_monitors()
        return self.target_monitor

    def get_offset(self):
        """ターゲットモニターの左上座標(Offset)を返す"""
        if self.target_monitor:
            return self.target_monitor.x, self.target_monitor.y
        return 0, 0

    def to_global(self, local_x, local_y):
        """
        AIが見ているローカル座標(Monitor内)を、Windows全体のグローバル座標に変換する。
        """
        off_x, off_y = self.get_offset()
        return off_x + local_x, off_y + local_y

monitor_manager = MonitorManager()
