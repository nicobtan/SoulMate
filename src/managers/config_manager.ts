// src/managers/config_manager.ts
import { api } from '../api_client.js';

export class ConfigManager {
    private static instance: ConfigManager;

    private constructor() { }

    public static getInstance(): ConfigManager {
        if (!ConfigManager.instance) ConfigManager.instance = new ConfigManager();
        return ConfigManager.instance;
    }

    public async init() {
        // Desktop environment usually needs a moment or specific event, 
        // but we can try loading immediately or wait for pywebviewready in index.ts
        await this.loadSettings();
        this.initSaveListeners();
    }

    public async loadSettings() {
        try {
            const settings = await api.get_settings();
            if (!settings) return;

            // 1. Opacity
            const bgRange = document.getElementById('bg-opacity-range') as HTMLInputElement;
            if (bgRange) {
                bgRange.value = String(settings.background_opacity || 0);
                this.updateBackgroundOpacity(settings.background_opacity || 0);
            } else {
                this.updateBackgroundOpacity(settings.background_opacity || 0);
            }

            // 2. Font Size
            if (settings.font_size) {
                const fRange = document.getElementById('font-size-range') as HTMLInputElement;
                const fValue = document.getElementById('font-size-value');
                if (fRange) fRange.value = String(settings.font_size);
                if (fValue) fValue.innerText = settings.font_size + 'px';
                document.documentElement.style.setProperty('--chat-font-size', settings.font_size + 'px');
            }

            // 3. API Key & Model
            const apiKeyInput = document.getElementById('api-key-input') as HTMLInputElement;
            const modelSelect = document.getElementById('model-select') as HTMLSelectElement;
            if (apiKeyInput) apiKeyInput.value = settings.api_key || '';
            if (modelSelect && settings.model_name) modelSelect.value = settings.model_name;

            // 4. Persona
            const personaSelect = document.getElementById('persona-select') as HTMLSelectElement;
            if (personaSelect) {
                const personas = await api.getPersonas();
                personaSelect.innerHTML = "";
                personas.forEach((pId: string) => {
                    const opt = document.createElement('option');
                    opt.value = pId;
                    opt.innerText = pId;
                    personaSelect.appendChild(opt);
                });
                personaSelect.value = settings.current_persona_id || 'default';
                personaSelect.value = settings.current_persona_id || 'default';
            }

            // 5. Chat Length Mode
            const lengthSelect = document.getElementById('chat-length-select') as HTMLSelectElement;
            if (lengthSelect) {
                lengthSelect.value = settings.chat_length_mode || 'standard';
            }

            // 6. TTS Settings
            const ttsProviderSelect = document.getElementById('tts-provider-select') as HTMLSelectElement;
            const voiceSelect = document.getElementById('voice-type-select') as HTMLSelectElement;

            if (ttsProviderSelect) {
                ttsProviderSelect.value = settings.tts_provider || 'voicevox';

                // Load Voices based on Provider
                await this.loadVoices(ttsProviderSelect.value);

                // Set Voice Selection after loading
                if (voiceSelect && settings.voice_type) {
                    voiceSelect.value = settings.voice_type;
                }
            }

            console.log("ConfigManager: Settings Loaded");

        } catch (err) {
            console.error("ConfigManager: Load Failed", err);
        }
    }

    private async loadVoices(provider: string) {
        const voiceSelect = document.getElementById('voice-type-select') as HTMLSelectElement;
        if (!voiceSelect) return;

        voiceSelect.innerHTML = "<option>Loading...</option>";
        try {
            const voices = await api.get_voice_types(provider);
            voiceSelect.innerHTML = "";
            voices.forEach((v: any) => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.innerText = v.name;
                voiceSelect.appendChild(opt);
            });
        } catch (e) {
            console.error("Load voices failed", e);
            voiceSelect.innerHTML = "<option>Error</option>";
        }
    }

    private initSaveListeners() {
        // Mobile/Web Settings Save Button
        const saveBtn = document.getElementById('settings-save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                const apiKey = (document.getElementById('api-key-input') as HTMLInputElement)?.value;
                const model = (document.getElementById('model-select') as HTMLSelectElement)?.value;
                const fontSize = (document.getElementById('font-size-range') as HTMLInputElement)?.value;
                const opacity = (document.getElementById('bg-opacity-range') as HTMLInputElement)?.value;
                const persona = (document.getElementById('persona-select') as HTMLSelectElement)?.value;
                const lenMode = (document.getElementById('chat-length-select') as HTMLSelectElement)?.value;

                const ttsProvider = (document.getElementById('tts-provider-select') as HTMLSelectElement)?.value;
                const voiceType = (document.getElementById('voice-type-select') as HTMLSelectElement)?.value;

                const settings = {
                    api_key: apiKey,
                    model_name: model,
                    font_size: parseInt(fontSize || '13'),
                    background_opacity: parseInt(opacity || '0'),
                    chat_length_mode: lenMode || 'standard',
                    tts_provider: ttsProvider || 'voicevox',
                    voice_type: voiceType || '3'
                };

                try {
                    await api.save_settings(settings);
                    if (persona) await api.changePersona(persona);
                    alert("設定を保存しました。");
                    const modal = document.getElementById('settings-modal');
                    if (modal) modal.style.display = 'none';
                } catch (e: any) {
                    alert("保存失敗: " + e.message);
                }
            });
        }

        // TTS Provider Change Listener
        const ttsProviderSelect = document.getElementById('tts-provider-select') as HTMLSelectElement;
        if (ttsProviderSelect) {
            ttsProviderSelect.addEventListener('change', async (e: any) => {
                await this.loadVoices(e.target.value);
            });
        }

        // Font Size Preview
        const fRange = document.getElementById('font-size-range') as HTMLInputElement;
        if (fRange) {
            fRange.addEventListener('input', (e: any) => {
                const size = e.target.value + 'px';
                const label = document.getElementById('font-size-value');
                if (label) label.innerText = size;
                document.documentElement.style.setProperty('--chat-font-size', size);
            });
        }

        // Opacity Preview
        const bgRange = document.getElementById('bg-opacity-range') as HTMLInputElement;
        if (bgRange) {
            bgRange.addEventListener('input', (e: any) => {
                this.updateBackgroundOpacity(parseInt(e.target.value));
            });
        }
    }

    private updateBackgroundOpacity(percent: number) {
        const label = document.getElementById('bg-opacity-value');
        if (label) label.innerText = percent + '%';

        const maxAlpha = 0.4; // 40% max white
        const alpha = (percent / 100) * maxAlpha;
        const bg = document.getElementById('character-area');

        if (bg) {
            bg.style.backgroundColor = percent === 0 ? 'transparent' : `rgba(255, 255, 255, ${alpha.toFixed(2)})`;
        }
    }
}
