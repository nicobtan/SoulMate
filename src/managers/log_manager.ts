export type LogCategory = 'sys' | 'rag' | 'dbg';

export class LogManager {
    private static instance: LogManager;
    private leftPanel: HTMLElement | null;
    private historyContent: HTMLElement | null;
    private panelTitle: HTMLElement | null;

    // UI State
    public isLogOpen: boolean = false;

    // Layout Config (Widths + Margins)
    private readonly CHAR_WIDTH = 500;
    private readonly LOG_TOTAL_WIDTH = 410; // 400px width + 10px margin
    private readonly CHAT_TOTAL_WIDTH = 455; // 450px width + 5px margin

    private constructor() {
        this.leftPanel = document.getElementById('left-panel');
        this.historyContent = document.getElementById('history-content');
        this.panelTitle = document.getElementById('panel-title');

        this.initButtons();

        // Expose globally for legacy calls
        (window as any).logToDebug = this.log.bind(this);
        (window as any).logToMind = this.logToMind.bind(this);
    }

    public static getInstance(): LogManager {
        if (!LogManager.instance) LogManager.instance = new LogManager();
        return LogManager.instance;
    }

    private initButtons() {
        const debugBtn = document.getElementById('debug-btn');
        // const historyBtn = document.getElementById('history-btn'); // Handled by HistoryManager now
        const closeBtn = document.getElementById('close-debug');

        if (debugBtn) debugBtn.addEventListener('click', () => this.togglePanel());
        // if (historyBtn) historyBtn.addEventListener('click', () => this.togglePanel('history'));
        if (closeBtn) closeBtn.addEventListener('click', () => this.closePanel());
    }



    public log(msg: string, type: 'info' | 'warn' | 'error' = 'info', category: LogCategory = 'sys') {
        // Target Containers
        const logAll = document.getElementById('log-all');
        const logTarget = document.getElementById(`log-${category === 'dbg' ? 'mind' : category}`);

        // Ensure dbg maps to mind silently or sys? 
        // User asked dbg -> mind. So we map dbg to mind if not explicit.
        // Also map 'sys' to log-sys, 'rag' to log-rag.

        const now = new Date();
        const timeStr = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
        const contentHtml = `<span class="log-time">${timeStr}</span> <span class="log-${type}">${msg}</span>`;

        // 1. Append to All
        if (logAll) {
            const entry = document.createElement('div');
            entry.className = `log-entry cat-${category}`;
            entry.innerHTML = contentHtml;
            logAll.appendChild(entry);
            logAll.scrollTop = logAll.scrollHeight;
        }

        // 2. Append to Specific Category
        if (logTarget) {
            // For Mind, we might use different styling (handled by CSS/logToMind), 
            // but for standard log() calls just reuse entry style or redirect to logToMind if category is dbg?
            if (category === 'dbg') {
                // Redirect to structured mind log
                this.logToMind(`[DBG] ${msg}`);
            } else {
                const entry = document.createElement('div');
                entry.className = `log-entry cat-${category}`;
                entry.innerHTML = contentHtml;
                logTarget.appendChild(entry);
                logTarget.scrollTop = logTarget.scrollHeight;
            }
        }
    }

    public logToMind(msg: string) {
        const mindContent = document.getElementById('log-mind');

        // ★ User Request: Also log to ALL tab for visibility
        // We reuse the standard logging logic for 'all' tab targeting
        // Construct a simple entry manually or reuse log() logic?
        // Let's create a 'sys' style entry for ALL tab to keep it consistent
        const logAll = document.getElementById('log-all');
        const now = new Date();
        const timeStr = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;

        if (logAll) {
            const entry = document.createElement('div');
            entry.className = `log-entry cat-mind`; // Use cat-mind for styling
            // Strip detailed HTML or keep it simple? Mind logs might be long.
            entry.innerHTML = `<span class="log-time">${timeStr}</span> <span class="log-info" style="color:#aaddff;">${msg}</span>`;
            logAll.appendChild(entry);
            logAll.scrollTop = logAll.scrollHeight;
        }

        if (!mindContent) return;

        const entry = document.createElement('div');
        entry.className = 'mind-entry';

        const mindTimeStr = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}]`;

        let contentHtml = msg;
        let targetContent = mindContent;

        if (msg.includes("[Vision]")) {
            contentHtml = `<span style="color: #d19bf7;">${msg}</span>`;
            // Redirect to Vision Tab content
            const visionContent = document.getElementById('log-vision');
            if (visionContent) targetContent = visionContent;
        } else if (msg.includes("[RAG]")) {
            contentHtml = `<span style="color: #7ce38b;">${msg}</span>`;
        } else if (msg.includes("[Expression]")) {
            contentHtml = `<span style="color: #ffb366;">${msg}</span>`;
        }

        entry.innerHTML = `<span class="mind-timestamp">${mindTimeStr}</span> ${contentHtml}`;

        if (targetContent) {
            targetContent.appendChild(entry);
            targetContent.scrollTop = targetContent.scrollHeight;
        }
    }

    public async togglePanel() {
        if (!this.leftPanel) return;

        const isOpen = this.leftPanel.classList.contains('open');

        if (isOpen) {
            await this.closePanel();
        } else {
            await this.openPanel();
        }
    }

    private async openPanel() {
        if (!this.leftPanel) return;

        this.isLogOpen = true;
        this.leftPanel.classList.add('open');

        // UI Update (Debug Mode Only)
        // Tabs are managed by UIManager / CSS logic now
        // if (this.debugContent) this.debugContent.style.display = 'block';
        // if (this.debugTabs) this.debugTabs.style.display = 'flex';
        // Remove historyContent refs if strictly needed, but styling handles it if we don't open 'history' mode.

        if (this.panelTitle) {
            this.panelTitle.innerText = 'SYSTEM LOGS';
            this.panelTitle.style.color = '#0f0';
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
