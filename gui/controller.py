import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import threading

class SoulMateController:
    def __init__(self, api_instance):
        self.api = api_instance
        self.root = None
        self.is_stealth = False
        
    def _create_gui(self):
        self.root = tk.Tk()
        self.root.title("SoulMate Controller")
        self.root.geometry("400x300")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#2D2D30")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#2D2D30", foreground="#FFFFFF")
        style.configure("TButton", background="#3E3E42", foreground="#FFFFFF")
        
        # --- Top Area: Status and Switch ---
        top_frame = tk.Frame(self.root, bg="#2D2D30")
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(top_frame, text="Status: RUNNING", font=("Helvetica", 10, "bold"), foreground="#00FF00")
        self.status_label.pack(side=tk.LEFT)
        
        self.stealth_btn = ttk.Button(top_frame, text="Enable Stealth Mode", command=self.toggle_stealth)
        self.stealth_btn.pack(side=tk.RIGHT)
        
        # --- Middle Area: Logs ---
        self.log_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=40, height=10, bg="#1E1E1E", fg="#D4D4D4", font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # --- Bottom Area: Actions ---
        bot_frame = tk.Frame(self.root, bg="#2D2D30")
        bot_frame.pack(fill=tk.X, padx=10, pady=5)
        
        force_btn = ttk.Button(bot_frame, text="Force AI Scan", command=self.force_scan)
        force_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        talk_btn = ttk.Button(bot_frame, text="Toggle UI", command=self.toggle_ui)
        talk_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Window closing hook
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.add_log("System: Controller GUI ready.")
        
        # Start main loop
        self.root.mainloop()

    def start(self):
        """Starts the GUI in a daemon thread so it doesn't block the main pywebview loop."""
        threading.Thread(target=self._create_gui, daemon=True).start()

    def add_log(self, message: str):
        """Thread-safe logging from external components."""
        if not self.root:
            return
        
        def _insert():
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END)
            
        try:
            self.root.after(0, _insert)
        except Exception:
            pass

    def toggle_stealth(self):
        self.is_stealth = not self.is_stealth
        
        if self.is_stealth:
            self.stealth_btn.config(text="Disable Stealth Mode")
            self.status_label.config(text="Status: STEALTH", foreground="#FFD700")
            self.add_log("System: Stealth mode enabled (Live2D disabled).")
            # Update API / Engine
            if self.api and hasattr(self.api, '_active_engine') and self.api._active_engine:
                 self.api._active_engine.set_stealth_mode(True)
            # Instruct frontend to pause TS ticker and optionally hide window
            if self.api and self.api._live2d_window:
                 try:
                     self.api._live2d_window.evaluate_js("if(window.setLive2DStealthMode) window.setLive2DStealthMode(true);")
                     # Also hide the window to completely drop GPU overhead for chromium view
                     self.api._live2d_window.hide()
                     self.api._live2d_visible = False
                 except Exception as e:
                     self.add_log(f"Error hiding window: {e}")
        else:
            self.stealth_btn.config(text="Enable Stealth Mode")
            self.status_label.config(text="Status: RUNNING", foreground="#00FF00")
            self.add_log("System: Stealth mode disabled (Live2D enabled).")
            # Update API / Engine
            if self.api and hasattr(self.api, '_active_engine') and self.api._active_engine:
                 self.api._active_engine.set_stealth_mode(False)
            if self.api and self.api._live2d_window:
                 try:
                     self.api._live2d_window.evaluate_js("if(window.setLive2DStealthMode) window.setLive2DStealthMode(false);")
                     self.api._live2d_window.show()
                     self.api._live2d_visible = True
                 except: pass

    def force_scan(self):
        self.add_log("User: Force AI Scan requested.")
        if self.api and hasattr(self.api, '_active_engine') and self.api._active_engine:
            self.api._active_engine.force_proactive_scan()
            
    def toggle_ui(self):
        self.add_log("User: Toggle Live2D UI.")
        if self.api:
            self.api.toggle_live2d()

    def on_close(self):
        """Clean shutdown hook"""
        self.add_log("System: Gui closed.")
        if self.root:
            self.root.destroy()
        if self.api:
            self.api.cleanup()
        import os
        os._exit(0)
