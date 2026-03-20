import tkinter as tk
import threading
import time
import math
import logging
import os
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

class GhostCursor:
    def __init__(self):
        self._root = None
        self._canvas = None
        self._cursor_id = None
        self._cursor_img = None 
        
        self.current_x = 0
        self.current_y = 0
        self.target_x = 0
        self.target_y = 0
        self.visible = False
        self.running = False
        self.smoothing = 0.2
        
        self._thread = threading.Thread(target=self._run_ui, daemon=True)
        self._thread.start()
        
    def _run_ui(self):
        self._root = tk.Tk()
        self._root.title("SoulMate Ghost Cursor")
        
        try:
            import ctypes
            user32 = ctypes.windll.user32
            x_virtual = user32.GetSystemMetrics(76)
            y_virtual = user32.GetSystemMetrics(77)
            w_virtual = user32.GetSystemMetrics(78)
            h_virtual = user32.GetSystemMetrics(79)
            screen_width, screen_height = w_virtual, h_virtual
            x_pos, y_pos = x_virtual, y_virtual
        except:
            screen_width = self._root.winfo_screenwidth()
            screen_height = self._root.winfo_screenheight()
            x_pos, y_pos = 0, 0

        self.offset_x = x_pos
        self.offset_y = y_pos

        geo_str = f"{screen_width}x{screen_height}{x_pos:+}{y_pos:+}"
        self._root.geometry(geo_str)
        
        # 透過設定
        TRANS_KEY = "#FF00FF"
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 1.0)
        self._root.attributes("-transparentcolor", TRANS_KEY)
        self._root.overrideredirect(True)
        
        # クリック透過 (Windows API)
        try:
            from ctypes import windll
            hwnd = windll.user32.GetParent(self._root.winfo_id())
            style = windll.user32.GetWindowLongW(hwnd, -20)
            style = style | 0x80000 | 0x20
            windll.user32.SetWindowLongW(hwnd, -20, style)
        except: pass

        self._canvas = tk.Canvas(self._root, width=screen_width, height=screen_height, bg=TRANS_KEY, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        
        self._load_cursor_image()
        self._update_loop()
        
        self.running = True
        try:
            self._root.mainloop()
        except KeyboardInterrupt: pass

    def _load_cursor_image(self):
        """画像を読み込み、基準点を設定する"""
        self._cursor_img = None 
        try:
            img_path = os.path.join(os.getcwd(), "assets", "cursor", "ghostcursor1.png")
            
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
                pil_img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                self._cursor_img = ImageTk.PhotoImage(pil_img, master=self._root)
                
                # 【修正ポイント】 anchor="center" -> "nw" (NorthWest: 左上)
                # これで、画像の左上隅（矢印の先端）が座標(x,y)に合います
                self._cursor_id = self._canvas.create_image(0, 0, image=self._cursor_img, anchor="nw", state="hidden")
                logger.info(f"👻 [GhostCursor] Loaded custom cursor: {img_path}")
            else:
                self._create_fallback_cursor()
        except Exception:
            self._create_fallback_cursor()

    def _create_fallback_cursor(self):
        self._cursor_img = None
        self._canvas.delete("all")
        # フォールバックは中心基準のまま（円なので）
        self._cursor_id = self._canvas.create_oval(0, 0, 40, 40, outline="#00FF00", width=4)

    def _update_loop(self):
        if not self._root: return
        
        if self.visible:
            try:
                self._root.lift()
                self._root.attributes("-topmost", True)
            except: pass
            
            # 移動計算
            dx = self.target_x - self.current_x
            dy = self.target_y - self.current_y
            
            if abs(dx) > 1 or abs(dy) > 1:
                self.current_x += dx * self.smoothing
                self.current_y += dy * self.smoothing
            else:
                self.current_x = self.target_x
                self.current_y = self.target_y
                
            # 座標変換
            offset_x = getattr(self, 'offset_x', 0)
            offset_y = getattr(self, 'offset_y', 0)
            cx = self.current_x - offset_x
            cy = self.current_y - offset_y
            
            try:
                if self._cursor_img:
                    # 画像モード: 左上基準(nw)なので、そのまま座標を渡せばOK
                    # 以前の中心補正などは不要です
                    self._canvas.coords(self._cursor_id, cx, cy)
                    self._canvas.itemconfigure(self._cursor_id, state="normal")
                else:
                    # 図形モード
                    self._canvas.coords(self._cursor_id, cx-20, cy-20, cx+20, cy+20)
                    self._canvas.itemconfigure(self._cursor_id, state="normal")
            except: pass
        else:
            try:
                self._canvas.itemconfigure(self._cursor_id, state="hidden")
            except: pass
            
        self._root.after(16, self._update_loop)

    def move_to(self, x, y):
        self.target_x = x
        self.target_y = y
        self.visible = True
        
    def hide(self):
        self.visible = False
        
    def show(self):
        self.visible = True
