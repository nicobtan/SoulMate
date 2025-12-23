// src/managers/ui_manager.ts
import { uiState } from '../constants.js';
import { LogManager } from './log_manager.js';
import { api } from '../api_client.js';

export class UIManager {
    private static instance: UIManager;

    // Elements
    private appContainer: HTMLElement | null;
    private rightPanel: HTMLElement | null;
    private chatToggleBtn: HTMLElement | null;
    private clockTime: HTMLElement | null;
    private clockDate: HTMLElement | null;
    private statusText: HTMLElement | null;
    private statusDot: HTMLElement | null;
    private suggestionToggleBtn: HTMLElement | null;
    private suggestionPopup: HTMLElement | null;
    private settingsModal: HTMLElement | null;

    // New Elements
    private characterArea: HTMLElement | null;
    private leftPanel: HTMLElement | null;
    private contextMenu: HTMLElement | null;

    private constructor() {
        this.appContainer = document.getElementById('app-container');
        this.rightPanel = document.getElementById('right-panel');
        this.chatToggleBtn = document.getElementById('chat-toggle-btn');
        this.clockTime = document.getElementById('clock-time');
        this.clockDate = document.getElementById('clock-date');
        this.statusText = document.getElementById('status-text');
        this.statusDot = document.getElementById('status-dot');
        this.suggestionToggleBtn = document.getElementById('suggestion-toggle-btn');
        this.suggestionPopup = document.getElementById('suggestion-popup');
        this.settingsModal = document.getElementById('settings-modal');

        this.characterArea = document.getElementById('character-area');
        this.leftPanel = document.getElementById('left-panel');
        this.contextMenu = document.getElementById('context-menu');
    }

    public static getInstance(): UIManager {
        if (!UIManager.instance) UIManager.instance = new UIManager();
        return UIManager.instance;
    }

    public init() {
        this.initLayoutDetection();
        this.initClock();
        this.initButtons();
        this.initFadeUI();
        this.initContextMenus();

        // Expose global helpers
        (window as any).openChatPanel = this.openChatPanel.bind(this);
        (window as any).updateStatusDisplay = this.updateStatus.bind(this);
        // Expose instance for onclick access from HTML
        (window as any).uiManager = this;

        // Global Click to close context menu
        window.addEventListener('click', () => {
            if (this.contextMenu && this.contextMenu.style.display !== 'none') {
                this.contextMenu.style.display = 'none';
            }
        }, { capture: true });

        console.log("UIManager Initialized");
    }

    // --- 1. Layout & Clock ---
    private initLayoutDetection() {
        const detect = () => {
            const isMobileUA = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
            const isSmallScreen = window.innerWidth <= 768;

            if (isMobileUA && isSmallScreen) {
                if (!document.body.classList.contains('mobile-mode')) {
                    document.body.classList.add('mobile-mode');
                    if ((window as any).resizeModel) (window as any).resizeModel();
                }
            } else {
                if (document.body.classList.contains('mobile-mode')) {
                    document.body.classList.remove('mobile-mode');
                    if ((window as any).resizeModel) (window as any).resizeModel();
                }
            }
        };
        window.addEventListener('DOMContentLoaded', detect);
        window.addEventListener('resize', detect);
    }

    private initClock() {
        const update = () => {
            const now = new Date();
            if (this.clockTime) this.clockTime.innerText = now.toLocaleTimeString('ja-JP', { hour12: false });
            if (this.clockDate) {
                const y = now.getFullYear();
                const m = String(now.getMonth() + 1).padStart(2, '0');
                const d = String(now.getDate()).padStart(2, '0');
                this.clockDate.innerText = `${y}-${m}-${d}`;
            }
        };
        setInterval(update, 1000);
        update();
    }

