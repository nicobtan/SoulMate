
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
        this.audio.addEventListener('ended', () => {
            this.notifyState(false);
            this.playNext();
        });
        this.audio.addEventListener('error', (e) => {
            console.error("Audio Error:", e);
            this.notifyState(false);
            this.playNext(); // Try next
        });
    }

    private queue: string[] = [];
    private isUnlocked: boolean = false;

    public static getInstance(): AudioManager {
        if (!AudioManager.instance) {
            AudioManager.instance = new AudioManager();
        }
        return AudioManager.instance;
    }

    /**
     * Unlock AudioContext for Mobile Browsers (Must be called on user interaction)
     */
    public unlock() {
        if (this.isUnlocked) return;

        // Silent 0.1s wav
        const silentWav = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
        const dummy = new Audio(silentWav);
        dummy.play().then(() => {
            this.isUnlocked = true;
            console.log("[Audio] AudioContext unlocked ✅");
        }).catch(e => {
            // Often fails if not directly inside click handler, but worth trying
            console.warn("[Audio] Unlock failed (will retry):", e);
        });
    }

    public enqueue(urlOrBase64: string) {
        // If Base64 raw data (not data URI), prefix it
        let source = urlOrBase64;
        if (!source.startsWith('http') && !source.startsWith('data:') && !source.startsWith('/') && !source.startsWith('audio/')) {
            // Assume MP3 base64 if just a string
            source = "data:audio/mp3;base64," + source;
        }

        this.queue.push(source);
        if (this.audio.paused) {
            this.playNext();
        }
    }

    private playNext() {
        if (this.queue.length === 0) return;

        const source = this.queue.shift();
        if (!source) return;

        this.play(source);
    }

    public play(url: string) {
        // Stop previous if playing (except if called via queue system which checks paused)
        // But if we call play() directly, we overwrite the current track
        // Logic: play() is low level. enqueue() is high level.

        this.audio.src = url;
        this.audio.playbackRate = this.playbackRates[this.currentRateIndex];

        this.audio.play().catch(e => {
            console.warn("AudioManager play failed (might be auto-play block):", e);
            // If failed, try next in queue?
            this.notifyState(false);
            this.playNext(); // Skip broken one
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
