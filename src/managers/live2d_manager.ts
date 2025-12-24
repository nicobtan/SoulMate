// src/managers/live2d_manager.ts
import { Live2DModel } from 'pixi-live2d-display';
import { AudioManager } from '../services/audio_manager.js';

// --- Internal Helper: Lip Sync Logic ---
class LipSyncManager {
    audioContext: AudioContext | null = null;
    analyser: AnalyserNode | null = null;
    dataArray: Uint8Array | null = null;
    source: MediaElementAudioSourceNode | null = null;
    isInitialized: boolean = false;

    init(audioElement: HTMLAudioElement) {
        if (this.isInitialized) return;

        // @ts-ignore
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioContext();
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;

        try {
            this.source = this.audioContext.createMediaElementSource(audioElement);
            this.source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
        } catch (e) {
            console.warn("LipSync: MediaElementSource attach failed (already attached?)", e);
        }

        this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.isInitialized = true;

        // Resume on play
        audioElement.addEventListener('play', () => {
            if (this.audioContext && this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
        });
    }

    update(model: any) {
        if (!this.isInitialized || !model || !this.analyser || !this.dataArray) return;

        this.analyser.getByteFrequencyData(this.dataArray as any);

        let values = 0;
        const length = this.dataArray.length;
        for (let i = 0; i < length; i++) {
            values += this.dataArray[i];
        }
        const average = values / length;

        // Sensitivity (0.0 - 1.0)
        let volume = (average / 255) * 5.0;
        if (volume > 1.0) volume = 1.0;
        if (volume < 0.1) volume = 0;

        if (model.internalModel && model.internalModel.coreModel) {
            model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', volume);
        }
    }

    public resume() {
        if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
    }
}

export class Live2DManager {
    private static instance: Live2DManager;
    private app: any; // PIXI.Application
    private model: any; // Live2DModel
    private lipSync: LipSyncManager;
    private characterArea: HTMLElement | null = null;

    // Idle Motion State
    private nextBlinkTime = 0;
    private blinkState = 0;
    private blinkStartTime = 0;
    private readonly BLINK_DURATION = 200;

    private constructor() {
        this.lipSync = new LipSyncManager();
    }

    public static getInstance(): Live2DManager {
        if (!Live2DManager.instance) Live2DManager.instance = new Live2DManager();
        return Live2DManager.instance;
    }

    public async init(containerId: string, modelPath: string) {
        this.characterArea = document.getElementById(containerId);
        if (!this.characterArea) throw new Error(`Container ${containerId} not found`);

        // 1. Initialize PIXI
        if (typeof (window as any).PIXI === 'undefined') throw new Error('PIXI not loaded');

        console.log('Init: Starting PixiJS...');
        this.app = new (window as any).PIXI.Application({
            view: document.createElement('canvas'),
            autoStart: true,
            resizeTo: this.characterArea,
            backgroundAlpha: 0,
        });

        this.characterArea.appendChild(this.app.view);

        await this.loadModel(modelPath);

        // 3. Init LipSync
        const audioManager = AudioManager.getInstance();
        this.lipSync.init(audioManager.audio);

        // 4. Register Ticker (LipSync & Idle)
        this.app.ticker.add(() => {
            if (this.model) {
                this.lipSync.update(this.model);
                this.updateIdleMotion();
            }
        });

        // 5. Setup Resize
        window.addEventListener('resize', () => setTimeout(() => this.resize(), 100));

        // Setup Global Hook for UIManager
        (window as any).resizeModel = this.resize.bind(this);
        (window as any).live2d_model = this.model;

        // Initial Resize
        this.resize();

        // 6. Setup Zoom Control
        window.addEventListener('wheel', (e) => this.handleZoom(e), { passive: false });
    }

    private async loadModel(path: string) {
        // Class check
        let ModelClass = (window as any).Live2DModel;
        if (!ModelClass && (window as any).PIXI.live2d) {
            ModelClass = (window as any).PIXI.live2d.Live2DModel;
        }

        console.log(`Loading Model: ${path}`);
        this.model = await ModelClass.from(path);
        this.app.stage.addChild(this.model);
        console.log("Model Loaded.");

        // Update global reference
        (window as any).live2d_model = this.model;
    }

