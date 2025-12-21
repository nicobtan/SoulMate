// src/index.ts
import { LogManager } from './managers/log_manager.js';
import { UIManager } from './managers/ui_manager.js';
import { Live2DManager } from './managers/live2d_manager.js';
import { ConfigManager } from './managers/config_manager.js';
import { ChatManager } from './managers/chat_manager.js';
import { SoulBubbleManager } from './soul_bubble.js'; // Keep if used directly or move to manager
import { api } from './api_client.js';
import { HistoryManager } from './managers/history_manager.js';

// --- Global Initialization ---
window.addEventListener('DOMContentLoaded', async () => {
    console.log("SoulMate System Booting...");

    // 1. Initialize Managers
    const logManager = LogManager.getInstance();
    const uiManager = UIManager.getInstance();
    const chatManager = ChatManager.getInstance();
    const configManager = ConfigManager.getInstance();
    const live2dManager = Live2DManager.getInstance();

    uiManager.init();
    chatManager.init();

    // 2. Load Settings & Config
    // Wait for PyWebview if in desktop mode, else load immediately
    if ((window as any).pywebview) {
        window.addEventListener('pywebviewready', () => configManager.init());
    } else {
        configManager.init(); // Web Mode
    }

    // 3. Initialize Live2D
    const modelPath = 'models/fav_usaneko_alwb/fav_usaneko_alwb.model3.json';
    try {
        await live2dManager.init('character-area', modelPath);
        logManager.log("Live2D Initialized", "info", "sys");
    } catch (e) {
        console.error("Live2D Init Error", e);
    }

    // 4. Initialize Soul Bubble System (Manual & Auto)
    // Note: If you want to move SoulBubble logic to a manager completely, you can.
    // For now, we keep the global glue here or in ChatManager. 
    // Ideally, create SoulBubbleManager instance inside ChatManager or standalone.
    // Let's keep it simple here as it was.
    const bubbleManager = new SoulBubbleManager();
    // Expose for global calls (from python)
    // Expose for global calls (from python)
    // Expose for global calls (from python)
    // Expose for global calls (from python)
    (window as any).soulBubbleManager = bubbleManager;

    // --- History Manager (Step 4) ---
    const historyManager = HistoryManager.getInstance();
    const histBtn = document.getElementById('history-btn');
    if (histBtn) {
        histBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            historyManager.open();
        });
    }

    // ★ Restore Global Bubble Hook
    (window as any).showSoulBubble = function (cat: string, txt: string, aid: string, type: string) {
        chatManager.showSoulBubble(cat, txt, aid, type);
    };

    logManager.log("System Ready.", "info", "sys");
});

// --- Restore Session Logic (Bridge) ---
// This could move to ChatManager, but keeping one top-level bridge is fine.
// ★ Restore Global Restore Hook (Used by Context Menu)
(window as any).restoreSession = async () => {
    try {
        const history = await api.restore_history();
        if (history && history.length > 0) {
            LogManager.getInstance().log(`Restored ${history.length} messages`, 'info', 'sys');
            ChatManager.getInstance().loadConversation(history);
            // Ensure panel is open if there is history? maybe not force it.
            // UIManager.getInstance().openChatPanel(true);
        }
    } catch (e) {
        console.warn("Session Restore skipped", e);
    }
};

window.addEventListener('pywebviewready', async () => {
    // Auto-restore on boot
    // ★修正: ユーザー要望により自動履歴読み込みを無効化
    // (window as any).restoreSession();

    // ★ Force Initial Resize to prevent UI clipping
    try {
        await (window as any).pywebview.api.resize_window(500, 500);
    } catch (e) {
        console.warn("Initial resize failed", e);
    }
});
