// src/managers/chat_manager.ts
import { api } from '../api_client.js';
import { LogManager } from './log_manager.js';
import { UIManager } from './ui_manager.js';
import { Live2DManager } from './live2d_manager.js';
import { AudioManager } from '../services/audio_manager.js';
import { emotions, categoryIcons, categoryMapping } from '../constants.js'; // constantsからimport

export class ChatManager {
    private static instance: ChatManager;
    private chatInput: HTMLTextAreaElement | null;
    private chatLogArea: HTMLElement | null;
    private previewArea: HTMLElement | null; // ★追加
    private previewContainer: HTMLElement | null; // ★追加
    private isVisionProcessing: boolean = false;
    private soulBubbleManager: any = null; // Reference
    private pendingAttachment: string | null = null; // ★追加

    // Audio Controls
    private audioPlayer: HTMLElement | null;
    private audioSpeedBtn: HTMLElement | null;
    private audioStopBtn: HTMLElement | null;
    private currentSpeedIndex: number = 0; // 0=x1.0
    private readonly speeds = [1.0, 1.25, 1.5, 2.0];

    private constructor() {
        this.chatInput = document.getElementById('chat-input') as HTMLTextAreaElement;
        this.chatLogArea = document.getElementById('chat-log-area');

        this.audioPlayer = document.getElementById('audio-player');
        this.audioSpeedBtn = document.getElementById('audio-speed-btn');
        this.audioStopBtn = document.getElementById('audio-stop-btn');

        this.previewArea = document.getElementById('attachment-preview-area');
        this.previewContainer = document.getElementById('preview-thumbnail-container');

        this.initListeners();

        // Expose global hook for Backend Push
        (window as any).receiveMessage = this.handlePushMessage.bind(this);

        // Expose global hook for History Restoration (Signal)
        (window as any).reloadSession = async (sessionId: number) => {
            console.log(`[ChatManager] Reloading session ${sessionId}...`);
            try {
                UIManager.getInstance().openChatPanel(true);
                // Fetch fresh data from API
                const data: any = await api.get_session_detail(sessionId);
                if (data.messages) {
                    this.loadConversation(data.messages);
                }
            } catch (e) {
                console.error("Failed to reload session:", e);
                this.addLog("セッションの復元に失敗しました", 'ai');
            }
        };
    }

    public static getInstance(): ChatManager {
        if (!ChatManager.instance) ChatManager.instance = new ChatManager();
        return ChatManager.instance;
    }

    // Call this after DOM Ready
    public init() {
        // SoulBubbleManagerはindex.tsで生成されてwindowにある前提、またはここで取得
        this.soulBubbleManager = (window as any).soulBubbleManager;
        this.initAudioListeners();
        console.log("ChatManager Initialized");
    }

    // ★追加: 会話ログを丸ごと置き換えるメソッド
    public loadConversation(messages: any[]) {
        if (!this.chatLogArea) return;

        // 1. クリア
        this.chatLogArea.innerHTML = '';

        // 2. 再描画
        messages.forEach(msg => {
            // DBのカラム名と合わせる (msg.content)
            const text = msg.content || "";
            const role = msg.role || "user";

            // 既存のaddLogはタイムスタンプを現在時刻にするため、
            // ここでは簡易的にaddLogを使う（タイムスタンプは現在になるが許容範囲）
            this.addLog(text, role as 'user' | 'ai');
        });

        // 3. 最下部へスクロール
        this.chatLogArea.scrollTop = this.chatLogArea.scrollHeight;

        console.log(`[ChatManager] Loaded ${messages.length} messages.`);
    }

