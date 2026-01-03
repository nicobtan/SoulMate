// src/index.ts
import { LogManager } from './managers/log_manager.js';
import { UIManager } from './managers/ui_manager.js';
import { Live2DManager } from './managers/live2d_manager.js';
import { ConfigManager } from './managers/config_manager.js';
import { ChatManager } from './managers/chat_manager.js';
import { SoulBubbleManager } from './soul_bubble.js'; // Keep if used directly or move to manager
import { api } from './api_client.js';
import { HistoryManager } from './managers/history_manager.js';
import { SocketClient } from './managers/socket_client.js';

// --- Global Initialization ---
window.addEventListener('DOMContentLoaded', async () => {
    console.log("SoulMate System Booting...");

    // 0. Detect Environment (Desktop vs Web)
    const disableMobileCss = () => {
        const link = document.getElementById('mobile-css-link') as HTMLLinkElement;
        if (link) {
            link.disabled = true;
            console.log("Environment: Mobile CSS Disabled for Desktop Mode");
        }
    };

    const handleMobileMode = () => {
        // Desktop App Mode -> Mobile Class OFF
        if (document.body.classList.contains('desktop-app')) {
            document.body.classList.remove('mobile-mode');
            return;
        }

        // Web Mode -> ALWAYS Mobile Mode (Allow debugging on PC Browser)
        document.body.classList.add('mobile-mode');

        // Ensure CSS is enabled (if previously disabled by desktop logic)
        const link = document.getElementById('mobile-css-link') as HTMLLinkElement;
        if (link && link.disabled) {
            link.disabled = false;
            console.log("Environment: Mobile CSS Re-enabled");
        }
    };

    if ((window as any).pywebview) {
        document.body.classList.add('desktop-app');
        disableMobileCss();
        console.log("Environment: Desktop App Detected");
    } else {
        // Double check async injection
        window.addEventListener('pywebviewready', () => {
            document.body.classList.add('desktop-app');
            disableMobileCss();
            document.body.classList.remove('mobile-mode'); // Remove if added
            console.log("Environment: Desktop App Detected (Async)");
        });

        // Enable Mobile Mode Handler for Web IF NOT Desktop
        // Default to Desktop view to prevent "Mobile Flash" (Black Bar at bottom)
        const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isSmallScreen = window.innerWidth <= 768; // Simple responsive check

        if (isMobileDevice || isSmallScreen) {
            handleMobileMode();
            console.log(`Environment: Web Mode (Mobile: ${isMobileDevice}, SmallScreen: ${isSmallScreen})`);
        } else {
            console.log("Environment: PC Browser (Desktop Width). Resize to <768px to trigger Mobile Mode.");

            // Optional: Dynamic Resize Listener for developers
            window.addEventListener('resize', () => {
                if (window.innerWidth <= 768 && !document.body.classList.contains('mobile-mode')) {
                    handleMobileMode();
                    console.log("Environment: Switched to Mobile Mode via Resize");
                }
            });
        }
    }

    // 0.5 Inject Web Settings (If Container Exists)
    const settingsContainer = document.getElementById('settings-container');
    if (settingsContainer) {
        try {
            const resp = await fetch('settings_web.html');
            if (resp.ok) {
                const html = await resp.text();
                settingsContainer.innerHTML = html;
                console.log("Web Settings Injected Successfully.");
            } else {
                console.warn("Failed to load settings_web.html");
            }
        } catch (e) {
            console.warn("Settings Injection Error (Expected on Desktop App if file not served):", e);
        }
    }

    // 1. Initialize Managers
    const logManager = LogManager.getInstance();
    const uiManager = UIManager.getInstance();
    const chatManager = ChatManager.getInstance();
    const configManager = ConfigManager.getInstance();
    const live2dManager = Live2DManager.getInstance();

    // 1.5 Init Socket Client (Web Mode)
    if (!(window as any).pywebview) {
        SocketClient.getInstance().init();
    }

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

    // ★ Expression Random Button logic
    const expBtn = document.getElementById('expression-test-btn');
    if (expBtn) {
        // Left Click: Random
        expBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            live2dManager.setRandomExpression();
        });

        // Right Click: Default (Reset)
        expBtn.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("[UI] Expression Button Right-Clicked (Reset Request)");
            live2dManager.triggerExpression('neutral'); // Reset
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
        await (window as any).pywebview.api.resize_window(450, 700);

        // --- Dev Scoped Features ---
        const settings = await (window as any).pywebview.api.get_settings();
        if (settings && settings.dev_skip_confirm === true) {
            (window as any).confirm = (msg: string) => {
                console.log(`[Dev] Bypassed confirm: ${msg}`);
                return true;
            };
            console.log("[Dev] confirm() is now bypassed (always returns true)");
        }
    } catch (e) {
        console.warn("Initial startup API calls failed", e);
    }
});