    public resize() {
        if (!this.model || !this.characterArea || !this.app) return;

        const frameW = this.characterArea.clientWidth;
        const frameH = this.characterArea.clientHeight;
        const isMobile = document.body.classList.contains('mobile-mode');

        // Resize Renderer
        this.app.renderer.resize(frameW, frameH);
        this.app.view.style.width = frameW + "px";
        this.app.view.style.height = frameH + "px";

        // Calculate Scale
        const internalHeight = this.model.internalModel.height;
        const targetScale = (frameH * 2.2) / internalHeight; // 2.2x Zoom

        this.model.scale.set(targetScale);

        // Calculate Position
        // X: Center
        this.model.x = (frameW / 2) - (this.model.width / 2);

        // Y: Position based on mode
        if (isMobile) {
            // Mobile: Move up slightly to fit in top half
            this.model.y = -frameH * 0.1;
        } else {
            // Desktop: Center face
            this.model.y = (frameH * 0.4) - (this.model.height * 0.15);
        }
    }

    public async triggerExpression(expressionId: string) {
        if (!this.model) return;
        console.log(`Triggering Expression: ${expressionId}`);
        try {
            await this.model.expression(expressionId);
        } catch (e) {
            console.warn("Expression failed:", e);
        }
    }

    public ensureAudioContext() {
        this.lipSync.resume();
    }

    public focusReset() {
        if (this.model) this.model.focus(0, 0);
    }

    private currentExpression: string = '';

    public async setRandomExpression() {
        if (!this.model) return;

        // 1. Get List of Expressions
        let expressions: string[] = [];
        const internal = this.model.internalModel;

        if (internal.settings && internal.settings.expressions) {
            // Cubism 4 Internal Model Settings usually has 'expressions' array of {Name, File}
            expressions = internal.settings.expressions.map((e: any) => e.Name);
        }

        // Fallback: Model 0005 known pattern (f01..f16)
        if (expressions.length === 0) {
            for (let i = 1; i <= 16; i++) {
                expressions.push(`f${i.toString().padStart(2, '0')}`);
            }
        }

        if (expressions.length === 0) {
            console.warn("No expressions found.");
            return;
        }

        // 2. Pick Random (Avoid immediate duplicate)
        const valid = expressions.filter(e => e !== this.currentExpression);
        const next = valid.length > 0
            ? valid[Math.floor(Math.random() * valid.length)]
            : expressions[0];

        this.currentExpression = next;

        // 3. Trigger & Log
        await this.triggerExpression(next);

        // Random Reason
        const reasons = [
            "Just felt like it", "Testing my face muscles", "Because you looked at me",
            "Practicing for a selfie", "Whimsical mood", "Did you see that?",
            "Trying to look cute", "System test... successful!", "Feeling a bit different"
        ];
        const reason = reasons[Math.floor(Math.random() * reasons.length)];

        // Log to System (UI)
        const ui = (window as any).uiManager;
        if (ui && ui.logSystem) {
            ui.logSystem(`[System] Expression changed: ${next} (Reason: ${reason})`);
        } else {
            console.log(`[System] Expression changed: ${next} (Reason: ${reason})`);
        }
    }

    private handleZoom(e: WheelEvent) {
        if (!e.ctrlKey || !this.model) return;
        e.preventDefault();

        const sensitivity = 0.0002;
        const scaleAmount = -e.deltaY * sensitivity;

        this.model.scale.x += scaleAmount;
        this.model.scale.y += scaleAmount;
        if (this.model.scale.x < 0.1) this.model.scale.set(0.1);

        // Re-center X
        const frameW = this.characterArea?.clientWidth || 500;
        this.model.x = (frameW / 2) - (this.model.width / 2);
    }

    private updateIdleMotion() {
        if (!this.model || !this.model.internalModel || !this.model.internalModel.coreModel) return;

        const now = Date.now();

        // 1. Breathing
        const t = (now / 1000) * 2;
        const breathValue = (Math.sin(t) + 1) / 2;
        this.model.internalModel.coreModel.setParameterValueById('ParamBreath', breathValue);

        // 2. Blinking
        if (this.blinkState === 0) {
            if (now > this.nextBlinkTime) {
                this.blinkState = 1;
                this.blinkStartTime = now;
            }
        } else {
            const elapsed = now - this.blinkStartTime;
            let eyeValue = 1.0;

            if (elapsed < this.BLINK_DURATION / 2) {
                // Closing
                eyeValue = 1.0 - (elapsed / (this.BLINK_DURATION / 2));
            } else if (elapsed < this.BLINK_DURATION) {
                // Opening
                eyeValue = (elapsed - (this.BLINK_DURATION / 2)) / (this.BLINK_DURATION / 2);
            } else {
                // Done
                this.blinkState = 0;
                eyeValue = 1.0;
                this.nextBlinkTime = now + Math.random() * 3000 + 1000;
            }

            this.model.internalModel.coreModel.setParameterValueById('ParamEyeLOpen', eyeValue);
            this.model.internalModel.coreModel.setParameterValueById('ParamEyeROpen', eyeValue);
        }
    }
}
