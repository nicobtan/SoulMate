
export { }; // Make this a module

const sessionListEl = document.getElementById('session-list');
const chatViewEl = document.getElementById('chat-view');
const resumeBtn = document.getElementById('resume-btn') as HTMLButtonElement;
let selectedSessionId: number | null = null;

window.addEventListener('pywebviewready', async () => {
    loadSessions();
});

async function loadSessions() {
    if (!window.pywebview) return;
    try {
        const sessions = await window.pywebview.api.get_history_sessions();
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
        sessionListEl.innerHTML = '<div style="padding:20px;">履歴はありません</div>';
        return;
    }

    sessions.forEach(s => {
        const div = document.createElement('div');
        div.className = 'session-item';
        div.innerHTML = `
            <div class="session-date">${new Date(s.created_at).toLocaleString()}</div>
            <div class="session-title">${s.title || '無題の会話'}</div>
        `;
        div.onclick = () => loadDetail(s.id, div);
        sessionListEl.appendChild(div);
    });
}

async function loadDetail(id: number, el: HTMLElement) {
    selectedSessionId = id;

    // Highlight
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
    chatViewEl.scrollTop = chatViewEl.scrollHeight;
}

if (resumeBtn) {
    resumeBtn.onclick = async () => {
        // Debug Alert
        alert(`Resume Clicked. Session: ${selectedSessionId}`);

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
