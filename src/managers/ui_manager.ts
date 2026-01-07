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

    // Mobile Elements
    private mobileMenuBtn: HTMLElement | null;
    private mobileContextMenu: HTMLElement | null;

    // Context & Panels
    private characterArea: HTMLElement | null;
    private leftPanel: HTMLElement | null;
    private contextMenu: HTMLElement | null;

    // Topic Modal Elements
    private topicModal: HTMLElement | null;
    private topicList: HTMLElement | null;
    private closeTopicBtn: HTMLElement | null;

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

        this.mobileMenuBtn = document.getElementById('mobile-menu-btn');
        this.mobileContextMenu = document.getElementById('mobile-context-menu');

        // Topic Modal
        this.topicModal = document.getElementById('topic-selection-modal');
        this.topicList = document.getElementById('topic-list');
        this.closeTopicBtn = document.getElementById('close-topic-modal');
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
        this.initMobileMenu();
        this.initTopicModalListener(); // New Listener Init

        // Expose global helpers
        (window as any).openChatPanel = this.openChatPanel.bind(this);
        (window as any).updateStatusDisplay = this.updateStatus.bind(this);
        // Expose instance for onclick access from HTML
        (window as any).uiManager = this;

        // Global Click to close context menu & Unlock Audio
        window.addEventListener('click', () => {
            if (this.contextMenu && this.contextMenu.style.display !== 'none') {
                this.contextMenu.style.display = 'none';
            }
            // Unlock Audio Context (Mobile Web)
            import('../services/audio_manager.js').then(({ AudioManager }) => {
                AudioManager.getInstance().unlock();
            });
        }, { capture: true });

        console.log("UIManager Initialized");
    }

    private initTopicModalListener() {
        if (this.closeTopicBtn && this.topicModal) {
            this.closeTopicBtn.addEventListener('click', () => {
                this.topicModal!.classList.add('hidden');
            });
        }
    }

    private initMobileMenu() {
        if (this.mobileMenuBtn && this.mobileContextMenu) {
            this.mobileMenuBtn.addEventListener('click', () => {
                this.mobileContextMenu!.classList.remove('hidden');
            });
        }
    }

    public closeMobileMenu() {
        if (this.mobileContextMenu) {
            this.mobileContextMenu.classList.add('hidden');
        }
    }

    public toggleWindow(target: string) {
        if (target === 'settings') {
            if (this.settingsModal) {
                this.settingsModal.style.display = 'block';
                // Ensure it's on top for mobile
                this.settingsModal.style.zIndex = '5000';
            }
        } else if (target === 'history' || target === 'logs') {
            // For mobile history/logs, we reuse logic or just show left panel as overlay
            // Since left-panel is hidden by !important css on mobile, we need to enforce display
            if (this.leftPanel) {
                const isHidden = this.leftPanel.style.display === 'none' || getComputedStyle(this.leftPanel).display === 'none';

                if (isHidden) {
                    this.leftPanel.style.setProperty('display', 'flex', 'important');
                    this.leftPanel.style.setProperty('position', 'fixed', 'important');
                    this.leftPanel.style.setProperty('top', '0', 'important');
                    this.leftPanel.style.setProperty('left', '0', 'important');
                    this.leftPanel.style.setProperty('width', '100%', 'important');
                    this.leftPanel.style.setProperty('height', '100dvh', 'important');
                    this.leftPanel.style.setProperty('z-index', '2000', 'important');
                    this.leftPanel.style.setProperty('background', 'rgba(0,0,0,0.95)', 'important');
                    this.leftPanel.style.setProperty('opacity', '1', 'important');

                    // Add close handler if not exists
                    this.leftPanel.onclick = (e) => {
                        // Close if clicked on background (simple dismissal)
                        if (e.target === this.leftPanel) {
                            this.leftPanel!.style.display = 'none';
                        }
                    };

                    // Switch logic
                    if (target === 'history') {
                        // Assuming switchLogTab('history') exists or handled
                        if ((this as any).switchLogTab) (this as any).switchLogTab('history');
                    } else {
                        // Default to system for logs
                        if ((this as any).switchLogTab) (this as any).switchLogTab('sys');
                    }
                } else {
                    this.leftPanel.style.display = 'none';
                }
            }
        }
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
        // Helper to unlock audio on interaction
        const unlockAudio = () => {
            import('../services/audio_manager.js').then(m => m.AudioManager.getInstance().unlock());
        };

        // Chat Toggle
        if (this.chatToggleBtn) {
            this.chatToggleBtn.addEventListener('click', () => {
                this.openChatPanel(!uiState.isChatOpen);
                import('../services/audio_manager.js').then(m => m.AudioManager.getInstance().unlock());
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
                unlockAudio();
            });
        }

        if (this.suggestionToggleBtn) {
            this.suggestionToggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleSuggestions();
                import('../services/audio_manager.js').then(m => m.AudioManager.getInstance().unlock());
            });
        }

        // Spawn Balloon Button -> Topic Selection (Mobile) or Soul Bubble (Desktop)
        const spawnBtn = document.getElementById('spawn-balloon-btn');
        if (spawnBtn) {
            spawnBtn.addEventListener('click', async () => {
                unlockAudio(); // Unlock here
                const isMobile = document.body.classList.contains('mobile-mode');

                if (isMobile) {
                    // Mobile: Show Topic Selection Modal
                    if (this.topicModal && this.topicList) {
                        this.topicModal.classList.remove('hidden');
                        this.topicList.innerHTML = '<div class="loading-spinner" style="color:#888;">思考中...</div>';

                        // Fetch Topics
                        const topics = await api.get_topic_suggestions();

                        // Render
                        this.topicList.innerHTML = '';
                        topics.forEach(topic => {
                            const btn = document.createElement('button');
                            btn.innerText = topic;
                            btn.style.width = '100%';
                            btn.style.padding = '12px';
                            btn.style.borderRadius = '6px';
                            btn.style.textAlign = 'left';
                            btn.style.cursor = 'pointer';
                            btn.style.marginBottom = '8px'; // Spacing

                            // Special Styling for Love Items
                            if (topic.includes('❤')) {
                                btn.style.background = 'linear-gradient(135deg, #e91e63, #ff4081)';
                                btn.style.color = 'white';
                                btn.style.border = '1px solid #ff80ab';
                                btn.style.fontWeight = 'bold';
                                btn.style.boxShadow = '0 2px 8px rgba(233, 30, 99, 0.4)';
                            } else {
                                btn.style.background = '#333';
                                btn.style.color = 'white';
                                btn.style.border = '1px solid #555';
                            }

                            btn.onclick = () => {
                                // User selected a topic -> Chat
                                import('./chat_manager.js').then(m => {
                                    m.ChatManager.getInstance().sendMessage(topic);
                                });
                                this.topicModal!.classList.add('hidden');
                                this.openChatPanel(true); // Ensure chat is open
                            };
                            this.topicList!.appendChild(btn);
                        });
                    }
                } else {
                    // Desktop: Spawn Floating Soul Bubble
                    // Logic restored from previous version
                    const bubble = await api.generate_bubble();
                    if (bubble && bubble.text) {
                        (window as any).showSoulBubble?.(bubble.category, bubble.text, bubble.action_id, bubble.type);
                    } else {
                        // Fallback if API returns null/empty
                        (window as any).showSoulBubble?.('topics', '何かお話ししましょう？', 'manual_fallback', 'discovery');
                    }
                }
            });
        }

        // Status Text Force Trigger
        if (this.statusText) {
            this.statusText.addEventListener('click', async () => {
                unlockAudio();
                // Only trigger if enabled and text indicates Proactive
                if (this.isProactive) {
                    console.log("[UI] Proactive Force Triggered by user.");
                    this.updateStatus("Watching...", true);

                    // Use ApiClient
                    await api.force_proactive();
                }
            });
            this.statusText.style.cursor = 'pointer'; // Hint functionality
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

    // State
    private isProactive: boolean = false;

    // --- 3. Public API ---
    public async openChatPanel(open: boolean = true) {
        if (open === uiState.isChatOpen) return;
        uiState.isChatOpen = open;

        if (this.rightPanel) {
            this.rightPanel.classList.toggle('open', open);
        }
        if (this.chatToggleBtn) this.chatToggleBtn.classList.toggle('active', open);

        await LogManager.getInstance().resizeWindow();
    }

    public setProactiveState(enabled: boolean) {
        this.isProactive = enabled;
        console.log(`[UI] Proactive Mode: ${enabled}`);

        // Immediate status update
        if (enabled) {
            this.updateStatus("Proactive", true);
        } else {
            this.updateStatus("Idle", true);
        }
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
                    if (this.isProactive) {
                        this.statusDot.style.backgroundColor = '#00ffff'; // Cyan for Proactive
                        this.statusDot.style.boxShadow = '0 0 10px #00ffff';
                    } else {
                        this.statusDot.style.backgroundColor = '#ffa500'; // Orange
                        this.statusDot.style.boxShadow = 'none';
                    }
                    if (text === 'Watching...') {
                        this.statusDot.style.animation = 'pulse 2s infinite';
                    }
                    break;
            }
        }
    }

    public updateSuggestions(suggestions: string[], onClickCallback: (text: string) => void) {
        if (!this.suggestionToggleBtn || !this.suggestionPopup) return;
        this.suggestionPopup.innerHTML = '';

        console.log(`[UI] Received suggestions count: ${suggestions ? suggestions.length : 0}`);

        if (!suggestions || suggestions.length === 0) {
            this.suggestionToggleBtn.style.display = 'none';
            this.suggestionPopup.classList.remove('visible');
            return;
        }

        this.suggestionToggleBtn.style.display = 'flex';

        // CSS Grid handles layout, we just append items.
        const fixedNavs = ["もっと詳しく教えて", "他の話題について"];

        suggestions.forEach(text => {
            const chip = document.createElement('div');
            chip.className = 'suggestion-chip';

            // Check for Love Prefix
            let displayText = text;
            if (text.startsWith("❤ ")) {
                chip.classList.add('love-chip');
            }

            // Check for Fixed Nav
            if (fixedNavs.some(n => text.includes(n)) || text === "別の話題はある？") {
                chip.classList.add('static-nav');
            }

            chip.innerText = displayText;

            chip.addEventListener('click', () => {
                onClickCallback(text);
                this.suggestionPopup!.classList.remove('visible');
            });
            this.suggestionPopup!.appendChild(chip);
        });
    }

    public toggleSuggestions() {
        if (!this.suggestionPopup) return;
        this.suggestionPopup.classList.toggle('visible');
    }

    public switchLogTab(tabName: string) {
        // Tab Buttons
        const btns = document.querySelectorAll('.tab-btn');
        btns.forEach(btn => btn.classList.remove('active'));

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
            // Settings / Exit / Proactive / Feedback
            const proactiveMark = this.isProactive ? '✓ ' : '';
            this.contextMenu.innerHTML = `
                <div class="ctx-item" id="ctx-settings-action">
                    <span class="ctx-icon">⚙️</span>
                    <span>設定</span>
                </div>
                <div class="ctx-item" id="ctx-proactive-toggle">
                    <span class="ctx-icon">👁️</span>
                    <span>Proactive Mode ${proactiveMark}</span>
                </div>
                <div class="ctx-item" id="ctx-feedback-action">
                    <span class="ctx-icon">📝</span>
                    <span>議論を保存 (Feedback)</span>
                </div>
                <div class="ctx-item" id="ctx-dify-action">
                    <span class="ctx-icon">🌐</span>
                    <span>Dify検索 (Test)</span>
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
                document.getElementById('ctx-proactive-toggle')?.addEventListener('click', async () => {
                    this.contextMenu!.style.display = 'none';
                    const newState = !this.isProactive;
                    this.setProactiveState(newState);
                    await api.toggle_proactive(newState);
                });
                document.getElementById('ctx-feedback-action')?.addEventListener('click', async () => {
                    this.contextMenu!.style.display = 'none';
                    await (window as any).pywebview.api.save_current_discussion();
                });
                // New Dify Handler
                document.getElementById('ctx-dify-action')?.addEventListener('click', async () => {
                    this.contextMenu!.style.display = 'none';
                    console.log("[UI] Manually triggering Dify...");
                    // Assuming API method 'trigger_dify_workflow' exists
                    await (window as any).pywebview.api.trigger_dify_workflow('AI');
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
    public showToast(message: string, duration: number = 3000) {
        let toast = document.getElementById('ui-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'ui-toast';
            toast.style.position = 'fixed';
            toast.style.bottom = '30px';
            toast.style.left = '50%';
            toast.style.transform = 'translateX(-50%)';
            toast.style.backgroundColor = 'rgba(0,0,0,0.8)';
            toast.style.color = 'white';
            toast.style.padding = '10px 20px';
            toast.style.borderRadius = '5px';
            toast.style.zIndex = '9999';
            toast.style.transition = 'opacity 0.5s';
            document.body.appendChild(toast);
        }

        toast.innerText = message;
        toast.style.opacity = '1';
        toast.style.display = 'block';

        setTimeout(() => {
            if (toast) {
                toast.style.opacity = '0';
                setTimeout(() => { if (toast) toast.style.display = 'none'; }, 500);
            }
        }, duration);
    }
}
