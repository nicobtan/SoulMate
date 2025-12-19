
import { api } from '../api_client.js';

export class HistoryManager {
    private static instance: HistoryManager;

    private modal: HTMLElement | null;
    private listContainer: HTMLElement | null;
    private chatContainer: HTMLElement | null;
    private resumeBtn: HTMLElement | null;

    private selectedSessionId: number | null = null;

    private constructor() {
        this.modal = document.getElementById('history-modal');
        this.listContainer = document.getElementById('session-list');
        this.chatContainer = document.getElementById('history-chat-view');
        this.resumeBtn = document.getElementById('resume-session-btn');

        this.initListeners();
    }

    public static getInstance(): HistoryManager {
        if (!HistoryManager.instance) HistoryManager.instance = new HistoryManager();
        return HistoryManager.instance;
    }

    private initListeners() {
        // Close Button
        const closeBtn = document.getElementById('history-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Resume Button
        if (this.resumeBtn) {
            this.resumeBtn.addEventListener('click', () => this.resumeSession());
        }
    }

    public async open() {
        if (this.modal) {
            this.modal.style.display = 'flex';
            // Re-bind elements in case DOM re-rendered (though unlikely for static modal)
            this.listContainer = document.getElementById('session-list');
            this.chatContainer = document.getElementById('history-chat-view');
        }
        await this.loadSessionList();
    }

    public close() {
        if (this.modal) this.modal.style.display = 'none';
    }

    private async loadSessionList() {
        if (!this.listContainer) return;
        this.listContainer.innerHTML = '<div style="padding:20px; color:#888;">読み込み中...</div>';

        try {
            // API: GET /history/sessions
            const sessions: any[] = await api.get_sessions();

            this.listContainer.innerHTML = '';

            if (!sessions || sessions.length === 0) {
                this.listContainer.innerHTML = '<div style="padding:20px;">履歴はありません</div>';
                return;
            }

            sessions.forEach((s: any) => {
                const item = document.createElement('div');
                item.className = 'session-item';
                item.innerHTML = `
                    <div class="session-date">${new Date(s.created_at).toLocaleString()}</div>
                    <div class="session-title">${s.title || '無題の会話'}</div>
                `;
                item.addEventListener('click', () => {
                    // UI selection
                    document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    this.loadSessionDetail(s.id);
                });
                this.listContainer!.appendChild(item);
            });

        } catch (e) {
            console.error(e);
            this.listContainer.innerHTML = '<div style="padding:20px; color:red;">読み込みエラー</div>';
        }
    }

    private async loadSessionDetail(sessionId: number) {
        this.selectedSessionId = sessionId;
        if (!this.chatContainer) return;

        this.chatContainer.innerHTML = '<div style="padding:20px;">会話内容を取得中...</div>';
        if (this.resumeBtn) {
            this.resumeBtn.classList.remove('active');
            (this.resumeBtn as HTMLButtonElement).disabled = true;
        }

        try {
            // API: GET /history/{id}
            const data: any = await api.get_session_detail(sessionId);
            const messages = data.messages || [];

            this.chatContainer.innerHTML = '';

            messages.forEach((msg: any) => {
                const div = document.createElement('div');
                div.className = `hist-msg ${msg.role}`;
                div.innerText = msg.content;
                this.chatContainer!.appendChild(div);
            });

            // Scroll to bottom
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;

            // Enable Resume
            if (this.resumeBtn) {
                this.resumeBtn.classList.add('active');
                (this.resumeBtn as HTMLButtonElement).disabled = false;
            }

        } catch (e) {
            this.chatContainer.innerHTML = 'エラーが発生しました';
        }
    }

    private async resumeSession() {
        if (!this.selectedSessionId) return;

        const resumeBtn = this.resumeBtn as HTMLButtonElement;
        if (resumeBtn) resumeBtn.disabled = true;

        try {
            // 1. API: POST /historoy/{id}/resume
            // Backendから { messages: [], suggestions: [], ... } が返ってくる
            // api_clientのresume_sessionが返すオブジェクトを使用
            const data = await api.resume_session(this.selectedSessionId);

            // 2. モーダルを閉じる
            this.close();

            // 3. チャットウィンドウを開く
            // Import UIManager and ChatManager dynamically or assume global/import
            // Since we need to use them, let's ensure imports at top, but for now assuming we can access via getInstance or global.
            // But this file has imports. 
            // We need to add imports to the top of file or use window if exposed?
            // Safer to use imports. I will add imports in a separate edit if needed, or assume they are available if I edit top.
            // Wait, existing imports are only 'api'.
            // I should use the proper imports.
            // BUT, circular dependency risk? ChatManager -> HistoryManager? 
            // HistoryManager is imported in index.ts. ChatManager is imported in index.ts.
            // If I import ChatManager here, it might be fine.

            // For now, let's rely on globals EXPOSED in index.ts if any? 
            // no, ChatManager.getInstance() is standard.

            // Let's use dynamic imports or assume I will fix imports in next step?
            // No, I should do it properly. 
            // Use (window as any).soulBubbleManager... wait, ChatManager instance is needed.

            const { UIManager } = await import('./ui_manager.js');
            const { ChatManager } = await import('./chat_manager.js');

            const uiManager = UIManager.getInstance();
            await uiManager.openChatPanel(true);

            // 4. チャットログを復元
            const chatManager = ChatManager.getInstance();
            if (data.messages) {
                chatManager.loadConversation(data.messages);
            }

            // 5. サジェストを復元
            if (data.suggestions && data.suggestions.length > 0) {
                uiManager.updateSuggestions(data.suggestions, (text) => {
                    // サジェストクリック時の挙動 (ChatManager経由で送信)
                    chatManager.sendMessage(text);
                });
            } else {
                // サジェストがない場合はクリア
                uiManager.updateSuggestions([], () => { });
            }

            console.log("Session Resumed Successfully");

        } catch (e) {
            console.error(e);
            alert('再開に失敗しました');
        } finally {
            if (resumeBtn) resumeBtn.disabled = false;
        }
    }
}
