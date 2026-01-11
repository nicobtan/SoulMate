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

// Queue for early logs
const logQueue: { msg: string, type: any, category: any }[] = [];
(window as any).logToDebug = (msg: string, type: 'info' | 'warn' | 'error' = 'info', category: 'sys' | 'rag' | 'dbg' | 'vision' = 'sys') => {
    logQueue.push({ msg, type, category });
    console.log(`[Pre-Init Log] ${msg}`);
};

// Make it globally accessible for Backend API
(window as any).updateVisionTarget = (appName: string, isLocked: boolean) => {
    const el = document.getElementById('vision-target-label');
    if (!el) return;

    if (isLocked) {
        el.style.display = 'block';
        el.innerText = `👁️ ${appName}`;
        el.style.color = '#00ffaa';
    } else {
        el.innerText = 'Scanning...';
        el.style.color = '#888';
        // Optional: Hide after delay or keep
        setTimeout(() => { if (el.innerText === 'Scanning...') el.style.display = 'none'; }, 5000);
    }
};

// --- Initialization ---
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

    // Flush Log Queue
    if (logQueue.length > 0) {
        console.log(`[Init] Flushing ${logQueue.length} early logs...`);
        logQueue.forEach(l => logManager.log(l.msg, l.type, l.category));
        logQueue.length = 0; // Clear
    }
    const uiManager = UIManager.getInstance();
    const chatManager = ChatManager.getInstance();
    const configManager = ConfigManager.getInstance();
    const live2dManager = Live2DManager.getInstance();

    // 1.5 Init Socket Client
    // SocketClient now handles Desktop Mode detection internally.
    setTimeout(() => {
        SocketClient.getInstance().init();
    }, 500); // Keep small delay just to be safe for injection

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
    const initLive2D = async () => {
        try {
            if ((window as any).pywebview) {
                const settings = await api.get_settings();
                const currentId = settings.current_character_id || 'default';
                console.log(`[Init] Fetching profile for: ${currentId}`);

                const profiles = await api.get_character_profiles();
                const profile = profiles.find((p: any) => p.id === currentId) || profiles[0];

                if (profile) {
                    console.log(`[Init] Loading Character: ${profile.name} (${profile.model_id})`);
                    await live2dManager.init('character-area', profile.model_id, {
                        scale: profile.scale,
                        x: profile.x,
                        y: profile.y
                    });
                } else {
                    console.warn("[Init] Character profile not found, falling back to default.");
                    await live2dManager.initialize();
                }
            } else {
                // Web Mode
                console.log("[Init] Web Mode: Initializing default Live2D.");
                await live2dManager.initialize();
            }
            logManager.log("Live2D Initialized", "info", "sys");
        } catch (e) {
            console.error("Live2D Init Error", e);
        }
    };

    // Execute Init
    if ((window as any).pywebview) {
        await initLive2D();
    } else {
        // Wait for pywebviewready, but if it doesn't come (Web Mode), falling back is tricky 
        // without a timeout. However, usually we can assume Desktop App will fire it.
        // For pure Web Mode, pywebviewready never fires.

        // Strategy: Set a timeout. If pywebviewready doesn't fire in 500ms, assume Web Mode.
        // OR: Listen to pywebviewready, and if it fires, run initLive2D (which handles desktop logic).
        // If we are strictly in "Desktop App" environment, we should wait.

        let initDone = false;
        window.addEventListener('pywebviewready', async () => {
            if (!initDone) {
                initDone = true;
                console.log("[Init] pywebviewready fired, initializing Live2D...");
                await initLive2D();
            }
        });

        // Fallback for Pure Web Mode (Development Only)
        // User requested strict waiting for desktop init. 
        // Web fallback now requires explicit '?web=true' parameter.
        const isWebDev = window.location.search.includes('web=true');

        if (isWebDev) {
            setTimeout(async () => {
                if (!initDone && !(window as any).pywebview) {
                    initDone = true;
                    console.log("[Init] Web Dev Mode Detected (Timeout). Initializing default Live2D.");
                    await initLive2D();
                }
            }, 1000);
        } else {
            console.log("[Init] Waiting for pywebviewready... (Desktop Mode)");
        }
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

// --- Vision Target Logic (Drag & Check) ---
const targetDragBtn = document.getElementById('vision-target-drag-btn');
if (targetDragBtn) {
    // Left Click (Hold): Start Drag Session
    targetDragBtn.addEventListener('mousedown', async (e) => {
        // Only trigger on Left Click (button 0)
        if (e.button !== 0) return;

        e.preventDefault();
        LogManager.getInstance().log("Vision Target Drag Started...", 'info', 'vision');

        // Change cursor to crosshair globally (simulated via body style)
        document.body.style.cursor = "crosshair";

        // Notify Backend to start monitoring
        await api.start_target_drag();
    });

    // Right Click: Debug Vision Image
    targetDragBtn.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        e.stopPropagation();

        const modal = document.getElementById('vision-debug-modal');
        const img = document.getElementById('vision-debug-image') as HTMLImageElement;

        if (modal && img) {
            // Bust cache with timestamp to force reload
            const timestamp = new Date().getTime();
            img.src = `debug/latest_vision.jpg?t=${timestamp}`;
            modal.style.display = 'flex';
        }
    });

    // Reset cursor on mouse up (globally)
    document.addEventListener('mouseup', () => {
        document.body.style.cursor = "default";
    });
}
