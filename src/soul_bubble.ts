export class SoulBubbleManager {
    private container: HTMLElement | null;
    private trashZone: HTMLElement | null;
    private activeBubbles: HTMLElement[] = [];

    // Drag State
    private isDragging = false;
    private dragTarget: HTMLElement | null = null;
    private dragOffsetX = 0;
    private dragOffsetY = 0;
    private startX = 0;
    private startY = 0;

    constructor() {
        this.container = document.getElementById('soul-bubble-container');
        this.trashZone = document.getElementById('trash-zone');

        window.addEventListener('mouseup', (e) => this.endDrag(e));
        window.addEventListener('mousemove', (e) => this.onDrag(e));

        // 背景クリックでバルーンを閉じる処理
        // #character-area かその親へのクリックを検知
        document.addEventListener('mousedown', (e) => {
            const target = e.target as HTMLElement;
            // バルーン以外のクリックなら閉じる
            if (!target.closest('.soul-bubble')) {
                this.collapseAll();
            }
        });
    }

    public collapseAll() {
        this.activeBubbles.forEach(b => {
            if (b.classList.contains('expanded')) {
                b.classList.remove('expanded');
                b.innerText = b.dataset.icon || '';
                b.style.animation = `gentleFloat ${3 + Math.random()}s infinite ease-in-out`;
                // CSSリセット (固定位置解除)
                b.style.position = '';
                b.style.transform = '';
            }
        });
    }

    // ★修正: icon と fullText を別々に受け取る
    public addBubble(category: string, icon: string, fullText: string, actionId: string, type: string = 'normal') {
        if (!this.container) return;

        const bubble = document.createElement('div');
        bubble.className = `soul-bubble ${category} bubble-${category}`;

        // 初期表示はアイコン
        bubble.innerText = icon;

        // データを保持
        bubble.dataset.icon = icon;
        bubble.dataset.fullText = fullText;
        bubble.dataset.actionId = actionId;
        bubble.dataset.category = category;

        // 初期配置
        const randomX = 180 + Math.random() * 140;
        const randomY = 60 + Math.random() * 100;
        bubble.style.left = `${randomX}px`;
        bubble.style.top = `${randomY}px`;

        // mousedown でドラッグ開始 (expandedでも発火させるため条件除去は startDrag 内で行うか、ここで行わない)
        bubble.addEventListener('mousedown', (e) => this.startDrag(e, bubble));

        this.container.appendChild(bubble);
        this.activeBubbles.push(bubble);

        requestAnimationFrame(() => {
            bubble.classList.add('appeared');
            bubble.style.animation = `gentleFloat ${3 + Math.random()}s infinite ease-in-out`;
        });
    }

    private startDrag(e: MouseEvent, bubble: HTMLElement) {
        if (e.button !== 0) return;

        // 拡大中でもクリックイベントを通すために return しない！
        // ただし、拡大中は「ドラッグ移動」だけ無効化する (onDragで制御)

        e.preventDefault();
        e.stopPropagation(); // 背景クリックでの閉じる処理を防止

        this.isDragging = true;
        this.dragTarget = bubble;
        this.startX = e.clientX;
        this.startY = e.clientY;

        const rect = bubble.getBoundingClientRect();
        this.dragOffsetX = e.clientX - rect.left;
        this.dragOffsetY = e.clientY - rect.top;

        // 拡大中でなければアニメーション停止
        if (!bubble.classList.contains('expanded')) {
            bubble.style.animation = 'none';
        }

        bubble.classList.add('dragging');
        if (this.trashZone && !bubble.classList.contains('expanded')) {
            this.trashZone.classList.add('visible');
        }
    }

    private onDrag(e: MouseEvent) {
        if (!this.isDragging || !this.dragTarget || !this.container) return;

        // ★拡大中は移動させない
        if (this.dragTarget.classList.contains('expanded')) return;

        e.preventDefault();

        const containerRect = this.container.getBoundingClientRect();
        const x = e.clientX - containerRect.left - this.dragOffsetX;
        const y = e.clientY - containerRect.top - this.dragOffsetY;

        this.dragTarget.style.left = `${x}px`;
        this.dragTarget.style.top = `${y}px`;

        if (this.trashZone) {
            const trashRect = this.trashZone.getBoundingClientRect();
            const bubbleRect = this.dragTarget.getBoundingClientRect();
            const isOver = (
                bubbleRect.left < trashRect.right &&
                bubbleRect.right > trashRect.left &&
                bubbleRect.top < trashRect.bottom &&
                bubbleRect.bottom > trashRect.top
            );
            if (isOver) this.trashZone.classList.add('active');
            else this.trashZone.classList.remove('active');
        }
    }

    private endDrag(e: MouseEvent) {
        if (!this.isDragging || !this.dragTarget) return;

        const movedDist = Math.hypot(
            e.clientX - this.startX,
            e.clientY - this.startY
        );

        const target = this.dragTarget;

        // ゴミ箱処理
        if (this.trashZone && this.trashZone.classList.contains('active')) {
            this.removeBubble(target);
            this.trashZone.classList.remove('active');
        }
        // クリック判定 (移動距離が小さい場合)
        else if (movedDist < 5) {
            this.handleClick(target);
        }
        // ドラッグ終了 (元に戻す)
        else {
            target.classList.remove('dragging');
            if (!target.classList.contains('expanded')) {
                target.style.animation = `gentleFloat ${3 + Math.random()}s infinite ease-in-out`;
            }
        }

        this.isDragging = false;
        this.dragTarget = null;
        if (this.trashZone) this.trashZone.classList.remove('visible');
    }

    private handleClick(bubble: HTMLElement) {
        const isExpanded = bubble.classList.contains('expanded');

        if (!isExpanded) {
            // --- 1回目のクリック: 拡大 ---
            this.collapseAll(); // 他を開いているなら閉じるする

            bubble.classList.add('expanded');
            bubble.innerText = bubble.dataset.fullText || ''; // テキストを表示
            bubble.style.animation = 'none'; // 停止

        } else {
            // --- 2回目のクリック: アクション実行 ---
            const actionId = bubble.dataset.actionId;
            if (!actionId) return;

            // チャットパネルを開く
            if ((window as any).openChatPanel) {
                (window as any).openChatPanel(true);
            }

            // エフェクト & 削除
            bubble.style.transform = "scale(1.5)";
            bubble.style.opacity = "0";

            if ((window as any).pywebview) {
                (window as any).pywebview.api.trigger_bubble_action(actionId).catch(console.error);
            }

            setTimeout(() => {
                if (bubble.parentNode) bubble.parentNode.removeChild(bubble);
                this.activeBubbles = this.activeBubbles.filter(b => b !== bubble);
            }, 300);
        }
    }

    private removeBubble(bubble: HTMLElement) {
        bubble.style.transform = "scale(0)";
        bubble.style.opacity = "0";
        setTimeout(() => {
            if (bubble.parentNode) bubble.parentNode.removeChild(bubble);
            this.activeBubbles = this.activeBubbles.filter(b => b !== bubble);
        }, 300);
        if (bubble.dataset.actionId && (window as any).pywebview) {
            (window as any).pywebview.api.dismiss_bubble(bubble.dataset.actionId).catch(() => { });
        }
    }
}
