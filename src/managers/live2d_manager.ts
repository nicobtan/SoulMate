// src/managers/live2d_manager.ts
import { LogManager } from './log_manager.js';
import { Live2DModel } from 'pixi-live2d-display';
import { AudioManager } from '../services/voice/audio_manager.js';

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

    private currentVolume = 0; // 現在の音量を保持

    update(model: any) {
        if (!this.isInitialized || !model || !this.analyser || !this.dataArray) return;

        this.analyser.getByteFrequencyData(this.dataArray as any);

        // 人の声に近い周波数帯(低〜中音域)に絞って平均を取る
        let values = 0;
        const start = Math.floor(this.dataArray.length * 0.05); // 低音
        const end = Math.floor(this.dataArray.length * 0.4);   // 中音
        for (let i = start; i < end; i++) {
            values += this.dataArray[i];
        }
        const average = values / (end - start);

        // 感度調整とゲイン
        let targetVolume = (average / 255) * 6.5; 
        if (targetVolume > 1.0) targetVolume = 1.0;
        if (targetVolume < 0.05) targetVolume = 0;

        // Lerp(線形補間)で滑らかに開閉させる (0.35 = 追従速度)
        this.currentVolume += (targetVolume - this.currentVolume) * 0.35;

        // 音量が小さくなった後、一定時間で表情をリセットする処理などをここに追加することも可能

        if (model.internalModel && model.internalModel.coreModel) {
            model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', this.currentVolume);
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

    public async init(containerId: string, modelIdOrPath: string, config?: { scale?: number, x?: number, y?: number }) {
        this.characterArea = document.getElementById(containerId);
        if (!this.characterArea) throw new Error(`Container ${containerId} not found`);

        // Apply Config
        this.customScale = config?.scale ?? 1.0;
        this.customOffsetX = config?.x ?? 0;
        this.customOffsetY = config?.y ?? 0;

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

        // Path Resolution
        let finalPath = modelIdOrPath;
        if (!modelIdOrPath.endsWith('.json')) {
            finalPath = `models/${modelIdOrPath}/${modelIdOrPath}.model3.json`;
            console.log(`[Init] Resolved Model ID '${modelIdOrPath}' to path: ${finalPath}`);
        }

        // Retry logic is inside loadModel now, but we await it here
        await this.loadModel(finalPath);

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
        // Also expose as camelCase for compatibility with Python API calls
        (window as any).live2dManager = this;

        // Initial Resize is handled by ResizeObserver callback, BUT we must ensure it runs after model load
        // because ResizeObserver might fire too early (while model is null).
        this.resize();

        // 6. Setup Zoom Control
        window.addEventListener('wheel', (e) => this.handleZoom(e), { passive: false });
    }

    /**
     * Default initialization for backward compatibility or simple usage.
     * Uses default container 'character-area' and default model.
     */
    // Helper for remote logging
    private remoteLog(msg: string) {
        console.log(msg);
        if ((window as any).pywebview && (window as any).pywebview.api && (window as any).pywebview.api.log_to_debug) {
            (window as any).pywebview.api.log_to_debug(msg, 'sys');
        }
    }

    public async initialize() {
        const defaultContainer = 'character-area';
        // Use the model found in the directory
        const defaultModel = 'models/fav_usaneko_alwb/fav_usaneko_alwb.model3.json';

        console.log(`Live2DManager: Auto-initializing with default model: ${defaultModel}`);
        return this.init(defaultContainer, defaultModel);
    }

    private async loadModel(path: string, retryCount = 0): Promise<void> {
        // Class check
        let ModelClass = (window as any).Live2DModel;
        if (!ModelClass && (window as any).PIXI.live2d) {
            ModelClass = (window as any).PIXI.live2d.Live2DModel;
        }

        console.log(`Loading Model (Attempt ${retryCount + 1}): ${path} `);

        try {
            // Optional: Timeout implementation could go here, but Pixi loader usually handles it.
            // We'll rely on try/catch first.
            this.model = await ModelClass.from(path);
            this.app.stage.addChild(this.model);
            console.log(`Model Loaded successfully on attempt ${retryCount + 1}.`);

            // Update global reference
            (window as any).live2d_model = this.model;

        } catch (e) {
            console.error(`[Live2D] Load failed (Attempt ${retryCount + 1}):`, e);

            if (retryCount < 3) {
                const delay = 1000 * (retryCount + 1); // 1s, 2s, 3s wait
                console.log(`[Live2D] Retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.loadModel(path, retryCount + 1);
            } else {
                console.error("[Live2D] All retry attempts failed. Model could not be loaded.");
                this.remoteLog(`❌ Live2D Load Failed: ${path}`);
                // Don't throw here to prevent full app crash? Or throw to notify caller?
                // Let's not throw, just log. Caller 'switchModel' might want to know though.
                throw e;
            }
        }
    }

    // Custom Positioning (Offsets)
    private customScale: number = 1.0;
    private customOffsetX: number = 0;
    private customOffsetY: number = 0;

    public async switchModel(modelIdOrPath: string, config?: { scale?: number, x?: number, y?: number }) {
        this.customScale = config?.scale ?? 1.0;
        this.customOffsetX = config?.x ?? 0;
        this.customOffsetY = config?.y ?? 0;

        // Cleanup old model
        if (this.model) {
            this.app.stage.removeChild(this.model);
            this.model.destroy();
            this.model = null;
        }

        // Logic: Try to construct path if it looks like an ID (no extension)
        let finalPath = modelIdOrPath;
        if (!modelIdOrPath.endsWith('.json')) {
            // Assume it's a model ID and construct path
            // Pattern: models/{id}/{id}.model3.json
            finalPath = `models/${modelIdOrPath}/${modelIdOrPath}.model3.json`;
            console.log(`[Live2D] Resolved Model ID '${modelIdOrPath}' to path: ${finalPath}`);
        }

        try {
            await this.loadModel(finalPath);
        } catch (e) {
            console.error(`[Live2D] Failed to load path: ${finalPath}, trying fallback logic...`, e);
            // Fallback: If ID mismatch, maybe try specific known mappings or revert to default
            // For now, let it fail but log clearly.
        }

        this.resize(); // Apply new settings
    }

    public resize() {
        if (!this.model || !this.characterArea || !this.app) return;

        const frameW = this.characterArea.clientWidth;
        // const frameH = this.characterArea.clientHeight; 
        // ★ Fix: Use window.innerHeight to ensure full screen height coverage (avoid black bars)
        const frameH = window.innerHeight;

        // ★ Safety Check: If size is 0 (hidden or not ready), wait and retry
        if (frameW === 0 || frameH === 0) {
            console.warn("[Live2D] Frame size is 0, deferring resize...");
            setTimeout(() => this.resize(), 500);
            return;
        }

        const isMobile = document.body.classList.contains('mobile-mode');

        // Resize Renderer
        this.app.renderer.resize(frameW, frameH);
        this.app.view.style.width = frameW + "px";
        this.app.view.style.height = frameH + "px";

        // Calculate Scale (Base: 2.2x Zoom)
        const internalHeight = this.model.internalModel.height;
        const internalWidth = this.model.internalModel.width;

        // Log model dimensions
        console.log(`[Live2D] Model Size: ${internalWidth}x${internalHeight}`);

        const baseScale = (frameH * 2.2) / internalHeight;

        // Apply Custom Scale Multiplier
        const finalScale = baseScale * this.customScale;

        this.model.scale.set(finalScale);

        // Calculate Position
        // X: Center + Offset
        const centerX = (frameW / 2) - (this.model.width / 2);
        this.model.x = centerX + this.customOffsetX;

        // Y: Position based on mode + Offset
        let baseY = 0;
        if (isMobile) {
            // Mobile: Move up slightly to fit in top half
            baseY = -frameH * 0.1;
        } else {
            // Desktop: Center face
            baseY = (frameH * 0.4) - (this.model.height * 0.15);
        }

        this.model.y = baseY + this.customOffsetY;

        this.remoteLog(`[Live2D] Resized Details: 
            Frame: ${frameW}x${frameH}
            ModelInternal: ${internalWidth}x${internalHeight}
            BaseScale: ${baseScale.toFixed(4)}
            CustomScale: ${this.customScale}
            FinalScale: ${finalScale.toFixed(4)}
            Pos: (${this.model.x.toFixed(1)}, ${this.model.y.toFixed(1)})`);
    }

    // ▼ AIの感情タグ(Key) と Live2Dの表情名(Value) の対応表
    private static readonly EMOTION_MAP: { [key: string]: string | string[] } = {
        // 喜び・ポジティブ系
        "happy": ["18.smile", "08.XD", "11.perori", "expression1", "expression2"],
        "joy": ["18.smile", "08.XD", "12.cat_mouth", "13.surprised", "expression1", "expression2"],
        "excited": ["18.smile", "08.XD", "12.cat_mouth", "13.surprised", "expression4"],
        "fun": ["08.XD", "11.perori", "12.cat_mouth", "expression4"],

        // 愛情・デレ系
        "loving": ["01.blush", "expression5"],
        "love": ["01.blush", "expression5"],
        "shy": ["01.blush", "expression5"],

        // 悲しみ・ネガティブ系
        "sad": ["03.cry", "expression6"],
        "sorrow": ["03.cry", "expression6"],
        "cry": ["03.cry", "expression6"],

        // 怒り
        "angry": ["02.angry", "15.angry2", "expression3"],
        "anger": ["02.angry", "expression3"],

        // 驚き・＞＜など
        "surprised": ["13.surprised", "expression8"],
        "shock": ["04.pale", "expression8"], // ＞＜ の代替
        "fear": ["04.pale", "expression8"],
        "error": ["04.pale", "expression8", "03.cry"], // エラー時専用タグ

        // その他・特殊
        "sleepy": ["17.sleep", "expression7"],
        "tired": ["17.sleep", "expression7"],
        "disgust": ["10.jitome", "expression3"],
        "doubt": ["10.jitome", "expression3"],

        // デフォルト
        "neutral": "",            
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
        if (!this.model) return;

        let availableExpressions: string[] = [];

        // 1. モデル内部に定義されている表情リストを動的に取得する (PixiLive2DDisplay)
        if (this.model.internalModel && this.model.internalModel.settings && this.model.internalModel.settings.expressions) {
            availableExpressions = this.model.internalModel.settings.expressions.map((e: any) => e.name || e.Name);
        }

        // 2. 内部リストが見つからなければ、ハードコードされたマップから候補を生成
        if (availableExpressions.length === 0) {
            const keys = Object.keys(Live2DManager.EMOTION_MAP).filter(k => k !== 'neutral' && k !== 'default');
            keys.forEach(k => {
                const val = Live2DManager.EMOTION_MAP[k];
                if (Array.isArray(val)) {
                    availableExpressions.push(...val);
                } else if (val) {
                    availableExpressions.push(val);
                }
            });
            // 重複を削除
            availableExpressions = Array.from(new Set(availableExpressions));
        }

        if (availableExpressions.length === 0) return;

        // ランダムに選んで適用
        const randomExpId = availableExpressions[Math.floor(Math.random() * availableExpressions.length)];
        
        const logger = LogManager.getInstance();
        logger.log(`Expression: Random Button (${randomExpId})`, 'info', 'sys');

        this.model.expression(randomExpId).catch((e: any) => {
            console.warn(`[Expression] Failed to set random expression: ${randomExpId}`, e);
        });

        this.currentExpression = randomExpId;
    }

    public async triggerExpression(aiEmotionTag: string) {
        if (!this.model) return;

        const key = (aiEmotionTag || "neutral").toLowerCase().trim();
        const mappedValue = Live2DManager.EMOTION_MAP[key] || Live2DManager.EMOTION_MAP["neutral"] || "";

        if (!mappedValue) {
            this.focusReset(); // default/neutralの時はリセット
            return;
        }

        // --- モデルが持っている表情リストを取得 ---
        let availableExpressions: string[] = [];
        if (this.model.internalModel && this.model.internalModel.settings && this.model.internalModel.settings.expressions) {
            availableExpressions = this.model.internalModel.settings.expressions.map((e: any) => e.name || e.Name);
        }

        let candidates: string[] = [];
        if (Array.isArray(mappedValue)) {
            candidates = mappedValue;
        } else {
            candidates = [mappedValue];
        }

        // 利用可能な表情のみにフィルタリング
        if (availableExpressions.length > 0) {
            const validCandidates = candidates.filter(c => availableExpressions.includes(c));
            if (validCandidates.length > 0) {
                candidates = validCandidates;
            } else {
                console.warn(`[Expression] Model does not have any of mapped expressions for '${key}': ${candidates}`);
                return;
            }
        }

        // 現在の表情を除外した候補リストを作成（ランダム変化用）
        const filteredByCurrent = this.currentExpression ? candidates.filter(v => v !== this.currentExpression) : candidates;
        const listToUse = filteredByCurrent.length > 0 ? filteredByCurrent : candidates;

        const expressionId = listToUse[Math.floor(Math.random() * listToUse.length)];
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
        const core = this.model.internalModel.coreModel;

        // 1. Breathing
        const breathT = (now / 1000) * 1.5; // 少しゆっくりめの呼吸
        const breathValue = (Math.sin(breathT) + 1) / 2;
        core.setParameterValueById('ParamBreath', breathValue);

        // 2. 微細な体の揺れ (予測しづらい動き)
        const idleT = now / 2000;
        const angleX = Math.sin(idleT * 0.7) * 2 + Math.cos(idleT * 0.3) * 1;
        const angleY = Math.cos(idleT * 0.8) * 1.5;
        const bodyAngleX = Math.sin(idleT * 0.5) * 1.2;

        core.setParameterValueById('ParamAngleX', angleX); // 首の左右
        core.setParameterValueById('ParamAngleY', angleY); // 首の上下
        core.setParameterValueById('ParamBodyAngleX', bodyAngleX); // 体の揺れ

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
