
import { api } from '../api_client.js';


export class HistoryManager {
    private static instance: HistoryManager;
    private isOpening: boolean = false;

    private constructor() {
        const btn = document.getElementById('history-btn');
        if (btn) {
            btn.addEventListener('click', () => this.open());
        }
    }

    public static getInstance(): HistoryManager {
        if (!HistoryManager.instance) HistoryManager.instance = new HistoryManager();
        return HistoryManager.instance;
    }

    public open() {
        if (this.isOpening) return;
        this.isOpening = true;

        if ((window as any).pywebview) {
            (window as any).pywebview.api.open_history_window();
        } else {
            console.warn("History Window requires PyWebview environment.");
        }

        // Reset flag after delay to allow retry if failed/closed quickly
        setTimeout(() => { this.isOpening = false; }, 2000);
    }
}
