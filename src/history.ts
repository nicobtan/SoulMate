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

async function loadSessions() {
    if (!window.pywebview) return;
    const keyword = searchInput ? searchInput.value : "";

    try {
        const sessions = await window.pywebview.api.get_history_sessions(keyword, isFavFilterOn);
        renderSessionList(sessions);
    } catch (e) {
        if (sessionListEl) sessionListEl.innerText = "Error loading history.";
        console.error(e);
    }
}

function renderSessionList(sessions: any[]) {
    if (!sessionListEl) return;
    sessionListEl.innerHTML = '';

    if (sessions.length === 0) {
        sessionListEl.innerHTML = '<div style="padding:20px; color:#888;">見つかりませんでした</div>';
        return;
    }

    sessions.forEach(s => {
        const div = document.createElement('div');
        div.className = 'session-item';
        if (s.id === selectedSessionId) div.classList.add('active');

        // Star Class
        const starClass = s.is_favorite ? 'active' : '';

        div.innerHTML = `
            <div class="session-info">
                <div class="session-date">${new Date(s.created_at).toLocaleString()}</div>
                <div class="session-title">${s.title || '無題の会話'}</div>
            </div>
            <div class="session-actions">
                <button class="icon-btn fav-btn ${starClass}" title="お気に入り">★</button>
                <button class="icon-btn del-btn" title="削除">🗑️</button>
            </div>
        `;

        // Item Click (Select)
        div.addEventListener('click', (e) => {
            loadDetail(s.id, div);
        });

        // Favorite Click
        const favBtn = div.querySelector('.fav-btn') as HTMLElement;
        if (favBtn) {
            favBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (!window.pywebview) return;
                const newState = !s.is_favorite;
                await window.pywebview.api.toggle_history_favorite(s.id, newState);
                s.is_favorite = newState; // Optimistic update
                favBtn.classList.toggle('active', newState);
                // If in filter mode, reload list might be needed, but UX-wise keeping it visible is ok
                if (isFavFilterOn && !newState) loadSessions();
            });
        }

        // Delete Click
        const delBtn = div.querySelector('.del-btn') as HTMLElement;
        if (delBtn) {
            delBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (confirm(`会話「${s.title}」を削除しますか？\nこの操作は取り消せません。`)) {
                    if (!window.pywebview) return;
                    await window.pywebview.api.delete_history_session(s.id);
                    if (selectedSessionId === s.id) {
                        if (chatViewEl) chatViewEl.innerHTML = '<div style="margin:auto; color:#888;">左のリストから会話を選択してください</div>';
                        if (resumeBtn) resumeBtn.disabled = true;
                        selectedSessionId = null;
                    }
                    loadSessions();
                }
            });
        }

        sessionListEl.appendChild(div);
    });
}

async function loadDetail(id: number, el: HTMLElement) {
    selectedSessionId = id;

    // UI Update
    document.querySelectorAll('.session-item').forEach(i => i.classList.remove('active'));
    el.classList.add('active');

    if (resumeBtn) resumeBtn.disabled = true;
    if (chatViewEl) chatViewEl.innerHTML = '<div style="margin:auto;">Loading...</div>';

    if (!window.pywebview) {
        if (chatViewEl) chatViewEl.innerText = "Error: PyWebview not found.";
        return;
    }

    try {
        const messages = await window.pywebview.api.get_history_messages(id);
        renderMessages(messages);
        if (resumeBtn) resumeBtn.disabled = false;
    } catch (e) {
        if (chatViewEl) chatViewEl.innerText = "Error loading messages.";
        console.error(e);
    }
}

function renderMessages(messages: any[]) {
    if (!chatViewEl) return;
    chatViewEl.innerHTML = '';
    messages.forEach(msg => {
        const div = document.createElement('div');
        div.className = `msg ${msg.role}`;
        div.innerText = msg.content;
        chatViewEl.appendChild(div);
    });
    // Scroll to bottom
    setTimeout(() => {
        chatViewEl.scrollTop = chatViewEl.scrollHeight;
    }, 10);
}

// Resume Button Logic
if (resumeBtn) {
    resumeBtn.onclick = async () => {
        if (!selectedSessionId) return;

        if (!window.pywebview) {
            alert("PyWebview environment required.");
            return;
        }

        resumeBtn.innerText = "復元中...";
        resumeBtn.disabled = true;
        try {
            // Python側に再開を依頼
            await window.pywebview.api.resume_history_session(selectedSessionId);
            // Python側でメインウィンドウ操作＆このウィンドウを閉じる処理が行われるはず
            // ここでは一応完了表示に戻す
            resumeBtn.innerText = "復元しました";
        } catch (e) {
            alert("再開に失敗しました");
            resumeBtn.disabled = false;
            resumeBtn.innerText = "この会話の続きをする ⏩";
            console.error(e);
        }
    };
}
