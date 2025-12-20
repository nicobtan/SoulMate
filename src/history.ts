export { }; // Make this a module

// Elements
const sessionListEl = document.getElementById('session-list');
const chatViewEl = document.getElementById('chat-view');
const resumeBtn = document.getElementById('resume-btn') as HTMLButtonElement;
const searchInput = document.getElementById('search-input') as HTMLInputElement;
const favFilterBtn = document.getElementById('fav-filter-btn') as HTMLElement;

let selectedSessionId: number | null = null;
let isFavFilterOn = false;
let searchTimeout: any = null;

// Init
window.addEventListener('pywebviewready', async () => {
    loadSessions();
});

// Search & Filter Listeners
if (searchInput) {
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadSessions(), 300); // Debounce
    });
}

if (favFilterBtn) {
    favFilterBtn.addEventListener('click', () => {
        isFavFilterOn = !isFavFilterOn;
        favFilterBtn.classList.toggle('active', isFavFilterOn);
        loadSessions();
    });
}

const getApi = () => (window as any).pywebview?.api;

async function loadSessions() {
    console.log("[History] loadSessions called. api ready?", !!getApi());
    const api = getApi();
    if (!api) {
        // もしapiがまだなら少し待って再試行
        setTimeout(loadSessions, 100);
        return;
    }
    const keyword = searchInput ? searchInput.value : "";

    try {
        const sessions = await api.get_history_sessions(keyword, isFavFilterOn);
        console.log(`[History] Loaded ${sessions.length} sessions.`);
        renderSessionList(sessions);
    } catch (e) {
        if (sessionListEl) sessionListEl.innerText = "Error loading history.";
        console.error("[History] Load failed:", e);
    }
}

function renderSessionList(sessions: any[]) {
    if (!sessionListEl) return;
    sessionListEl.innerHTML = '';

    if (sessions.length === 0) {
        sessionListEl.innerHTML = '<div style="padding:20px; text-align:center; color:#585b70;">思い出は見つかりませんでした</div>';
        return;
    }

    sessions.forEach(s => {
        const div = document.createElement('div');
        div.className = 'session-item';
        if (s.id === selectedSessionId) div.classList.add('active');

        const starClass = s.is_favorite ? 'active' : '';
        const displayDate = new Date(s.updated_at || s.created_at).toLocaleString('ja-JP', {
            month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
        });

        div.innerHTML = `
            <div class="session-meta">
                <span class="session-date">${displayDate}</span>
                <div class="session-actions">
                    <button class="icon-btn fav-btn ${starClass}" title="お気に入り">★</button>
                    <button class="icon-btn del-btn" title="削除">🗑️</button>
                </div>
            </div>
            <div class="session-title">${s.title || '無題の会話'}</div>
        `;

        div.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            if (target.classList.contains('icon-btn') || target.parentElement?.classList.contains('icon-btn')) return;
            loadDetail(s.id, div);
        });

        const favBtn = div.querySelector('.fav-btn') as HTMLElement;
        if (favBtn) {
            favBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const api = getApi();
                if (!api) return;
                const newState = !s.is_favorite;
                await api.toggle_history_favorite(s.id, newState);
                s.is_favorite = newState;
                favBtn.classList.toggle('active', newState);
                if (isFavFilterOn && !newState) loadSessions();
            });
        }

        const delBtn = div.querySelector('.del-btn') as HTMLElement;
        if (delBtn) {
            delBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const api = getApi();
                if (!api) return;
                if (!confirm("この会話を削除してもいいかしら？")) return;
                await api.delete_history_session(s.id);
                loadSessions();
                if (selectedSessionId === s.id) {
                    if (chatViewEl) chatViewEl.innerHTML = '';
                    if (resumeBtn) resumeBtn.disabled = true;
                }
            });
        }

        sessionListEl.appendChild(div);
    });
}

async function loadDetail(sessionId: number, element: HTMLElement) {
    const api = getApi();
    if (!api || !chatViewEl) return;

    // UI Feedback
    document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    selectedSessionId = sessionId;

    chatViewEl.innerHTML = '<div style="margin:auto;">読み込み中...</div>';

    try {
        const messages = await api.get_history_messages(sessionId);
        renderMessages(messages);
        if (resumeBtn) resumeBtn.disabled = false;
    } catch (e) {
        chatViewEl.innerHTML = 'Error loading messages.';
    }
}

function renderMessages(messages: any[]) {
    if (!chatViewEl) return;
    chatViewEl.innerHTML = '';

    messages.forEach(m => {
        const div = document.createElement('div');
        div.className = `msg ${m.role}`;

        const content = document.createElement('div');
        content.innerText = m.content;
        div.appendChild(content);

        const time = document.createElement('span');
        time.className = 'msg-time';
        time.innerText = new Date(m.created_at).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
        div.appendChild(time);

        chatViewEl.appendChild(div);
    });

    chatViewEl.scrollTop = chatViewEl.scrollHeight;
}

// Resume Button Logic
if (resumeBtn) {
    resumeBtn.addEventListener('click', async () => {
        const api = getApi();
        if (!api || !selectedSessionId) return;
        await api.resume_history_session(selectedSessionId);
    });
}

// --- Manual Save / Clear Buttons ---
const manualSaveBtn = document.getElementById('manual-save-btn');
const manualClearBtn = document.getElementById('manual-clear-btn');

if (manualSaveBtn) {
    manualSaveBtn.addEventListener('click', async () => {
        const api = getApi();
        if (!api) return;
        const originalText = manualSaveBtn.innerHTML;
        manualSaveBtn.innerHTML = "<span>⏳</span> 保存中...";
        try {
            await api.manual_save_session();
            await loadSessions();
            manualSaveBtn.innerHTML = "<span>✅</span> 完了!";
            setTimeout(() => {
                if (manualSaveBtn) manualSaveBtn.innerHTML = originalText;
            }, 2000);
        } catch (e) {
            alert("保存に失敗しました");
            manualSaveBtn.innerHTML = originalText;
        }
    });
}

if (manualClearBtn) {
    manualClearBtn.addEventListener('click', async () => {
        const api = getApi();
        if (!api) return;
        if (!confirm("現在の会話を終了して、新しく始めますか？\n（今の会話は履歴に残ります）")) return;
        try {
            await api.start_new_session();
            await loadSessions();
            if (chatViewEl) chatViewEl.innerHTML = '<div style="margin:auto; color:#888;">新しい会話を開始しました</div>';
            if (resumeBtn) resumeBtn.disabled = true;
            selectedSessionId = null;
        } catch (e) {
            alert("新規作成に失敗しました");
        }
    });
}