    private initAudioListeners() {
        const am = AudioManager.getInstance();

        // 1. Play State -> UI Visibility
        am.onPlayStateChange = (isPlaying) => {
            if (this.audioPlayer) {
                if (isPlaying) {
                    this.audioPlayer.style.display = 'flex';
                    requestAnimationFrame(() => this.audioPlayer!.classList.add('visible'));
                } else {
                    this.audioPlayer.classList.remove('visible');
                    setTimeout(() => {
                        if (!this.audioPlayer!.classList.contains('visible')) {
                            this.audioPlayer!.style.display = 'none';
                        }
                    }, 300);
                }
            }
        };

        // 2. Stop Button
        if (this.audioStopBtn) {
            this.audioStopBtn.addEventListener('click', () => am.stop());
        }

        // 3. Speed Button (Left/Right Click)
        if (this.audioSpeedBtn) {
            // 左クリック: 加速
            this.audioSpeedBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.changeSpeed(1);
            });
            // 右クリック: 減速
            this.audioSpeedBtn.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                this.changeSpeed(-1);
            });
        }
    }

    private changeSpeed(direction: number) {
        this.currentSpeedIndex += direction;

        // Loop around
        if (this.currentSpeedIndex >= this.speeds.length) this.currentSpeedIndex = 0;
        if (this.currentSpeedIndex < 0) this.currentSpeedIndex = this.speeds.length - 1;

        const newSpeed = this.speeds[this.currentSpeedIndex];

        // Apply to Audio
        const am = AudioManager.getInstance();
        if (am.audio) {
            am.audio.playbackRate = newSpeed;
        }

        // Update Button Text
        if (this.audioSpeedBtn) {
            this.audioSpeedBtn.innerText = `x${newSpeed.toFixed(1)}`; // x1.0, x1.5...
        }
    }

    private initListeners() {
        const sendBtn = document.getElementById('send-button'); // or chat-send-btn
        // Actually ID in index.html is 'chat-send-btn' usually, verify if needed. 
        // Code snippet said 'send-button' // or chat-send-btn. 
        // Let's check index.ts previous view... it was 'chat-send-btn'.
        // I'll stick to 'chat-send-btn' if 'send-button' is not found.
        const actualSendBtn = document.getElementById('chat-send-btn') || document.getElementById('send-button');
        if (actualSendBtn) actualSendBtn.addEventListener('click', () => this.sendMessage());

        if (this.chatInput) {
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Vision Button
        const visionBtn = document.getElementById('vision-btn');
        if (visionBtn) {
            visionBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.chatWithVision("screen");
            });
            visionBtn.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                this.chatWithVision("clipboard");
            });
        }

        // Force Talk
        const forceBtn = document.getElementById('force-talk-btn');
        if (forceBtn) {
            forceBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.triggerForceTalk();
            });
        }
    }

    // ★ New: Bubble Logic Helper
    public showSoulBubble(rawCategory: string, text: string, actionId: string, type: string = 'normal') {
        if (!this.soulBubbleManager) {
            this.soulBubbleManager = (window as any).soulBubbleManager;
            if (!this.soulBubbleManager) return;
        }

        const rawLower = rawCategory ? rawCategory.toLowerCase().trim() : 'topic';

        // ★修正: カテゴリマップにないものは「topic (青)」か「suggestion (オレンジ)」に強制統一する
        // これで「グレーのバルーン」が出るのを防ぎます
        let styleCategory = categoryMapping[rawLower];

        if (!styleCategory) {
            // 未知のカテゴリ (utility, space等) が来た場合のフォールバック
            if (rawLower.includes('news') || rawLower.includes('tech')) styleCategory = 'news';
            else if (rawLower.includes('game') || rawLower.includes('fun')) styleCategory = 'fun';
            else styleCategory = 'topic'; // デフォルトは青色
        }

        // アイコン決定
        let displayText = text;
        if (categoryIcons[styleCategory]) {
            displayText = categoryIcons[styleCategory];
        } else if (text.length > 4) {
            displayText = '💭';
        }

        // Managerへ追加
        this.soulBubbleManager.addBubble(styleCategory, displayText, text, actionId, type);
        console.log(`[ChatManager] Bubble Added: ${styleCategory} -> ${displayText}`);
    }

    public async sendMessage(overrideText?: string) {
        // Ensure Audio
        Live2DManager.getInstance().ensureAudioContext();

        const text = overrideText || this.chatInput?.value.trim();
        if (!text && !this.pendingAttachment) return; // 何もなければ送信しない

        // UI Updates
        // 画像がある場合はログに表示
        if (this.pendingAttachment) {
            const imgHtml = `<img src="${this.pendingAttachment}" style="max-width: 200px; border-radius: 8px; margin: 5px 0; display: block;">`;
            this.addRawLog(imgHtml, 'user');
        }

        if (text) {
            this.addLog(text, 'user');
        }

        const currentAttachment = this.pendingAttachment;
        this.clearAttachment(); // 送信開始時にクリア

        if (this.chatInput) this.chatInput.value = '';

        const thinkingId = this.addLog('考え中...', 'ai', true);
        UIManager.getInstance().updateStatus("Thinking...");

        try {
            // chat APIを画像付きで呼ぶ
            const response = await api.chat(text || "", currentAttachment || undefined);
            this.removeLog(thinkingId);
            UIManager.getInstance().updateStatus("Active");

            this.handleResponseObject(response);

        } catch (e: any) {
            this.removeLog(thinkingId);
            this.addLog(`Error: ${e.message}`, 'ai');
            UIManager.getInstance().updateStatus("Error", false);
            // If error, also output to raw log or console
            console.error(e);
        }
    }

    public async triggerForceTalk() {
        Live2DManager.getInstance().ensureAudioContext();
        UIManager.getInstance().openChatPanel(true);

        const thinkingId = this.addLog('...', 'ai', true);
        UIManager.getInstance().updateStatus("Thinking...");

        try {
            const response = await api.force_talk();
            this.removeLog(thinkingId);
            UIManager.getInstance().updateStatus("Active");
            this.handleResponseObject(response);
        } catch (e: any) {
            this.removeLog(thinkingId);
            this.addLog(`Error: ${e.message}`, 'ai');
            UIManager.getInstance().updateStatus("Error", false);
        }
    }

    public async chatWithVision(mode: string) {
        if (this.isVisionProcessing) return;
        this.isVisionProcessing = true;

        UIManager.getInstance().updateStatus("Capturing...");

        try {
            // 即時送信せず、プレビュー用に取得するだけにする
            const res = await (window as any).pywebview.api.take_screenshot_for_preview(mode);
            if (res.status === 'success' && res.image_data) {
                this.attachImage(res.image_data);
                UIManager.getInstance().openChatPanel(true);
            } else {
                this.addLog("画像の取得に失敗しました", 'ai');
            }
        } catch (e: any) {
            console.error(e);
            this.addLog(`Error: ${e.message}`, 'ai');
        } finally {
            this.isVisionProcessing = false;
            UIManager.getInstance().updateStatus("Active");
        }
    }

    // --- Attachment Helper Methods ---
    public attachImage(dataUrl: string) {
        this.pendingAttachment = dataUrl;
        this.updatePreviewUI();
    }

    public clearAttachment() {
        this.pendingAttachment = null;
        this.updatePreviewUI();
    }

    private updatePreviewUI() {
        if (!this.previewArea || !this.previewContainer) return;

        if (this.pendingAttachment) {
            this.previewArea.style.display = 'flex';
            this.previewContainer.innerHTML = `
                <img src="${this.pendingAttachment}" class="preview-thumb">
                <button class="preview-close" id="preview-close-btn">×</button>
            `;
            // 閉じるボタンのイベント
            document.getElementById('preview-close-btn')?.addEventListener('click', () => {
                this.clearAttachment();
            });
        } else {
            this.previewArea.style.display = 'none';
            this.previewContainer.innerHTML = '';
        }
    }

    public handlePushMessage(data: any, audio: string | null = null) {
        Live2DManager.getInstance().ensureAudioContext();

        let text = "";
        let audioData = audio;
        let suggestions: string[] = [];

        if (typeof data === 'string') {
            text = data;
        } else {
            text = data.response || data.text || "";
            // If data has audio attached, use it? usually audio arg is passed separately in current backend.
            // But if data object has it, prioritize it? or not.
            // The signature is (data, audio).
            suggestions = data.suggestions || [];
        }

        this.processAIResponse(text, audioData);
        UIManager.getInstance().updateSuggestions(suggestions, (t) => this.sendMessage(t));
    }

    private handleResponseObject(response: any) {
        let text = "";
        let audio = null;
        let suggestions: string[] = [];
        let grounding = null;

        if (typeof response === 'string') {
            text = response;
        } else {
            text = response.text;
            audio = response.audio;
            suggestions = response.suggestions || [];
            grounding = response.grounding_info;
        }

        // Output
        this.processAIResponse(text, audio, grounding);
        UIManager.getInstance().updateSuggestions(suggestions, (t) => this.sendMessage(t));
    }

    private processAIResponse(text: string, audio: string | null, grounding: any = null) {
        // 1. Emotion Parse
        let displayMsg = text;
        let emotionId = null;

        for (const [tag, exp] of Object.entries(emotions)) {
            if (text.includes(tag)) {
                emotionId = exp;
                displayMsg = displayMsg.replace(tag, '');
            }
        }

        // 2. Trigger Live2D
        if (emotionId) {
            Live2DManager.getInstance().triggerExpression(emotionId);
        }

        // 3. UI Log
        this.addLog(displayMsg, 'ai');

        // 4. Audio
        if (audio) {
            AudioManager.getInstance().play(audio);
        }

        // 5. Grounding Info (RAG)
        if (grounding) {
            // Format grounding info nicely? or just raw log.
            // LogManager has methods for this? 
            // Previous code had nice HTML formatting for RAG.
            // Let's use LogManager.log but maybe we need a dedicated display?
            // The LogManager log just puts it in the sys log or rag log.
            // Let's format it briefly.
            let msg = "RAG Info Received";
            if (grounding.web_search_queries) msg += ` Queries: ${grounding.web_search_queries}`;

            // To render clickable links in "RAG" tab, we need to pass HTML likely.
            // LogManager.log renders text? 
            // In index.ts refactor step 2, we saw addDebugLog logic.
            // LogManager should handle 'rag' type.
            LogManager.getInstance().log(`RAG Source: ${JSON.stringify(grounding)}`, 'info', 'rag');
        }
    }

    // --- Helpers ---
    private addLog(text: string, type: 'user' | 'ai', isThinking = false): string {
        if (!this.chatLogArea) return '';
        const div = document.createElement('div');
        // ★修正: Date.now() だけでは高速処理時に衝突するため、ランダム値を付与
        const id = 'msg-' + Date.now() + '-' + Math.floor(Math.random() * 10000);
        div.id = id;
        div.className = `message ${type}`;

        // Simple text with linkify?
        // The previous index.ts had processTextForLinks.
        // For now, simple text or innerHTML if we assume text is safe.
        // User instructions used innerText.
        div.innerText = text; // or use innerHTML if rich text needed

        if (isThinking) {
            div.style.fontStyle = 'italic';
            div.style.color = '#aaa';
        } else {
            // Timestamp
            const span = document.createElement('span');
            span.className = 'msg-timestamp';
            span.innerText = new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
            div.appendChild(span);
        }

        this.chatLogArea.appendChild(div);
        this.chatLogArea.scrollTop = this.chatLogArea.scrollHeight;
        return id;
    }

    private addRawLog(html: string, type: 'user' | 'ai') {
        if (!this.chatLogArea) return;
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.innerHTML = html;
        this.chatLogArea.appendChild(div);
        this.chatLogArea.scrollTop = this.chatLogArea.scrollHeight;
    }

    private removeLog(id: string) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }
}

