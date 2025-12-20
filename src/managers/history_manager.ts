
export class HistoryManager {
    private static instance: HistoryManager;

    private constructor() {
        // 初期化ロジック不要
    }

    public static getInstance(): HistoryManager {
        if (!HistoryManager.instance) HistoryManager.instance = new HistoryManager();
        return HistoryManager.instance;
    }

    public open() {
        console.log("[HistoryManager] Requesting to open History Window...");

        // 左パネル(System Log)が開いていたら閉じる（干渉防止）
        const leftPanel = document.getElementById('left-panel');
        if (leftPanel && leftPanel.classList.contains('open')) {
            // 今回はシンプルに何もしない（API呼び出しだけする）。
        }

        // 新しいウィンドウを開くAPIを呼ぶ
        if ((window as any).pywebview) {
            (window as any).pywebview.api.open_history_window();
        } else {
            console.warn("History Window requires PyWebview.");
        }
    }
}
