
import { ChatManager } from './chat_manager.js';
import { LogManager } from './log_manager.js';
import { UIManager } from './ui_manager.js';

declare const io: any; // CDN global

export class SocketClient {
    private static instance: SocketClient;
    private socket: any;

    private constructor() {
        // Lazy initialization
    }

    public static getInstance(): SocketClient {
        if (!SocketClient.instance) SocketClient.instance = new SocketClient();
        return SocketClient.instance;
    }

    public init() {
        if (this.socket) return; // Already initialized

        // Desktop Mode Check: Skip Socket.IO to avoid 404 errors (Main.py doesn't serve socket.io)
        if ((window as any).pywebview) {
            console.log("[Socket] Desktop Mode detected. Skipping Socket.IO connection.");
            return;
        }

        if (typeof io !== 'undefined') {
            // Auto-connect to current host
            this.socket = io({
                transports: ['websocket', 'polling']
            });
            this.initListeners();
            console.log("[Socket] Initialized");
        } else {
            console.warn("[Socket] socket.io client not found. Web Push disabled.");
        }
    }

    public disconnect() {
        if (this.socket && this.socket.connected) {
            this.socket.disconnect();
            console.log("[Socket] Force disconnected (Desktop Mode)");
        }
    }

    private initListeners() {
        this.socket.on('connect', () => {
            console.log(`[Socket] Connected: ${this.socket.id}`);
            UIManager.getInstance().updateStatus("Connected", true);
        });

        this.socket.on('disconnect', () => {
            console.log("[Socket] Disconnected");
            UIManager.getInstance().updateStatus("Disconnected", false);
        });

        // --- Core Events ---

        // 1. Proactive/Push Message (Includes Audio)
        // Data format matches what handlePushMessage expects: { text: "...", audio: "path", emotion: "...", suggestions: [] }
        this.socket.on('chat_message', (data: any) => {
            console.log("[Socket] Received chat_message:", data);
            ChatManager.getInstance().handlePushMessage(data);
        });

        // 2. Debug Logs
        this.socket.on('debug_log', (data: any) => {
            // data: { msg: "...", level: "info", category: "sys" }
            const { msg, level, category } = data;
            LogManager.getInstance().log(msg, level || 'info', category || 'sys');
        });

        // 3. Mind Logs
        this.socket.on('mind_log', (data: any) => {
            // data: { msg: "..." }
            const { msg } = data;
            // Use translation logic inside LogManager or BaseApiMixin on server?
            // Server BaseApiMixin.log_to_mind already translates.
            // So 'msg' here is likely translated text or raw?
            // BaseApiMixin log_to_mind emits translated text if we implement it so.
            // Let's assume server sends ready-to-display text.
            // But wait, server BaseApiMixin uses 'evaluate_js("logToMind...")'.
            // We will override it to emit 'mind_log'.

            // LogManager doesn't have explicit logToMind method exposed easily, 
            // but log(..., 'mind') goes to mind tab effectively?
            // Let's check LogManager later. Yes, category='mind'.
            LogManager.getInstance().log(msg, 'info', 'mind' as any);
        });

        // 4. Ghost Message (Filler)
        this.socket.on('ghost_message', (data: any) => {
            ChatManager.getInstance().showGhostMessage(data.text);
        });

        // 5. Play Audio (Streamed Data)
        this.socket.on('play_audio', (data: any) => {
            // data: { audio: "base64..." }
            if (data.audio) {
                import('../services/audio_manager.js').then(({ AudioManager }) => {
                    // Prefix for WAV as per server sending WAV
                    const src = "data:audio/wav;base64," + data.audio;
                    AudioManager.getInstance().enqueue(src);
                });
            }
        });

        // 6. Play Audio (URL Command)
        this.socket.on('play_audio_command', (data: any) => {
            // data: { url: "..." }
            // Direct audio play for fillers
            // Use AudioManager
            import('../services/audio_manager.js').then(({ AudioManager }) => {
                AudioManager.getInstance().play(data.url);
            });
        });
    }
}