// ★ Pythonから呼ばれる関数を定義 (User Request / Legacy Support)
(window as any).restoreChat = (messagesJson: string) => {
    console.log("[Restore] Received data from Python (restoreChat)");
    try {
        const messages = JSON.parse(messagesJson);
        ChatManager.getInstance().loadConversation(messages);
    } catch (e) {
        console.error("Failed to restore chat:", e);
    }
};

// ★ 新しい復元用フック (restoreChatV2)
(window as any).restoreChatV2 = (jsonStr: string) => {
    console.log("[Restore V2] Received data");
    try {
        const data = JSON.parse(jsonStr);
        const { title, messages, suggestions } = data;

        const cm = ChatManager.getInstance();
        const ui = UIManager.getInstance();
        const log = LogManager.getInstance();

        // 1. チャットログ復元
        cm.loadConversation(messages);

        // 2. パネルを開く
        ui.openChatPanel(true);

        // 3. サジェスト復元
        if (suggestions && suggestions.length > 0) {
            ui.updateSuggestions(suggestions, (t) => cm.sendMessage(t));
        } else {
            // Default suggestions if none
            ui.updateSuggestions(['何ができる？', '今日の運勢は？'], (t) => cm.sendMessage(t));
        }

        // 4. システムログ出力
        // "YYYY/MM/DD HH:MM Title talk is loaded."
        const now = new Date();
        const timeStr = `${now.getFullYear()}/${(now.getMonth() + 1).toString().padStart(2, '0')}/${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        log.log(`${timeStr} "${title}" talk is loaded.`, "info", "sys");

    } catch (e) {
        console.error("Failed to restore chat V2:", e);
    }
};
// ★ Pythonから呼ばれてチャット画面をクリアする
(window as any).clearChatLog = () => {
    console.log("[ChatManager] Clearing chat log for new session...");
    const logArea = document.getElementById('chat-log-area');
    if (logArea) {
        logArea.innerHTML = '';
        // システムログにも出力
        LogManager.getInstance().log("Session cleared. Started new conversation.", "info", "sys");
    }
};
