import { api } from './api_client.js';

class SoulBubble {
    public element: HTMLElement;
    private content: HTMLElement;
    private actionId: string;
    private container: HTMLElement;
    private isExpanded: boolean = false;
    private manager: SoulBubbleManager;
    public slotIndex: number;

    constructor(manager: SoulBubbleManager, container: HTMLElement, category: string, text: string, actionId: string, slotIndex: number, type: string = 'normal') {
        this.manager = manager;
        this.container = container;
        this.actionId = actionId;
        this.slotIndex = slotIndex;

        // Create Element
        this.element = document.createElement('div');

        // Color Mapping
        const colorMap: { [key: string]: string } = {
            'topics': 'blue',
            'play': 'green',
            'bond': 'pink',
            'utility': 'orange'
        };
        const color = colorMap[category] || 'blue';
        this.element.className = `soul-bubble bubble-${color}`;

        // Discovery Mode
        if (type === 'discovery') {
            this.element.classList.add('bubble-discovery');
        }

        // Icon Mapping
        const iconMap: { [key: string]: string } = {
            'topics': '💡',
            'play': '🎮',
            'bond': '💖',
            'utility': '⚠️'
        };
        // Explicitly handle discovery icon
        let iconChar = iconMap[category] || '💬';
        if (type === 'discovery') {
            iconChar = '✨';
        }

        // Content Structure
        this.element.innerHTML = `
            <div class="bubble-content">
                <span class="icon">${iconChar}</span>
                <span class="text">${text}</span>
            </div>
        `;
        this.content = this.element.querySelector('.bubble-content') as HTMLElement;

        // Drag Logic Initialization
        this.initDrag();

        // Position Logic (Slot-based)
        const slot = SoulBubbleManager.SLOTS[slotIndex] || SoulBubbleManager.SLOTS[0];

        // Add slight randomness to make it organic, but keep within slot
        const randX = (Math.random() - 0.5) * 4; // +/- 2%
        const randY = (Math.random() - 0.5) * 4; // +/- 2%

        this.element.style.top = `${slot.top + randY}%`;
        this.element.style.left = `${slot.left + randX}%`;

        // Add random float delay/duration
        const floatDuration = 4 + Math.random() * 2; // 4-6s (Slower)
        const floatDelay = Math.random() * 3;

        // Event Listeners (Handled by initDrag now)
        // Check handled by initDrag() which distinguishes click vs drag

        // Append to DOM
        this.container.appendChild(this.element);

        // Start Animation (Pop In -> Float)
        requestAnimationFrame(() => {
            this.element.classList.add('appeared');

            // Start floating after pop-in finishes
            setTimeout(() => {
                this.element.classList.add('floating');
                this.element.style.animation = `gentleFloat ${floatDuration}s infinite ease-in-out -${floatDelay}s`;
            }, 550);
        });
    }

    private handleClick() {
        if (this.isExpanded) {
            // Second Click: Execute Action
            this.triggerAction();
        } else {
            // First Click: Expand
            this.expand();
        }
    }

    public expand() {
        this.manager.collapseAll(this);
        this.isExpanded = true;
        this.element.classList.add('expanded');
        this.element.style.zIndex = "1005";

        // Store original left for restoration
        this.element.dataset.originalLeft = this.element.style.left;

        // Move to fixed reading position (30% from left) as requested
        this.element.style.left = '30%';
    }

    public collapse() {
        if (!this.isExpanded) return;
        this.isExpanded = false;
        this.element.classList.remove('expanded');
        this.element.style.zIndex = "";

        // Revert Position
        if (this.element.dataset.originalLeft) {
            this.element.style.left = this.element.dataset.originalLeft;
            delete this.element.dataset.originalLeft;
        }
    }

