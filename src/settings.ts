// settings.ts
// Logic for the standalone settings window
export { }; // Treat as module

declare global {
    interface Window {
        pywebview?: {
            api: {
                close_window: () => void;
                resize_window: (width: number, height: number) => void;
                move_window: (x: number, y: number) => void;
                get_window_pos: () => Promise<{ x: number, y: number }>;
                open_settings: () => void;
                get_settings: () => Promise<any>;
                save_settings: (settings: any) => Promise<any>;
                chat: (message: string) => Promise<any>;
                get_personas: () => Promise<string[]>;
                get_url_metadata: (url: string) => Promise<{ title: string, image: string | null }>;
                suggest_reply: () => Promise<string>;
                force_talk: () => Promise<any>;
            };
        };
    }
}

const fontSizeRange = document.getElementById('font-size-range') as HTMLInputElement;
const fontSizeValue = document.getElementById('font-size-value');
const bgOpacityRange = document.getElementById('bg-opacity-range') as HTMLInputElement;
const bgOpacityValue = document.getElementById('bg-opacity-value');
const apiKeyInput = document.getElementById('api-key-input') as HTMLInputElement;
const modelSelect = document.getElementById('model-select') as HTMLSelectElement;
const personaSelect = document.getElementById('persona-select') as HTMLSelectElement;
const voiceSelect = document.getElementById('voice-select') as HTMLSelectElement;
const saveBtn = document.getElementById('save-btn');
// const closeBtn = document.getElementById('settings-close-btn'); // Not present in HTML

// Sync UI updates
if (fontSizeRange && fontSizeValue) {
    fontSizeRange.addEventListener('input', () => {
        fontSizeValue.innerText = `${fontSizeRange.value}px`;
    });
}
if (bgOpacityRange && bgOpacityValue) {
    bgOpacityRange.addEventListener('input', () => {
        bgOpacityValue.innerText = `${bgOpacityRange.value}%`;
    });
}

// Load Settings
window.addEventListener('pywebviewready', async () => {
    if (window.pywebview && window.pywebview.api) {
        try {
            const settings = await window.pywebview.api.get_settings();
            // Fetch Persona List dynamically
            const personas = await window.pywebview.api.get_personas();

            console.log("Settings loaded:", settings);
            console.log("Personas loaded:", personas);

            if (fontSizeRange) {
                fontSizeRange.value = settings.font_size || 13;
                if (fontSizeValue) fontSizeValue.innerText = `${settings.font_size || 13}px`;
            }
            if (bgOpacityRange) {
                bgOpacityRange.value = settings.background_opacity || 0;
                if (bgOpacityValue) bgOpacityValue.innerText = `${settings.background_opacity || 0}%`;
            }
            if (apiKeyInput) apiKeyInput.value = settings.api_key || "";
            if (modelSelect) modelSelect.value = settings.model || "gemini-2.5-flash-lite";
            if (voiceSelect) voiceSelect.value = settings.voice_type || "ja-JP-Neural2-B";

            // Populate Personas
            if (personaSelect && personas) {
                personaSelect.innerHTML = "";
                personas.forEach((filename: string) => {
                    const opt = document.createElement('option');
                    opt.value = filename;
                    opt.innerText = filename; // Display filename for now
                    personaSelect.appendChild(opt);
                });
                // Use current_persona_file if available, otherwise fallback to id or default
                personaSelect.value = settings.current_persona_file || "default.yaml";
            }

        } catch (e) {
            console.error("Failed to load settings:", e);
        }
    }
});

// Close Button logic removed as button does not exist


// Save Settings
if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
        const settings = {
            api_key: apiKeyInput ? apiKeyInput.value : "",
            model: modelSelect ? modelSelect.value : "gemini-2.5-flash-lite",
            font_size: fontSizeRange ? parseInt(fontSizeRange.value) : 13,
            background_opacity: bgOpacityRange ? parseInt(bgOpacityRange.value) : 0,
            current_persona_file: personaSelect ? personaSelect.value : "default.yaml",
            voice_type: voiceSelect ? voiceSelect.value : "ja-JP-Neural2-B"
        };

        if (window.pywebview && window.pywebview.api) {
            const res = await window.pywebview.api.save_settings(settings);
            if (res.status === 'success') {
                alert('Saved! Closing settings...');
                window.close(); // Close this secondary window
            } else {
                alert('Error: ' + res.message);
            }
        }
    });
}
