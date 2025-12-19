
import { api } from '../api_client.js';
import { LogManager } from './log_manager.js';

export class HistoryManager {
    private static instance: HistoryManager;
    private isOpening: boolean = false;

    private constructor() {
        const btn = document.getElementById('history-btn');
        if (btn) {
            console.log("HistoryManager: Button found, attaching listener.");
            btn.addEventListener('click', () => {
                console.log("HistoryManager: Button clicked.");
                LogManager.getInstance().log("History Button Clicked", "info", "sys");
                this.open();
            });
        } else {
            console.error("HistoryManager: 'history-btn' not found in DOM.");
            LogManager.getInstance().log("History Button Not Found", "error", "sys");
        }
    }

    public static getInstance(): HistoryManager {
        if (!HistoryManager.instance) HistoryManager.instance = new HistoryManager();
        return HistoryManager.instance;
    }

    public open() {
        console.log(`HistoryManager: open() called. isOpening=${this.isOpening}`);
        LogManager.getInstance().log(`Attempting to open History Window (Locked: ${this.isOpening})`, "info", "sys");

        if (this.isOpening) {
            LogManager.getInstance().log("History Window opening is locked (debounce).", "warn", "sys");
            return;
        }
        this.isOpening = true;

        if ((window as any).pywebview) {
            console.log("HistoryManager: Calling pywebview.api.open_history_window()");
            (window as any).pywebview.api.open_history_window();
            LogManager.getInstance().log("Signal sent to open History Window.", "info", "sys");
        } else {
            console.warn("History Window requires PyWebview environment.");
            LogManager.getInstance().log("PyWebview environment missing.", "error", "sys");
        }

        // Reset flag after delay to allow retry if failed/closed quickly
        setTimeout(() => {
            this.isOpening = false;
            console.log("HistoryManager: Opening lock released.");
        }, 2000);
    }
}