    private async triggerAction() {
        console.log("Soul Bubble Action: " + this.actionId);

        this.element.style.transform = "scale(0)";
        this.element.style.opacity = "0";

        setTimeout(() => {
            this.destroy();
        }, 300);

        try {
            // Auto-open chat panel
            // @ts-ignore
            if (typeof window.openChatPanel === 'function') window.openChatPanel(true);

            await api.trigger_bubble_action(this.actionId);
        } catch (e) {
            console.error("Failed to trigger bubble action:", e);
        }
    }

    public async dismiss() {
        // Animate out
        this.element.style.transform = "scale(0)";
        this.element.style.opacity = "0";

        setTimeout(() => {
            this.destroy();
        }, 300);

        try {
            console.log("Dismissing bubble:", this.actionId);
            const res = await api.dismiss_bubble(this.actionId);
            if (res && res.status === 'success' && res.refilled && res.bubble) {
                // Auto-Refill triggered
                const b = res.bubble;
                // Add new bubble (delay slightly)
                setTimeout(() => {
                    this.manager.addBubble(b.category, b.text, b.actionId, b.type || 'normal');
                }, 500);
            }
        } catch (e) {
            console.error("Dismiss failed:", e);
        }
    }

    private isDragging: boolean = false;
    private wasDragged: boolean = false; // Flag to filter click events after dragging
    private startX: number = 0;
    private startY: number = 0;
    private initialLeft: number = 0;
    private initialTop: number = 0;

    private initDrag() {
        this.element.addEventListener('mousedown', (e) => this.onMouseDown(e));

        // Re-add click listener to handle selection distinct from drag
        this.element.addEventListener('click', (e) => {
            e.stopPropagation(); // Always stop propagation to prevent document click (collapseAll)

            if (this.wasDragged) {
                // If this click was part of a drag release, ignore it
                this.wasDragged = false;
                return;
            }
            this.handleClick();
        });
    }

    private onMouseDown(e: MouseEvent) {
        if (e.button !== 0) return; // Only left click
        // e.stopPropagation(); // Let mousedown bubble if needed, but click must be stopped. 
        // Actually, stopping mousedown is usually fine for UI components.
        e.stopPropagation();

        this.isDragging = false;
        this.wasDragged = false;
        this.startX = e.clientX;
        this.startY = e.clientY;

        // Get current computed position
        const rect = this.element.getBoundingClientRect();
        this.initialLeft = rect.left;
        this.initialTop = rect.top;

        const onMouseMove = (moveEvent: MouseEvent) => {
            const dx = moveEvent.clientX - this.startX;
            const dy = moveEvent.clientY - this.startY;

            // Threshold to start dragging
            if (!this.isDragging && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
                this.isDragging = true;
                this.element.classList.add('dragging');

                // Show Trash Zone
                const trash = document.getElementById('trash-zone');
                if (trash) {
                    trash.classList.add('visible');
                    trash.style.opacity = '0.6';
                    trash.style.pointerEvents = 'all';
                }
            }

            if (this.isDragging) {
                // Move element directly
                this.element.style.position = 'fixed';
                this.element.style.left = `${this.initialLeft + dx}px`;
                this.element.style.top = `${this.initialTop + dy}px`;
                this.element.style.transform = 'scale(1.1)';

                // Trash collision
                this.checkTrashCollision(moveEvent.clientX, moveEvent.clientY);
            }
        };

        const onMouseUp = (upEvent: MouseEvent) => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);

            const trash = document.getElementById('trash-zone');

