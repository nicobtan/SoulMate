
export class AudioManager {
    private static instance: AudioManager;
    public audio: HTMLAudioElement;
    private playbackRates: number[] = [1.0, 1.5, 2.0];
    private currentRateIndex: number = 0;

    // Callbacks
    public onPlayStateChange?: (isPlaying: boolean) => void;
    public onSpeedChange?: (speed: number) => void;

    private constructor() {
        this.audio = new Audio();
        this.audio.crossOrigin = "anonymous";

        // Bind Events
        this.audio.addEventListener('play', () => this.notifyState(true));
        this.audio.addEventListener('pause', () => this.notifyState(false));
        this.audio.addEventListener('ended', () => this.notifyState(false));
        this.audio.addEventListener('error', (e) => {
            console.error("Audio Error:", e);
            this.notifyState(false);
        });
    }

    public static getInstance(): AudioManager {
        if (!AudioManager.instance) {
            AudioManager.instance = new AudioManager();
        }
        return AudioManager.instance;
    }

    public play(url: string) {
        // Stop previous if playing
        this.stop();

        this.audio.src = url;
        this.audio.playbackRate = this.playbackRates[this.currentRateIndex];

        this.audio.play().catch(e => {
            console.warn("AudioManager play failed (might be auto-play block):", e);
            this.notifyState(false);
        });
    }

    public stop() {
        this.audio.pause();
        this.audio.currentTime = 0;
        this.notifyState(false);
    }

    public toggleSpeed() {
        this.currentRateIndex = (this.currentRateIndex + 1) % this.playbackRates.length;
        const newRate = this.playbackRates[this.currentRateIndex];
        this.audio.playbackRate = newRate;

        if (this.onSpeedChange) {
            this.onSpeedChange(newRate);
        }
    }

    public getCurrentSpeed(): number {
        return this.playbackRates[this.currentRateIndex];
    }

    private notifyState(isPlaying: boolean) {
        if (this.onPlayStateChange) {
            this.onPlayStateChange(isPlaying);
        }
    }
}