    // --- 2. Buttons & Interactions ---
    private initButtons() {
        // Chat Toggle
        if (this.chatToggleBtn) {
            this.chatToggleBtn.addEventListener('click', () => {
                this.openChatPanel(!uiState.isChatOpen);
            });
        }

        // Settings Modal Close
        const closeBtn = document.getElementById('settings-close-btn');
        if (closeBtn && this.settingsModal) {
            closeBtn.addEventListener('click', () => {
                this.settingsModal!.style.display = 'none';
            });
        }

        // Mobile Settings Open
        const mobileBtn = document.getElementById('mobile-settings-btn');
        if (mobileBtn && this.settingsModal) {
            mobileBtn.addEventListener('click', () => {
                this.settingsModal!.style.display = 'block';
            });
        }

        if (this.suggestionToggleBtn) {
            this.suggestionToggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleSuggestions();
            });
        }

        // Spawn Balloon Button
        const spawnBtn = document.getElementById('spawn-balloon-btn');
        if (spawnBtn) {
            spawnBtn.addEventListener('click', async () => {
                const bubble = await api.generate_bubble();
                // Note: The backend push usually handles display, but if return value is immediate, we might need to handle it.
                // However, python side typically emits 'show_bubble' event or similar?
                // Looking at legacy code, generate_bubble might return data we pass to showSoulBubble?
                // Let's check api.generate_bubble signature in python.
                // Assuming it returns bubble data or triggers push. For now, let's log it.
                if (bubble && bubble.text) {
                    // Manually show if returned
                    (window as any).showSoulBubble?.(bubble.category, bubble.text, bubble.action_id, bubble.type);
                }
            });
        }
    }

    private initFadeUI() {
        if (!this.appContainer) return;
        let fadeTimer: any = null;

        this.appContainer.classList.add('ui-hidden');
        window.addEventListener('mousemove', () => {
            this.appContainer!.classList.remove('ui-hidden');
            if (fadeTimer) clearTimeout(fadeTimer);
            fadeTimer = setTimeout(() => {
                this.appContainer!.classList.add('ui-hidden');
            }, 60000); // 60s
        });
    }

    // --- 3. Public API ---
    public async openChatPanel(open: boolean = true) {
        if (open === uiState.isChatOpen) return;
        uiState.isChatOpen = open;

        if (this.rightPanel) this.rightPanel.classList.toggle('open', open);
        if (this.chatToggleBtn) this.chatToggleBtn.classList.toggle('active', open);

        await LogManager.getInstance().resizeWindow();
    }

    public updateStatus(state: 'Idle' | 'Listening' | 'Thinking' | 'Speaking' | string, isActive: boolean = true) {
        // Support legacy calls (string, boolean) and new calls (enum)
        const text = state;

        if (this.statusText) this.statusText.innerText = text;

        if (this.statusDot) {
            this.statusDot.style.animation = 'none';
            if (!isActive) {
                this.statusDot.style.backgroundColor = '#888';
                return;
            }

            // Color Mapping
            switch (text) {
                case 'Listening':
                    this.statusDot.style.backgroundColor = '#ff4444'; // Red
                    this.statusDot.style.animation = 'pulse 1s infinite';
                    break;
                case 'Thinking':
                case 'Thinking...': // Legacy compatibility
                case '考え中...':
                    this.statusDot.style.backgroundColor = '#ffff00'; // Yellow
                    this.statusDot.style.animation = 'pulse 0.5s infinite';
                    break;
                case 'Speaking':
                    this.statusDot.style.backgroundColor = '#00ff00'; // Green
                    this.statusDot.style.animation = 'pulse 1.5s infinite';
                    break;
                default: // Active/Idle
                    this.statusDot.style.backgroundColor = '#ffa500'; // Orange
                    break;
            }
        }
    }

    public updateSuggestions(suggestions: string[], onClickCallback: (text: string) => void) {
        if (!this.suggestionToggleBtn || !this.suggestionPopup) return;
        this.suggestionPopup.innerHTML = '';

        if (!suggestions || suggestions.length === 0) {
            this.suggestionToggleBtn.style.display = 'none';
            this.suggestionPopup.style.display = 'none';
            return;
        }

        this.suggestionToggleBtn.style.display = 'flex';
        suggestions.forEach(text => {
            const chip = document.createElement('div');
            chip.className = 'suggestion-chip';

            // Check for Love Prefix
            let displayText = text;
            if (text.startsWith("❤ ")) {
                chip.classList.add('love-chip');
                // Remove prefix from display or keep it? User said "icon: 'heart' (UI側で...として表示)".
                // Keeping it confirms the icon is there, or we can use CSS to add icon.
                // Let's keep the text as is, but style the chip pink.
            }

            chip.innerText = displayText;
            if (displayText === "別の話題はある？" || displayText.includes("他の話題")) chip.classList.add('static-cmd');

            chip.addEventListener('click', () => {
                onClickCallback(text);
                this.suggestionPopup!.style.display = 'none';
            });
            this.suggestionPopup!.appendChild(chip);
        });
    }

    public toggleSuggestions() {
        if (!this.suggestionPopup) return;
        const isVisible = this.suggestionPopup.style.display === 'flex';
        this.suggestionPopup.style.display = isVisible ? 'none' : 'flex';
    }

    public switchLogTab(tabName: string) {
        // Tab Buttons
        const btns = document.querySelectorAll('.tab-btn');
        btns.forEach(btn => btn.classList.remove('active'));

        // Find clicked button based on onclick attribute or class? 
        // Index.html logic uses hardcoded onclicks.
        // We can just rely on the onclick adding active class manually? 
        // No, we need to find the specific button associated with tabName.
        // Simplified: Loop and check mapping, or just query mapped button.
        // Button Logic:
        const targetBtn = document.querySelector(`.tab-btn[onclick*="'${tabName}'"]`);
        if (targetBtn) targetBtn.classList.add('active');

        // Content
        const Contents = document.querySelectorAll('.log-content');
        Contents.forEach(content => content.classList.remove('active'));

        const targetContent = document.getElementById(`log-${tabName}`);
        if (targetContent) {
            targetContent.classList.add('active');
            targetContent.scrollTop = targetContent.scrollHeight;
        }
    }

    private initContextMenus() {
        if (this.characterArea) {
            this.characterArea.addEventListener('contextmenu', (e) => this.showCtxMenu(e, 'settings'));
        }
        if (this.leftPanel) {
            this.leftPanel.addEventListener('contextmenu', (e) => this.showCtxMenu(e, 'restore'));
        }
    }

    private showCtxMenu(e: MouseEvent, type: 'restore' | 'settings') {
        e.preventDefault();
        e.stopPropagation();
        if (!this.contextMenu) return;

        const x = e.clientX;
        const y = e.clientY;

        // Content Switching
        this.contextMenu.innerHTML = '';

        if (type === 'restore') {
            this.contextMenu.innerHTML = `
                <div class="ctx-item" id="ctx-restore-action">
                    <span class="ctx-icon">↻</span>
                    <span>履歴を復元</span>
                </div>
            `;
            setTimeout(() => {
                document.getElementById('ctx-restore-action')?.addEventListener('click', () => {
                    // Restore logic via API call (hooked in index.ts or global)
                    (window as any).restoreSession?.();
                    this.contextMenu!.style.display = 'none';
                });
            }, 0);
        } else {
            // Settings / Exit
            this.contextMenu.innerHTML = `
                <div class="ctx-item" id="ctx-settings-action">
                    <span class="ctx-icon">⚙️</span>
                    <span>設定</span>
                </div>
                <div style="height:1px; background:#444; margin:2px 0;"></div>
                <div class="ctx-item" id="ctx-exit-action">
                    <span class="ctx-icon">❌</span>
                    <span>終了</span>
                </div>
            `;
            setTimeout(() => {
                document.getElementById('ctx-settings-action')?.addEventListener('click', () => {
                    this.contextMenu!.style.display = 'none';
                    if ((window as any).pywebview) (window as any).pywebview.api.open_settings();
                });
                document.getElementById('ctx-exit-action')?.addEventListener('click', () => {
                    this.contextMenu!.style.display = 'none';
                    if ((window as any).pywebview) (window as any).pywebview.api.close_window();
                });
            }, 0);
        }

        this.contextMenu.style.left = `${x}px`;
        this.contextMenu.style.top = `${y}px`;
        this.contextMenu.style.display = 'block';
    }
}
