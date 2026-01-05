// src/managers/live2d_manager.ts
import { LogManager } from './log_manager.js';
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
        // ★変更: window.resize ではなく ResizeObserver を使う
        // これにより、要素のサイズが実際に変わった時だけ反応する
        if (this.characterArea) {
            const resizeObserver = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    if (entry.target === this.characterArea) {
                        // 描画タイミングに合わせて実行
                        requestAnimationFrame(() => this.resize());
                    }
                }
            });
            resizeObserver.observe(this.characterArea);
            console.log("[Live2D] ResizeObserver attached.");
        }

        // Setup Global Hook for UIManager
        (window as any).resizeModel = this.resize.bind(this);
        (window as any).live2d_model = this.model;

        // ★ Explicitly expose manager as requested by user
        (window as any).live2d_manager = this;

        // Initial Resize
        this.resize();

        // 6. Setup Zoom Control
        window.addEventListener('wheel', (e) => this.handleZoom(e), { passive: false });
    }

    /**
     * Default initialization for backward compatibility or simple usage.
     * Uses default container 'character-area' and default model.
     */
    public async initialize() {
        const defaultContainer = 'character-area';
        // Use the model found in the directory
        const defaultModel = 'models/fav_usaneko_alwb/fav_usaneko_alwb.model3.json';

        console.log(`Live2DManager: Auto-initializing with default model: ${defaultModel}`);
        return this.init(defaultContainer, defaultModel);
    }

    private async loadModel(path: string) {
        // Class check
        let ModelClass = (window as any).Live2DModel;
        if (!ModelClass && (window as any).PIXI.live2d) {
            ModelClass = (window as any).PIXI.live2d.Live2DModel;
        }

        console.log(`Loading Model: ${path} `);
        this.model = await ModelClass.from(path);
        this.app.stage.addChild(this.model);
        console.log("Model Loaded.");

        // Update global reference
        (window as any).live2d_model = this.model;
    }

    public resize() {
        if (!this.model || !this.characterArea || !this.app) return;

        const frameW = this.characterArea.clientWidth;
        // const frameH = this.characterArea.clientHeight; 
        // ★ Fix: Use window.innerHeight to ensure full screen height coverage (avoid black bars)
        const frameH = window.innerHeight;
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

    // ▼ AIの感情タグ(Key) と Live2Dの表情名(Value) の対応表
    private static readonly EMOTION_MAP: { [key: string]: string | string[] } = {
        // 喜び・ポジティブ系 (配列で複数を指定！)
        "happy": ["18.smile", "08.XD", "11.perori"],
        "joy": ["18.smile", "08.XD", "12.cat_mouth", "13.surprised"],
        "excited": ["18.smile", "08.XD", "12.cat_mouth", "13.surprised"],
        "fun": ["08.XD", "11.perori", "12.cat_mouth"],

        // 愛情・デレ系 (ここが重要！)
        "loving": "01.blush",     // 照れる
        "love": "01.blush",
        "shy": "01.blush",

        // 悲しみ・ネガティブ系
        "sad": "03.cry",
        "sorrow": "03.cry",
        "cry": "03.cry",

        // 怒り
        "angry": ["02.angry", "15.angry2"], // 怒りも2種類
        "anger": "02.angry",

        // 驚き
        "surprised": "13.surprised",
        "shock": "04.pale",       // 驚愕で青ざめる演出

        // その他・特殊
        "fear": "04.pale",        // 恐怖
        "sleepy": "17.sleep",     // 眠い
        "tired": "17.sleep",
        "disgust": "10.jitome",   // 軽蔑/ジト目
        "doubt": "10.jitome",

        // デフォルト
        "neutral": "",            // 表情リセット
        "default": ""
    };

    /**
     * 感情タグからLive2Dの表情IDを取得する（ランダム対応版）
     */
    private static getExpressionId(emotionTag: string, currentId: string | null = null): string {
        // 小文字化してキー検索
        const key = (emotionTag || "neutral").toLowerCase().trim();

        // マップから値を取得 (なければデフォルトキー、それでもなければ空文字)
        const value = this.EMOTION_MAP[key] || this.EMOTION_MAP["neutral"] || "";

        // ★ここがポイント: 配列ならランダム抽選
        if (Array.isArray(value)) {
            // 現在の表情を除外した候補リストを作成
            const candidates = currentId ? value.filter(v => v !== currentId) : value;

            // 候補がなくなってしまったら（選択肢が1つしかない場合など）、元のリストを使う
            const listToUse = candidates.length > 0 ? candidates : value;

            const randomIndex = Math.floor(Math.random() * listToUse.length);
            return listToUse[randomIndex];
        }

        return value;
    }

    /**
     * ランダムな表情をセットする (ボタン用)
     */
    public setRandomExpression() {
        const keys = Object.keys(Live2DManager.EMOTION_MAP).filter(k => k !== 'neutral' && k !== 'default');
        if (keys.length === 0) return;

        const randomKey = keys[Math.floor(Math.random() * keys.length)];
        this.triggerExpression(randomKey);
    }

    public async triggerExpression(aiEmotionTag: string) {
        if (!this.model) return;

        // 1. IDの取得 (neutralなら空文字 "" が返る)
        const expressionId = Live2DManager.getExpressionId(aiEmotionTag, this.currentExpression);
        const logger = LogManager.getInstance();

        try {
            if (expressionId) {
                // --- 表情セット (通常) ---
                logger.log(`Expression: ${aiEmotionTag} (${expressionId})`, 'info', 'sys');
                await this.model.expression(expressionId);
            } else {
                // --- 表情リセット (Default) ---
                logger.log(`Expression: Reset(${aiEmotionTag})`, 'info', 'sys');

                // 試行策1: 公式の高レベルAPIで空っぽをセットする
                // (undefinedを渡すとリセットされる仕様の実装が多いです)
                await this.model.expression(undefined);

                // 試行策2: 内部マネージャーを直接叩いて強制解除 (Cubism 4系)
                if (this.model.internalModel && this.model.internalModel.motionManager && this.model.internalModel.motionManager.expressionManager) {
                    this.model.internalModel.motionManager.expressionManager.setExpression(null);
                }

                // 試行策3: それでもダメな場合のパラメータ強制リセット (頬染め対策)
                // "ParamCheek" は一般的な赤面のIDですが、モデルによって違うので安全策として
                if (this.model.internalModel && this.model.internalModel.coreModel) {
                    // 一般的な頬染めパラメータを0にする (もし存在すれば)
                    try {
                        this.model.internalModel.coreModel.setParameterValueById('ParamCheek', 0);
                        this.model.internalModel.coreModel.setParameterValueById('ParamBlush', 0);
                    } catch (e) { /* 無視 */ }
                }
            }

            this.currentExpression = expressionId;

        } catch (e) {
            console.warn(`[Expression] Failed to set expression: ${expressionId} `, e);
            logger.log(`Expression Error: ${e} `, 'error', 'sys');
        }
    }


    public ensureAudioContext() {
        this.lipSync.resume();
    }

    public focusReset() {
        if (this.model) this.model.focus(0, 0);
    }

    private currentExpression: string = '';



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
