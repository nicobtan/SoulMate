export type LogCategory = 'sys' | 'rag' | 'dbg';

export class LogManager {
    private static instance: LogManager;
    private debugContent: HTMLElement | null;
    private leftPanel: HTMLElement | null;
    private historyContent: HTMLElement | null;
    private debugTabs: HTMLElement | null;
    private panelTitle: HTMLElement | null;

    // UI State
    public isLogOpen: boolean = false;

    // Layout Config (Widths + Margins)
    private readonly CHAR_WIDTH = 500;
    private readonly LOG_TOTAL_WIDTH = 410; // 400px width + 10px margin
    private readonly CHAT_TOTAL_WIDTH = 490; // 450px width + 40px margin

    private constructor() {
        this.debugContent = document.getElementById('debug-content');
        this.leftPanel = document.getElementById('left-panel');
        this.historyContent = document.getElementById('history-content');
        this.debugTabs = document.getElementById('debug-tabs');
        this.panelTitle = document.getElementById('panel-title');

        this.initTabs();
        this.initButtons();

        // Expose globally for legacy calls
        (window as any).logToDebug = this.log.bind(this);
    }

    public static getInstance(): LogManager {
        if (!LogManager.instance) LogManager.instance = new LogManager();
        return LogManager.instance;
    }

    private initButtons() {
        const debugBtn = document.getElementById('debug-btn');
        const historyBtn = document.getElementById('history-btn');
        const closeBtn = document.getElementById('close-debug');

        if (debugBtn) debugBtn.addEventListener('click', () => this.togglePanel('debug'));
        if (historyBtn) historyBtn.addEventListener('click', () => this.togglePanel('history'));
        if (closeBtn) closeBtn.addEventListener('click', () => this.closePanel());
    }

    private initTabs() {
        const tabs = document.querySelectorAll('.log-tab');
        if (tabs && this.debugContent) {
            tabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    tabs.forEach(t => t.classList.remove('active'));
                    (e.target as HTMLElement).classList.add('active');
                    const viewMode = (e.target as HTMLElement).dataset.view;
                    if (viewMode && this.debugContent) {
                        this.debugContent.className = viewMode;
                        this.debugContent.scrollTop = this.debugContent.scrollHeight;
                    }
                });
            });
        }
    }

    public log(msg: string, type: 'info' | 'warn' | 'error' = 'info', category: LogCategory = 'sys') {
        if (!this.debugContent) return;

        const entry = document.createElement('div');
        entry.className = `log-entry cat-${category}`;
        const now = new Date();
        const timeStr = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
        entry.innerHTML = `<span class="log-time">${timeStr}</span> <span class="log-${type}">${msg}</span>`;

        this.debugContent.appendChild(entry);
        this.debugContent.scrollTop = this.debugContent.scrollHeight;
    }

    public async togglePanel(mode: 'debug' | 'history') {
        if (!this.leftPanel) return;

        // Check if currently open in same mode
        const currentMode = this.panelTitle?.innerText.includes('HISTORY') ? 'history' : 'debug';
        const isOpen = this.leftPanel.classList.contains('open');

        if (isOpen && currentMode === mode) {
            await this.closePanel();
        } else {
            await this.openPanel(mode);
        }
    }

    private async openPanel(mode: 'debug' | 'history') {
        if (!this.leftPanel) return;

        this.isLogOpen = true;
        this.leftPanel.classList.add('open');

        // UI Update
        if (this.debugContent) this.debugContent.style.display = (mode === 'debug') ? 'block' : 'none';
        if (this.historyContent) this.historyContent.style.display = (mode === 'history') ? 'block' : 'none';
        if (this.debugTabs) this.debugTabs.style.display = (mode === 'debug') ? 'flex' : 'none';

        if (this.panelTitle) {
            this.panelTitle.innerText = (mode === 'debug') ? 'SYSTEM LOGS' : 'CHAT HISTORY';
            this.panelTitle.style.color = (mode === 'debug') ? '#0f0' : '#0ff';
        }

        // Load History Callback
        if (mode === 'history' && (window as any).loadHistorySystematic) {
            (window as any).loadHistorySystematic();
        }

        await this.resizeWindow();
    }

    public async closePanel() {
        if (!this.leftPanel) return;
        this.isLogOpen = false;
        this.leftPanel.classList.remove('open');
        await this.resizeWindow();
    }

    // ★修正: 左右パネルの状態を見て、正しい合計幅を計算する
    public async resizeWindow() {
        if (!(window as any).pywebview) return;

        try {
            // Check Chat Panel State (DOM Check)
            const rightPanel = document.getElementById('right-panel');
            const isChatOpen = rightPanel ? rightPanel.classList.contains('open') : false;

            // Calculate Total Width
            let targetWidth = this.CHAR_WIDTH; // 500

            if (this.isLogOpen) targetWidth += this.LOG_TOTAL_WIDTH; // +410
            if (isChatOpen) targetWidth += this.CHAT_TOTAL_WIDTH;   // +490

            // Resize (Height fixed at 500)
            await (window as any).pywebview.api.resize_window(targetWidth, 500);

        } catch (e) {
            console.error("Window Resize Failed", e);
        }
    }
}
