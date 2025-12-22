import { ChatManager } from './managers/chat_manager.js';

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

    // URL Linkifier Helper
    private linkify(text: string): string {
        const urlPattern = /(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig;
        return text.replace(urlPattern, '<a href="$1" target="_blank" style="color: cyan; text-decoration: underline;">$1</a>');
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

        // ★修正: Manual/Debug生成の場合、キャラの頭上(Y < 100)に制限
        let randomY = 60 + Math.random() * 100;
        if (type === 'manual' || type === 'debug') {
            randomY = 30 + Math.random() * 50; // 30px ~ 80px (Head area)
        }

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
            // ★修正: URLリンク化 (innerHTMLを使用)
            const rawText = bubble.dataset.fullText || '';
            bubble.innerHTML = this.linkify(rawText);

            bubble.style.animation = 'none'; // 停止

        } else {
            // --- 2回目のクリック: アクション実行 ---
            // リンククリックの場合はここに来ないようにしたいが、
            // バブリングで来る可能性がある。
            // しかし、<a>タグをクリックした場合、ブラウザが別ウィンドウを開く動作をするはず。
            // ここではバブリングストップ等はしていないが、target="_blank"なら問題ないことが多い。
            // もしクリックで閉じてしまうなら e.target.tagName チェックが必要。
            // (handleClickはClickハンドラではなく、endDragから呼ばれるカスタムメソッドなのでEventオブジェクトがない)
            // 実装上、リンククリック = mousedown -> mouseup -> click イベント
            // ここでは endDrag -> handleClick なので、ドラッグ判定による擬似クリック。
            // <a>タグの上でマウスダウン->アップした場合もここに来る。

            // 簡易対策: リンククリック時はバブルを閉じないように変更するのは難しい（eventがないため）。
            // ただし、ユーザーは「リンクを開いた後、バブルが消えてもいい」場合が多い。
            // あるいは「リンクを開く」動作と「バブルのアクション」が競合する。

            // Log for User Visibility (Action Triggered)
            const rawText = bubble.dataset.fullText || '';
            ChatManager.getInstance().logUserAction(rawText);

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