            if (this.isDragging) {
                this.wasDragged = true; // Mark as dragged to suppress click

                // Drop Logic
                if (trash && trash.classList.contains('active')) {
                    // Dropped in trash
                    this.dismiss();
                } else {
                    // Spring back
                    this.element.style.transition = 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                    this.resetPosition();
                }

                this.element.classList.remove('dragging');
                this.element.style.transform = ''; // Clear scale

                // Hide Trash
                if (trash) {
                    trash.classList.remove('visible', 'active');
                    trash.style.opacity = '0';
                    trash.style.pointerEvents = 'none';
                }
            } else {
                // Was not a drag (just a click-like down/up). 
                // We do NOT call handleClick here. 
                // We let the native 'click' event fire, which will be caught by our listener.
            }
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    private resetPosition() {
        // Revert to percentage based position from slot
        const slot = SoulBubbleManager.SLOTS[this.slotIndex];
        // We need to clear fixed positioning and return to absolute/container relative?
        // Actually our slot logic sets style.top/left in %.
        // When we set style.position='fixed' we overrode that.
        // We should revert to absolute and clear explicit pixel values? 
        // Or re-apply slot values.

        this.element.style.position = 'absolute';

        // Slightly re-randomize to avoid stiffness or use stored?
        // Let's use stored if possible but re-calc is fine.
        const randX = (Math.random() - 0.5) * 4;
        const randY = (Math.random() - 0.5) * 4;

        this.element.style.left = `${slot.left + randX}%`;
        this.element.style.top = `${slot.top + randY}%`;

        // Clear transition after animation
        setTimeout(() => {
            this.element.style.transition = '';
        }, 300);
    }

    private checkTrashCollision(x: number, y: number) {
        const trash = document.getElementById('trash-zone');
        if (!trash) return;

        const rect = trash.getBoundingClientRect();
        // Check if mouse is inside trash rect
        if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
            trash.classList.add('active');
        } else {
            trash.classList.remove('active');
        }
    }

    public destroy() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        this.manager.remove(this);
    }
}

export class SoulBubbleManager {
    private container: HTMLElement | null;
    private bubbles: SoulBubble[] = [];

    // Slot Definitions (Arch Layout)
    // Slot Definitions (Arch Layout) - Raised positions
    public static readonly SLOTS = [
        { left: 50, top: 5 },  // 0: Center Top (was 15)
        { left: 35, top: 15 }, // 1: Left Mid (was 25)
        { left: 65, top: 15 }, // 2: Right Mid (was 25)
        { left: 20, top: 30 }, // 3: Far Left Low (was 40)
        { left: 80, top: 30 }  // 4: Far Right Low (was 40)
    ];
    private occupiedSlots: boolean[];

    constructor() {
        this.container = document.getElementById('soul-bubble-container');
        this.occupiedSlots = new Array(SoulBubbleManager.SLOTS.length).fill(false);

        // Global Click Listener to Collapse All
        document.addEventListener('click', () => {
            this.collapseAll();
        });
    }

    public addBubble(category: string, text: string, actionId: string, type: string = 'normal') {
        if (!this.container) return;

        // Find Allocatable Slot
        let slotIdx = this.occupiedSlots.findIndex(occupied => !occupied);

        if (slotIdx === -1) {
            // No free slots. Remove oldest bubble to free space
            if (this.bubbles.length > 0) {
                const old = this.bubbles.shift();
                if (old) {
                    old.destroy();
                    // Re-check slots
                    slotIdx = this.occupiedSlots.findIndex(occupied => !occupied);
                }
            }
        }

        if (slotIdx === -1) {
            console.warn("No slots available for Soul Bubble");
            return;
        }

        // Occupy
        this.occupiedSlots[slotIdx] = true;

        const bubble = new SoulBubble(this, this.container, category, text, actionId, slotIdx, type);
        this.bubbles.push(bubble);
    }

    public collapseAll(exclude?: SoulBubble) {
        this.bubbles.forEach(b => {
            if (b !== exclude) b.collapse();
        });
    }

    public remove(bubble: SoulBubble) {
        // Free Slot
        if (bubble.slotIndex >= 0 && bubble.slotIndex < this.occupiedSlots.length) {
            this.occupiedSlots[bubble.slotIndex] = false;
        }

        const idx = this.bubbles.indexOf(bubble);
        if (idx > -1) {
            this.bubbles.splice(idx, 1);
        }
    }
}
