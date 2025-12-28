export { }; // Make this a module

// Elements
const sessionListEl = document.getElementById('session-list');
const chatViewEl = document.getElementById('chat-view');
const resumeBtn = document.getElementById('resume-btn') as HTMLButtonElement;
const searchInput = document.getElementById('search-input') as HTMLInputElement;
const favFilterBtn = document.getElementById('fav-filter-btn') as HTMLElement;

// Tab Elements
const tabHistory = document.getElementById('tab-history');
const tabDiary = document.getElementById('tab-diary');

// State
let selectedSessionId: number | null = null;
let isFavFilterOn = false;
let searchTimeout: any = null;
let currentMode: 'history' | 'diary' = 'history';

// Init
window.addEventListener('pywebviewready', async () => {
    loadSessions();
});

// Tab Listeners
if (tabHistory) {
    tabHistory.addEventListener('click', () => switchMode('history'));
}
if (tabDiary) {
    tabDiary.addEventListener('click', () => switchMode('diary'));
}

function switchMode(mode: 'history' | 'diary') {
    currentMode = mode;
    if (tabHistory) tabHistory.classList.toggle('active', mode === 'history');
    if (tabDiary) tabDiary.classList.toggle('active', mode === 'diary');

    // UI Reset
    if (sessionListEl) sessionListEl.innerHTML = '<div style="padding:20px; text-align:center;">読み込み中...</div>';
    if (chatViewEl) chatViewEl.innerHTML = '<div style="margin:auto; text-align:center; color:#585b70;"><span style="font-size:3rem; display:block; margin-bottom:10px;">💬</span>左のリストから選択してください</div>';
    if (resumeBtn) resumeBtn.style.display = (mode === 'history') ? 'block' : 'none'; // Hide resume for diary

    selectedSessionId = null;
    loadSessions();
}

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
    console.log("[History] loadSessions called. Mode:", currentMode);
    const api = getApi();
    if (!api) {
        setTimeout(loadSessions, 100);
        return;
    }

    const keyword = searchInput ? searchInput.value : "";

    try {
        if (currentMode === 'history') {
            const sessions = await api.get_history_sessions(keyword, isFavFilterOn);
            renderSessionList(sessions);
        } else {
            // Diary Mode
            const diaries = await api.get_diary_list();
            renderDiaryList(diaries);
        }
    } catch (e) {
        if (sessionListEl) sessionListEl.innerText = "Error loading data.";
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

function renderDiaryList(diaries: any[]) {
    if (!sessionListEl) return;
    sessionListEl.innerHTML = '';

    if (diaries.length === 0) {
        sessionListEl.innerHTML = '<div style="padding:20px; text-align:center;">まだ日記がありません<br><span style="font-size:12px; color:#888;">(翌朝4時に生成されます)</span></div>';
        // Debug Button
        const dbgBtn = document.createElement('button');
        dbgBtn.innerText = "生成テスト (Debug)";
        dbgBtn.className = "btn-flat";
        dbgBtn.style.marginTop = "10px";
        dbgBtn.onclick = async () => {
            const api = getApi();
            if (api) {
                if (confirm("昨日分の日記を強制生成しますか？")) {
                    await api.generate_diary_manual();
                    setTimeout(loadSessions, 2000);
                }
            }
        };
        sessionListEl.appendChild(dbgBtn);
        return;
    }

    diaries.forEach(d => {
        const div = document.createElement('div');
        div.className = 'session-item';
        // Use ID for selection
        if (selectedSessionId === d.id) div.classList.add('active');

        div.innerHTML = `
            <div class="session-meta">
                <span class="session-date">${d.date}</span>
                <div class="session-actions">
                    <span style="font-size:16px;">${getTargetEmotionIcon(d.emotion)}</span>
                </div>
            </div>
            <div class="session-title">${d.title}</div>
        `;

        div.addEventListener('click', () => {
            loadDetail(d.id, div);
        });

        sessionListEl.appendChild(div);
    });
}

function getTargetEmotionIcon(emo: string) {
    if (!emo) return '📔';
    if (emo === 'happy') return '😊';
    if (emo === 'sad') return '😢';
    if (emo === 'angry') return '💢';
    if (emo === 'calm') return '😌';
    return '📔';
}

async function loadDetail(id: number, element: HTMLElement) {
    const api = getApi();
    if (!api || !chatViewEl) return;

    // UI Feedback
    document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    selectedSessionId = id;

    chatViewEl.innerHTML = '<div style="margin:auto;">読み込み中...</div>';

    try {
        if (currentMode === 'history') {
            const messages = await api.get_history_messages(id);
            renderMessages(messages);
            if (resumeBtn) resumeBtn.disabled = false;
        } else {
            // Diary Detail
            const diary = await api.get_diary_entry(id);
            renderDiaryDetail(diary);
        }
    } catch (e) {
        chatViewEl.innerHTML = 'Error loading content.';
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

function renderDiaryDetail(diary: any) {
    if (!chatViewEl) return;
    chatViewEl.innerHTML = '';

    if (!diary) {
        chatViewEl.innerHTML = "Diary not found.";
        return;
    }

    const container = document.createElement('div');
    container.className = 'diary-content-view';

    container.innerHTML = `
        <div class="diary-inner-container">
            <div class="diary-date">${diary.date} の日記</div>
            <div class="diary-title">${diary.title}</div>
            <div style="white-space: pre-wrap;">${diary.content}</div>
            <div style="margin-top:40px; text-align:center; opacity:0.6;">
                Generated by SoulMate
            </div>
        </div>
    `;

    chatViewEl.appendChild(container);
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
