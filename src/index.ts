/// <reference path="./types.d.ts" />
export { }; // Ensure this file is treated as a module
import { api } from './api_client.js';

import { Live2DModel } from 'pixi-live2d-display';
import { SoulBubbleManager } from './soul_bubble.js';

// Debug: Check Renderer
const userAgent = navigator.userAgent;
console.log('UserAgent:', userAgent);
if (userAgent.indexOf('Edg') === -1) {
    console.warn('Warning: Not using Edge Chromium? Transparency might fail.');
}

// Layout Mode Detection (Phase 18 Refactor)
function detectLayoutMode() {
    const isMobileUA = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const isSmallScreen = window.innerWidth <= 768;

    // Strict Mobile Mode: Must be Mobile Device AND Small Screen
    // This prevents Desktop (Small Window) from triggering Mobile Mode.
    if (isMobileUA && isSmallScreen) {
        if (!document.body.classList.contains('mobile-mode')) {
            document.body.classList.add('mobile-mode');
            console.log("Switched to MOBILE LAYOUT");
            // @ts-ignore
            if (typeof window.resizeModel === 'function') window.resizeModel();
        }
    } else {
        if (document.body.classList.contains('mobile-mode')) {
            document.body.classList.remove('mobile-mode');
            console.log("Switched to DESKTOP LAYOUT");
            // @ts-ignore
            if (typeof window.resizeModel === 'function') window.resizeModel();
        }
    }
}

// Initial Check
window.addEventListener('DOMContentLoaded', detectLayoutMode);
// Dynamic Check (Orientation change, resize on mobile)
window.addEventListener('resize', detectLayoutMode);

// Types moved to types.d.ts

// Global reference to Model for LipSync
import { AudioManager } from './services/audio_manager.js';

// Global reference to Model for LipSync
let live2dModel: any = null;
let audioCtx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let mediaSource: MediaElementAudioSourceNode | null = null;

const suggestionToggleBtn = document.getElementById('suggestion-toggle-btn');
const suggestionPopup = document.getElementById('suggestion-popup');

// Audio Player UI
const audioPlayer = document.getElementById('audio-player');
const audioStopBtn = document.getElementById('audio-stop-btn');
const audioSpeedBtn = document.getElementById('audio-speed-btn');

// Initialize AudioManager
const audioManager = AudioManager.getInstance();

// Bind UI Events
if (audioStopBtn) {
    audioStopBtn.addEventListener('click', () => audioManager.stop());
}

if (audioSpeedBtn) {
    audioSpeedBtn.addEventListener('click', () => {
        audioManager.toggleSpeed();
    });
}

// Subscribe to State Changes
audioManager.onPlayStateChange = (isPlaying) => {
    if (audioPlayer) {
        if (isPlaying) {
            audioPlayer.classList.add('visible');
            audioPlayer.style.display = 'flex';
        } else {
            audioPlayer.classList.remove('visible');
            setTimeout(() => {
                if (!audioPlayer.classList.contains('visible')) {
                    audioPlayer.style.display = 'none';
                }
            }, 300); // Wait for fade out
        }
    }
};

audioManager.onSpeedChange = (speed) => {
    if (audioSpeedBtn) {
        audioSpeedBtn.innerText = `x${speed.toFixed(1)}`;
    }
};


// --- Lip Sync Logic (Refactored for Singleton Audio) ---
function playAudioWithLipSync(url: string) {
    // 1. Setup AudioContext if needed
    if (!audioCtx) {
        // @ts-ignore
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }

    // 2. Setup Analyser Node ONCE for the singleton audio element
    // Crucial: createMediaElementSource can only be called once per element.
    if (!mediaSource) {
        mediaSource = audioCtx.createMediaElementSource(audioManager.audio);
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        mediaSource.connect(analyser);
        analyser.connect(audioCtx.destination);
    }

    // 3. Play via Manager
    audioManager.play(url);

    // 4. Lip Sync Loop
    if (!analyser) return; // Should not happen

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    let currentMouthY = 0;

    const updateLip = () => {
        if (audioManager.audio.paused || audioManager.audio.ended) {
            if (live2dModel?.internalModel?.coreModel) {
                live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', 0);
            }
            return;
        }

        requestAnimationFrame(updateLip);
        analyser!.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
        let average = sum / bufferLength;

        // Sensitivity
        let targetOpenAmount = (average / 60); // Tuning
        if (targetOpenAmount < 0.1) targetOpenAmount = 0;
        if (targetOpenAmount > 1.0) targetOpenAmount = 1.0;

        // Smoothing
        const smoothing = 0.3;
        currentMouthY += (targetOpenAmount - currentMouthY) * smoothing;

        if (live2dModel?.internalModel?.coreModel) {
            live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', currentMouthY);
        }
    };

    // Trigger loop when play actually starts
    audioManager.audio.onplay = () => {
        updateLip();
    };
}
// --- Error Handling Overlay ---
function showError(message: string) {
    // ... (Keep existing error handler)
    console.error(message);
}

// ... (Existing Event Listeners) ...

// --- Context Menu Logic ---
const menu = document.getElementById('context-menu') as HTMLElement;
const settingsButton = document.getElementById('menu-settings');
const closeButton = document.getElementById('menu-close');

// UI Elements
const rightPanel = document.getElementById('right-panel') as HTMLElement;
const chatToggleBtn = document.getElementById('chat-toggle-btn'); // New toggle button
const settingsModal = document.getElementById('settings-modal'); // Legacy ref? Or needed for hiding modal? 
// Actually we removed the modal logic but some TS might still reference it if I didn't clean it up?
// The build errors showed usage of 'settingsModal' in line 167 etc.
// Wait, I thought I removed modal code? 
// Ah, lines 167-176 in current file view still reference 'settingsModal'.
// I should probably keep the definition or remove the usage blocks.
// The usage blocks are:
// 1. Context menu strict close (lines 142-146 in prev view, lines ~60 in current view?)
// Let's restore definitions to fix errors first, then maybe clean up if needed.
const settingsCloseBtn = document.getElementById('settings-close-btn');
const fontSizeRange = document.getElementById('font-size-range') as HTMLInputElement;
const fontSizeValue = document.getElementById('font-size-value');
const characterArea = document.getElementById('character-area') as HTMLElement;

if (menu) {
    document.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        menu.style.display = 'block';
        menu.style.left = e.pageX + 'px';
        menu.style.top = e.pageY + 'px';
    });

    document.addEventListener('click', function (e) {
        if (menu.style.display === 'block') {
            menu.style.display = 'none';
        }
    });
}

// --- Chat Logic ---
const chatInput = document.getElementById('chat-input') as HTMLTextAreaElement;
const chatSendBtn = document.getElementById('chat-send-btn');
const forceTalkBtn = document.getElementById('force-talk-btn');
const chatLogArea = document.getElementById('chat-log-area');

// ... (existing code)

if (chatSendBtn) {
    chatSendBtn.addEventListener('click', () => sendMessage()); // Wrapper to avoid event args
}

// Force Talk Logic
// Force Talk Logic
// Helper for Mobile Debugging
function logToServer(msg: string) {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.debug_log) {
        window.pywebview.api.debug_log(msg).catch((e: any) => console.error("Bridge log failed", e));
    } else {
        // Fallback or Web Mode
        fetch('/api/debug_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        }).catch(e => console.error("Log failed", e));
    }
}

// Force Talk Logic
if (forceTalkBtn) {
    const trigger = (e: Event) => {
        e.preventDefault();
        logToServer("Force Talk Button Pressed (Event: " + e.type + ")");
        triggerForceTalk();
    };
    forceTalkBtn.addEventListener('click', trigger);
    forceTalkBtn.addEventListener('touchstart', trigger, { passive: false });
    logToServer("Force Talk Button Logic Initialized");
} else {
    logToServer("ERROR: Force Talk Button element not found at init");
}

// --- Session Restore Logic (Phase 35) ---
async function restoreSession() {
    logToServer("restoreSession() Called.");
    try {
        const history = await api.restore_history();
        logToServer(`restoreSession received raw: ${JSON.stringify(history)}`); // LOG CONTENT
        logToServer(`restoreSession received: ${history ? history.length : 'null'} items`);

        if (!history || history.length === 0) return;

        // Render messages without TTS/AI triggers
        history.forEach((msg: any) => {
            logToServer(`Restoring msg: ${msg.role} - ${msg.text.substring(0, 20)}...`); // LOG ENTRY

            // Re-use addLog but manual mode
            addLog(msg.text, msg.role, false);
        });

        // Add Divider
        if (chatLogArea) {
            const divider = document.createElement('div');
            divider.className = 'session-divider';
            divider.innerText = '--- Last Session ---';
            divider.style.textAlign = 'center';
            divider.style.color = '#888';
            divider.style.fontSize = '10px';
            divider.style.margin = '10px 0';
            chatLogArea.appendChild(divider);

            // Scroll to bottom
            chatLogArea.scrollTop = chatLogArea.scrollHeight;
        }
        logToServer("Session Restore Completed.");

    } catch (e) {
        logToServer(`Session restore failed: ${e}`);
        console.error("Session restore failed", e);
    }
}

// --- Robust Init for Restore ---
// User Request: Wait for pywebviewready in Desktop, else DOMContentLoaded for Web
const initRestore = () => {
    // Note: window.pywebview might be injected slightly after DOMContentLoaded in some envs,
    // but usually pywebviewready is the standard event.

    // Listener for Desktop
    window.addEventListener('pywebviewready', () => {
        logToServer("Event: pywebviewready. Calling restoreSession (Desktop).");
        restoreSession();
    });

    // Fallback/Web Check
    window.addEventListener('DOMContentLoaded', () => {
        // Give a short grace period to see if pywebview appears
        setTimeout(() => {
            if (!(window as any).pywebview) {
                console.log("No pywebview detected. Calling restoreSession (Web Mode).");
                restoreSession();
            } else {
                logToServer("pywebview detected. Waiting for ready event...");
            }
        }, 100);
    });
};
initRestore();


// Re-check in case script ran too early
const btn = document.getElementById('force-talk-btn');
if (btn && !forceTalkBtn) {
    logToServer("Force Talk Button found on DOMContentLoaded (Late Init)");
    const trigger = (e: Event) => {
        e.preventDefault();
        logToServer("Force Talk Button Pressed (Late Event: " + e.type + ")");
        triggerForceTalk();
    };
    btn.addEventListener('click', trigger);
    btn.addEventListener('touchstart', trigger, { passive: false });
}

async function triggerForceTalk() {
    // 0. Resume Audio
    if (!audioCtx) {
        // @ts-ignore
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }

    // 1. Show Thinking...
    const thinkingId = addLog('考え中...', 'ai', true);
    updateStatus("Thinking...", true);

    // Auto-Open Chat Panel (User Request)
    if (!uiState.isChatOpen) {
        // @ts-ignore
        if (typeof window.openChatPanel === 'function') window.openChatPanel(true);
    }

    // 2. Call Backend
    // Use API Client (Adapts to Desktop/Web)
    try {
        const response = await api.force_talk();

        removeLog(thinkingId);
        updateStatus("Active", true);

        // Handle Response
        let text = "";
        let audio = null;
        let suggestions: string[] = [];

        if (typeof response === 'string') {
            text = response;
        } else {
            text = response.text;
            audio = response.audio;
            suggestions = response.suggestions || [];
        }

        // Output
        processAIResponse(text, audio);

        // Update Suggestions
        updateSuggestions(suggestions);

    } catch (err: any) {
        removeLog(thinkingId);
        addLog('Error: ' + err.message, 'ai');
        updateStatus("Error", false);
    }
}

// --- Suggestion Chips Logic ---
function updateSuggestions(suggestions: string[]) {
    if (!suggestionToggleBtn || !suggestionPopup) return;
    suggestionPopup.innerHTML = ''; // Clear

    if (!suggestions || suggestions.length === 0) {
        suggestionToggleBtn.style.display = 'none';
        suggestionPopup.style.display = 'none';
        return;
    }

    // Show Toggle Button
    suggestionToggleBtn.style.display = 'flex';

    suggestions.forEach(text => {
        const chip = document.createElement('div');
        chip.className = 'suggestion-chip';
        chip.innerText = text;

        // Check for static command styling
        if (text === "別の話題はある？") {
            chip.classList.add('static-cmd');
        }

        chip.addEventListener('click', () => {
            // Fill input and send
            if (chatInput) chatInput.value = text;
            sendMessage();
            // Close popup
            suggestionPopup.style.display = 'none';
        });

        suggestionPopup.appendChild(chip);
    });
}

// Toggle Logic
if (suggestionToggleBtn && suggestionPopup) {
    const toggle = (e: Event) => {
        e.preventDefault();
        logToServer("Suggestion Toggle Pressed (Event: " + e.type + ")");
        const isVisible = suggestionPopup.style.display === 'flex';
        suggestionPopup.style.display = isVisible ? 'none' : 'flex';
        logToServer("Suggestion Popup State: " + (isVisible ? 'Hidden' : 'Shown'));
    };
    suggestionToggleBtn.addEventListener('click', toggle);
    suggestionToggleBtn.addEventListener('touchstart', toggle, { passive: false });
}

if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// --- Emotion-Expression Map ---
const emotions: { [key: string]: string } = {
    '[happy]': '01.blush',  // Smile/Blush
    '[angry]': '02.angry',  // Angry
    '[sad]': '03.cry',      // Cry
    '[pale]': '04.pale',    // Pale
    '[wink]': '06.wink_R',  // Wink
    '[surprise]': '13.surprised', // Surprised
    '[love]': 'fx_01_heart' // Heart FX
};

// --- Response Processing Helper ---
function processAIResponse(text: string, audio: string | null) {
    // --- Detect Emotion Tags ---
    let displayMessage = text;
    let triggeredEmotion = null;

    for (const [tag, expName] of Object.entries(emotions)) {
        if (text.includes(tag)) {
            triggeredEmotion = expName;
            displayMessage = displayMessage.replace(tag, '');
        }
    }

    // Trigger Expression
    if (triggeredEmotion && live2dModel) {
        console.log("Triggering expression:", triggeredEmotion);
        try {
            live2dModel.expression(triggeredEmotion);
        } catch (e) {
            console.warn("Expression trigger failed:", e);
        }
    }

    // Add AI Response (Cleaned)
    addLog(displayMessage, 'ai');

    // Play Audio if available
    if (audio) {
        console.log("Playing audio:", audio);
        playAudioWithLipSync(audio);
    }
}

// --- Receive Message from Backend (Push Notification) ---
(window as any).receiveMessage = function (data: any, audio: string | null) {
    console.log("Received Push Message Data:", data);

    // Ensure AudioContext is active
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume().catch(e => console.warn("Auto-resume failed:", e));
    }

    let text = "";
    let suggestions: string[] = [];

    if (typeof data === 'string') {
        text = data;
    } else if (typeof data === 'object') {
        text = data.response || "";
        suggestions = data.suggestions || [];
    }

    processAIResponse(text, audio);
    updateSuggestions(suggestions);
};


async function sendMessage() {
    // 0. Resume AudioContext immediately (User Interaction)
    if (!audioCtx) {
        // @ts-ignore
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }

    if (!chatInput || !chatLogArea) return;
    const message = chatInput.value.trim();
    if (!message) return;

    // 1. Add User Message
    addLog(message, 'user');
    chatInput.value = '';

    // 2. Show Thinking...
    const thinkingId = addLog('考え中...', 'ai', true);
    updateStatus("Thinking...", true);

    // 3. Call Backend
    try {
        const response = await api.chat(message);
        // Remove Thinking
        removeLog(thinkingId);
        updateStatus("Active", true);

        // Handle Response
        let text = "";
        let audio = null;
        let suggestions: string[] = [];

        if (typeof response === 'string') {
            text = response;
        } else {
            text = response.text;
            audio = response.audio;
            suggestions = response.suggestions || [];
        }

        // Output
        processAIResponse(text, audio);

        // Update Suggestions
        updateSuggestions(suggestions);

    } catch (err: any) {
        removeLog(thinkingId);
        addLog('Error: ' + err.message, 'ai');
        updateStatus("Error", false);
    }
}

// --- Rich Link Utilities ---
function escapeHtml(unsafe: string): string {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function processTextForLinks(text: string): string {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return escapeHtml(text).replace(urlRegex, (url) => {
        // Generate unique ID for card placeholder
        const cardId = 'card-' + Math.random().toString(36).substr(2, 9);

        // Return a temporary anchor + placeholder for rich card
        // We trigger the fetch async
        setTimeout(() => fetchLinkMetadata(url, cardId), 10);

        return `<a href="${url}" target="_blank" class="chat-link">${url}</a><div id="${cardId}" class="link-card-placeholder"></div>`;
    });
}

async function fetchLinkMetadata(url: string, elementId: string) {
    const el = document.getElementById(elementId);
    if (!el || !window.pywebview || !window.pywebview.api) return;

    try {
        const metadata = await window.pywebview.api.get_url_metadata(url);
        if (metadata && metadata.title) {
            // Render Card
            let html = `<div class="link-card" onclick="window.open('${url}', '_blank')">`;
            if (metadata.image) {
                html += `<div class="link-card-thumb" style="background-image: url('${metadata.image}')"></div>`;
            }
            html += `<div class="link-card-content">
                        <div class="link-card-title">${escapeHtml(metadata.title)}</div>
                        <div class="link-card-url">${escapeHtml(url)}</div>
                     </div></div>`;
            el.outerHTML = html; // Replace placeholder
        } else {
            el.remove(); // No data, remove placeholder
        }
    } catch (e) {
        console.warn("Metadata fetch failed", e);
        el.remove();
    }
}

function addLog(text: string, type: 'user' | 'ai', isThinking: boolean = false): string {
    if (!chatLogArea) return '';

    const div = document.createElement('div');
    const id = 'msg-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
    div.id = id;
    div.classList.add('message', type);

    // Use InnerHTML with safe processing
    div.innerHTML = processTextForLinks(text);

    // Add Timestamp
    const timeSpan = document.createElement('span');
    timeSpan.classList.add('msg-timestamp');
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
    timeSpan.innerText = timeStr;
    div.appendChild(timeSpan);

    if (isThinking) {
        div.style.fontStyle = 'italic';
        div.style.color = '#aaa';
    }

    chatLogArea.appendChild(div);
    chatLogArea.scrollTop = chatLogArea.scrollHeight;
    return id;
}

function removeLog(id: string) {
    const el = document.getElementById(id);
    if (el) el.remove();
}




if (closeButton) {
    closeButton.addEventListener('click', function () {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.close_window();
        } else {
            console.warn('Python API not found (Development Mode)');
        }
    });
}

// --- Settings Logic ---
// Elements
// No longer fetching input/range elements here as they are in settings window

// --- Settings Logic ---
// --- Settings Logic ---
// Load basic settings for appearance (Font/Opacity) and Persona
async function loadSettings() {
    try {
        const settings = await api.get_settings();

        // 1. Background Opacity
        if (bgOpacityRange) {
            bgOpacityRange.value = settings.background_opacity || 0;
            updateBackgroundOpacity(settings.background_opacity || 0);
        } else {
            updateBackgroundOpacity(settings.background_opacity || 0);
        }

        // 2. Font Size
        if (settings.font_size) {
            if (fontSizeRange) fontSizeRange.value = settings.font_size;
            if (fontSizeValue) fontSizeValue.innerText = settings.font_size + 'px';
            document.documentElement.style.setProperty('--chat-font-size', settings.font_size + 'px');
        }

        // 3. API Key & Model
        const apiKeyInput = document.getElementById('api-key-input') as HTMLInputElement;
        const modelSelect = document.getElementById('model-select') as HTMLSelectElement;
        if (apiKeyInput) apiKeyInput.value = settings.api_key || '';
        if (modelSelect && settings.model_name) modelSelect.value = settings.model_name;

        // 4. Persona (New)
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
            // Set current
            const currentP = settings.current_persona_id || 'default';
            personaSelect.value = currentP;
        }

    } catch (err) {
        console.error("Failed to load settings:", err);
    }
}
// window.addEventListener('DOMContentLoaded', loadSettings); // Avoid race condition
window.addEventListener('pywebviewready', loadSettings);

// Open Settings Window
if (settingsButton) {
    settingsButton.addEventListener('click', function () {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.open_settings();
        }
    });
}

// Mobile Settings Save Logic
const settingsSaveBtn = document.getElementById('settings-save-btn');
if (settingsSaveBtn) {
    settingsSaveBtn.addEventListener('click', async () => {
        const apiKeyInput = document.getElementById('api-key-input') as HTMLInputElement;
        const modelSelect = document.getElementById('model-select') as HTMLSelectElement;
        const personaSelect = document.getElementById('persona-select') as HTMLSelectElement;

        const newSettings: any = {
            font_size: fontSizeRange ? parseInt(fontSizeRange.value) : 13,
            background_opacity: bgOpacityRange ? parseInt(bgOpacityRange.value) : 0,
            api_key: apiKeyInput ? apiKeyInput.value : undefined,
            model_name: modelSelect ? modelSelect.value : undefined
        };

        try {
            await api.save_settings(newSettings);

            // Handle Persona Change
            if (personaSelect) {
                await api.changePersona(personaSelect.value);
            }

            alert("Settings Saved!");
            if (settingsModal) settingsModal.style.display = 'none';
        } catch (e: any) {
            alert("Save Failed: " + e.message);
        }
    });
}

// Prevent drag when clicking on settings modal (Stop EasyDrag)
if (settingsModal) {
    settingsModal.addEventListener('mousedown', (e) => {
        e.stopPropagation();
    });
    // Also stop propagation for children inputs to be safe
    const inputs = settingsModal.querySelectorAll('input, button, select');
    inputs.forEach(el => {
        el.addEventListener('mousedown', (e) => e.stopPropagation());
    });
}



// Font Size Change
if (fontSizeRange && fontSizeValue) {
    fontSizeRange.addEventListener('input', (e: any) => {
        const size = e.target.value + 'px';
        fontSizeValue.innerText = size;
        document.documentElement.style.setProperty('--chat-font-size', size);
    });
}

// Background Opacity Change (White/Background transparency)
const bgOpacityRange = document.getElementById('bg-opacity-range') as HTMLInputElement;
const bgOpacityValue = document.getElementById('bg-opacity-value');
const characterAreaBg = document.getElementById('character-area') as HTMLElement;

// Function to update background
function updateBackgroundOpacity(percent: number) {
    if (bgOpacityValue) bgOpacityValue.innerText = percent + '%';

    // User wants: 0% = Transparent, 100% = Thin White (e.g. 0.4)
    // Map 0-100 to 0.0-0.4
    const maxAlpha = 0.4;
    const alpha = (percent / 100) * maxAlpha;

    // STRICTLY set rgba
    if (characterAreaBg) {
        if (percent === 0) {
            characterAreaBg.style.backgroundColor = 'transparent';
        } else {
            characterAreaBg.style.backgroundColor = `rgba(255, 255, 255, ${alpha.toFixed(2)})`;
        }
    }
}

if (bgOpacityRange) {
    // Initialize
    updateBackgroundOpacity(parseInt(bgOpacityRange.value));

    bgOpacityRange.addEventListener('input', (e: any) => {
        const val = parseInt(e.target.value);
        updateBackgroundOpacity(val);
        e.stopPropagation(); // Prevent drag on slider
    });
}

// UI State Management
const uiState = {
    charWidth: 500,
    chatWidth: 450, // width + margin
    logWidth: 410, // width 400 + margin 10
    isChatOpen: false,
    isLogOpen: false
};

const leftPanel = document.getElementById('left-panel') as HTMLElement;
// rightPanel is already defined above
const debugContent = document.getElementById('debug-content');

// --- Chat Toggle Function (Exposed) ---
// We expose this so SoulBubble and ForceTalk can open the panel
(window as any).openChatPanel = async function (open: boolean = true) {
    if (open === uiState.isChatOpen) return; // No change

    uiState.isChatOpen = open;
    rightPanel.classList.toggle('open', uiState.isChatOpen);
    if (chatToggleBtn) chatToggleBtn.classList.toggle('active', uiState.isChatOpen);

    if (window.pywebview && window.pywebview.api) {
        try {
            // Margin Logic: 
            // Right Panel CSS has margin-left: 40px. Width 450. Total 490.
            const chatTotalWidth = 490;
            let w = uiState.charWidth;
            if (uiState.isLogOpen) w += uiState.logWidth;
            if (uiState.isChatOpen) w += chatTotalWidth;

            await window.pywebview.api.resize_window(w, 500);
        } catch (err) {
            console.error("Resize failed:", err);
        }
    }
};

// --- Chat Toggle Logic ---
if (chatToggleBtn && rightPanel) {
    chatToggleBtn.addEventListener('click', async () => {
        // Toggle current state
        // @ts-ignore
        if (typeof window.openChatPanel === 'function') window.openChatPanel(!uiState.isChatOpen);
    });
}


// --- Phase 7.5 UI Logic ---

// 1. Clock
const clockTime = document.getElementById('clock-time');
const clockDate = document.getElementById('clock-date');

function updateClock() {
    const now = new Date();
    if (clockTime) {
        // HH:MM:SS
        clockTime.innerText = now.toLocaleTimeString('ja-JP', { hour12: false });
    }
    if (clockDate) {
        // YYYY-MM-DD
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, '0');
        const d = String(now.getDate()).padStart(2, '0');
        clockDate.innerText = `${y}-${m}-${d}`;
    }
}
setInterval(updateClock, 1000);
updateClock(); // Initial call

// 2. Status Bar
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');

function updateStatus(text: string, isActive: boolean = true) {
    if (statusText) statusText.innerText = text;
    if (statusDot) {
        statusDot.style.backgroundColor = isActive ? '#ffa500' : '#888';
        statusDot.style.animation = isActive ? 'pulse 2s infinite' : 'none';
    }
}
// Initial status
updateStatus("Idle", true);

// 3. Soul Bubble Logic
const soulBubbleManager = new SoulBubbleManager();

// Exposed for Python
// @ts-ignore
(window as any).showSoulBubble = function (category: string, text: string, actionId: string, type: string = 'normal') {
    if (soulBubbleManager) {
        soulBubbleManager.addBubble(category, text, actionId, type);
    }
};

// --- Systematic Panel Logic (Debug & History) ---
const debugBtn = document.getElementById('debug-btn');
const historyBtn = document.getElementById('history-btn');
const closeDebugBtn = document.getElementById('close-debug');
const panelTitle = document.getElementById('panel-title');
const historyContent = document.getElementById('history-content');

let currentActivePanel: 'debug' | 'history' | 'none' = 'none';

async function toggleLeftPanel(mode: 'debug' | 'history') {
    if (!leftPanel || !window.pywebview || !window.pywebview.api) return;

    const wasOpen = uiState.isLogOpen;
    const previousMode = currentActivePanel;

    if (currentActivePanel === mode) {
        // Closing active panel
        currentActivePanel = 'none';
        uiState.isLogOpen = false;
    } else {
        // Opening or Switching
        currentActivePanel = mode;
        uiState.isLogOpen = true;
    }

    // Update UI Content Visibility
    if (debugContent) debugContent.style.display = (currentActivePanel === 'debug') ? 'block' : 'none';
    if (historyContent) historyContent.style.display = (currentActivePanel === 'history') ? 'block' : 'none';

    // Update Header
    if (panelTitle) {
        panelTitle.innerText = (currentActivePanel === 'debug') ? 'SYSTEM LOGS' : 'CHAT HISTORY';
        panelTitle.style.color = (currentActivePanel === 'debug') ? '#0f0' : '#0ff';
    }

    // Window Resize Logic
    // Only resize if state changed (Closed <-> Open)
    // If Switching (Open <-> Open), no resize needed.
    if (wasOpen !== uiState.isLogOpen) {
        leftPanel.classList.toggle('open', uiState.isLogOpen);
        try {
            const { x, y } = await window.pywebview.api.get_window_pos();
            // Width calculation
            // Note: Chat Panel Width logic used 490 in openChatPanel, but toggleLogPanel used 390?
            // CSS: #right-panel width 450 + margin-left 40 = 490.
            // Let's use 490 to be safe/consistent with CSS.
            const chatTotalWidth = 490;
            let baseW = uiState.charWidth + (uiState.isChatOpen ? chatTotalWidth : 0);

            if (uiState.isLogOpen) {
                // OPENING: Move Left, Resize Width +
                await window.pywebview.api.move_window(x - uiState.logWidth, y);
                await window.pywebview.api.resize_window(baseW + uiState.logWidth, 500);
            } else {
                // CLOSING: Resize Width -, Move Right
                await window.pywebview.api.move_window(x + uiState.logWidth, y);
                await window.pywebview.api.resize_window(baseW, 500);
            }
        } catch (e) {
            console.error("Panel Toggle Failed", e);
        }
    }

    // Fetch History if needed
    if (currentActivePanel === 'history') {
        loadHistorySystematic();
    }
}

async function loadHistorySystematic() {
    if (!historyContent) return;
    historyContent.innerHTML = '<div style="color:#888; text-align:center; margin-top:10px;">Loading data...</div>';

    try {
        const history = await api.get_history(50);
        renderHistorySystematic(history);
    } catch (e) {
        historyContent.innerHTML = '<div style="color:#f44; margin-top:10px;">Error loading history.</div>';
    }
}

function renderHistorySystematic(logs: any[]) {
    if (!historyContent) return;
    historyContent.innerHTML = '';

    if (!logs || logs.length === 0) {
        historyContent.innerHTML = '<div style="color:#888; margin-top:10px;">No history found.</div>';
        return;
    }

    logs.forEach(log => {
        const item = document.createElement('div');
        item.className = 'hist-entry';
        let timeStr = '--:--';
        if (log.timestamp) {
            try {
                const d = new Date(log.timestamp);
                timeStr = d.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
            } catch (e) { }
        }
        const persona = log.persona || 'System';
        item.innerHTML = `
            <div class="hist-meta">
                <span style="color:#666;">[${timeStr}]</span> 
                <span style="color:${log.user ? '#8cf' : '#ddd'}; font-weight:bold;">${log.user ? 'USER' : persona}</span>
            </div>
            <div style="padding-left:10px; color:${log.user ? '#ccc' : '#fff'};">
               ${log.user ? escapeHtml(log.user) : escapeHtml(log.ai)}
            </div>`;
        historyContent.appendChild(item);
    });
    historyContent.scrollTop = historyContent.scrollHeight;
}

if (debugBtn) debugBtn.addEventListener('click', () => toggleLeftPanel('debug'));
if (historyBtn) historyBtn.addEventListener('click', () => toggleLeftPanel('history'));

// Updated Close Button to just close current
if (closeDebugBtn) closeDebugBtn.addEventListener('click', () => {
    if (currentActivePanel !== 'none') toggleLeftPanel(currentActivePanel);
});

// 3. Debug Log Content
function logToDebug(msg: string, type: 'info' | 'warn' | 'error' = 'info') {
    if (!debugContent) return;

    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    const now = new Date();
    timeSpan.innerText = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;

    const msgSpan = document.createElement('span');
    msgSpan.className = `log-${type}`;
    msgSpan.innerText = msg;

    entry.appendChild(timeSpan);
    entry.appendChild(msgSpan);

    // Insert at top? or Append? Append usually.
    debugContent.appendChild(entry);
    debugContent.appendChild(entry);
    debugContent.scrollTop = debugContent.scrollHeight;
}

// Global Exposure for Python
(window as any).logToDebug = logToDebug;

// --- Dual Context Menus (Phase 35 Follow-up) ---
const contextMenu = document.getElementById('context-menu');
// Removed duplicate characterArea declaration (it's likely defined globally or earlier)
// Use the earlier reference or just getElementById here if scope allows, but re-using existing var is safer
const charAreaRef = document.getElementById('character-area');

// Helper to show menu
const showCtxMenu = (e: MouseEvent, type: 'restore' | 'settings') => {
    e.preventDefault();
    if (!contextMenu) return;

    const x = e.clientX;
    const y = e.clientY;

    // Content Switching
    contextMenu.innerHTML = ''; // Clear

    if (type === 'restore') {
        contextMenu.innerHTML = `
            <div class="ctx-item" id="ctx-restore-action">
                <span class="ctx-icon">↻</span>
                <span>履歴を復元</span>
            </div>
        `;
        // Re-attach listener
        setTimeout(() => {
            const btn = document.getElementById('ctx-restore-action');
            if (btn) {
                btn.addEventListener('click', async () => {
                    contextMenu.classList.remove('visible');
                    logToServer("[UI] Manual Restore Triggered.");
                    if (leftPanel) {
                        const originalBorder = leftPanel.style.borderColor;
                        leftPanel.style.borderColor = '#0f0';
                        leftPanel.style.transition = 'all 0.3s ease';
                        await restoreSession();
                        setTimeout(() => {
                            leftPanel.style.borderColor = originalBorder;
                            leftPanel.style.transition = ''; // Clear transition after use
                        }, 800);
                    }
                });
            }
        }, 0);
    } else {
        contextMenu.innerHTML = `
            <div class="ctx-item" id="ctx-settings-action">
                <span class="ctx-icon">⚙️</span>
                <span>設定</span>
            </div>
            <div style="height:1px; background:#444; margin:2px 0;"></div>
            <div class="ctx-item" id="ctx-exit-action">
                <span class="ctx-icon">❌</span>
                <span>終了</span>
            </div>
        `;
        // Re-attach listeners
        setTimeout(() => {
            const settingsBtn = document.getElementById('ctx-settings-action');
            if (settingsBtn) {
                settingsBtn.addEventListener('click', () => {
                    contextMenu.classList.remove('visible');
                    // Use new Window API for Settings (Tabbed Interface)
                    if (window.pywebview) {
                        window.pywebview.api.open_settings();
                    } else {
                        console.error("pywebview API not available");
                    }
                });
            }
            const exitBtn = document.getElementById('ctx-exit-action');
            if (exitBtn) {
                exitBtn.addEventListener('click', () => {
                    contextMenu.classList.remove('visible');
                    if (window.pywebview) window.pywebview.api.close_window();
                });
            }
        }, 0);
    }

    contextMenu.style.left = `${x}px`;
    contextMenu.style.top = `${y}px`;
    contextMenu.classList.add('visible');
    console.log(`[UI] Context Menu Opened (${type})`);
};

if (leftPanel) {
    leftPanel.addEventListener('contextmenu', (e) => showCtxMenu(e, 'restore'));
}

if (characterArea) {
    characterArea.addEventListener('contextmenu', (e) => {
        showCtxMenu(e, 'settings');
    });
}

// Global Close
window.addEventListener('click', () => {
    if (contextMenu?.classList.contains('visible')) {
        contextMenu.classList.remove('visible');
    }
});

// Hook into console to capture system logs? 
// Or just manual logging. Let's redirect console.log/error/warn partially.
const originalLog = console.log;
const originalWarn = console.warn;
const originalError = console.error;

console.log = (...args) => {
    originalLog(...args);
    // Serialize args
    const msg = args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ');
    logToDebug(msg, 'info');
};

console.warn = (...args) => {
    originalWarn(...args);
    const msg = args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ');
    logToDebug(msg, 'warn');
};

console.error = (...args) => {
    originalError(...args);
    const msg = args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ');
    logToDebug(msg, 'error');
};

logToDebug("System initialized.", "info");
logToDebug("Live2D Engine starting...", "info");


// --- UI Interaction Logic (Phase 5) ---
const appContainer = document.getElementById('app-container') as HTMLElement;
let fadeTimer: any = null;

// Initial state: UI hidden
if (appContainer) {
    appContainer.classList.add('ui-hidden');

    // Show UI on mouse move
    window.addEventListener('mousemove', () => {
        appContainer.classList.remove('ui-hidden');

        // Reset timer
        if (fadeTimer) clearTimeout(fadeTimer);

        // Hide again after 60 seconds (as requested, originally 1 min)
        // Shortened to 5 secs for debug feels too fast? Let's stick to 60s as spec or maybe 5s for demo?
        // Spec says "1 min". Let's do 60000.
        fadeTimer = setTimeout(() => {
            appContainer.classList.add('ui-hidden');
        }, 60000);
    });
}

// --- Live2D Initialization ---
(async function () {
    try {
        console.log('Initializing PixiJS...');
        fetch('/api/debug_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Init: Starting PixiJS Init..." })
        }).catch(e => { });

        if (typeof PIXI === 'undefined') {
            throw new Error('PIXI is not loaded. Check script tags.');
        }

        // Initialize Pixi Application
        const characterArea = document.getElementById('character-area') as HTMLElement;
        if (!characterArea) throw new Error('Character Area not found');

        const app = new PIXI.Application({
            view: document.createElement('canvas'),
            autoStart: true,
            resizeTo: characterArea, // Resize to the specific 500x500 frame
            backgroundAlpha: 0,
        });

        fetch('/api/debug_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Init: PIXI App Created" })
        }).catch(e => { });

        // Insert Canvas INSIDE the character area (behind button)
        const canvas = app.view as HTMLCanvasElement;
        characterArea.appendChild(canvas);

        // Ensure menu is top
        if (menu) menu.style.zIndex = "4000";

        // ★MOVED: Define resizeModel early to avoid ReferenceError
        const resizeModel = () => {
            // Need model to be accessible? Yes, via closure 'model' variable which is defined LATER... 
            // WAIT. 'model' is defined later (line 902).
            // If I move this up, I cannot close over 'model' const yet.
            // I must use 'live2dModel' (let var) or window.live2d_model.
            // Or change 'const model' to 'let model' at top scope.

            // Let's use 'window.live2d_model' or 'live2dModel' variable which is 'let' at top level?
            // Line 42: let live2dModel: any = null;
            // Let's rely on 'live2dModel' global variable.

            const model = live2dModel; // Use global ref
            if (!model) return;

            const frameW = characterArea.clientWidth;
            const frameH = characterArea.clientHeight;

            // Debug Log to Server
            const debugMsg = `Resize: Frame=${frameW}x${frameH}, Mode=${document.body.classList.contains('mobile-mode') ? 'Mobile' : 'Desktop'}`;
            console.log(debugMsg);

            fetch('/api/debug_log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: debugMsg })
            }).catch(() => { });

            // Force PIXI to match container size in pixels (Critical for mobile)
            if (app && app.renderer) {
                app.renderer.resize(frameW, frameH);
                app.view.style.width = frameW + "px";
                app.view.style.height = frameH + "px";
            }

            // Recalculate Scale using Logic Height (Stable)
            const internalHeight = model.internalModel.height;
            const targetScale = (frameH * 2.2) / internalHeight;

            // Debug Calc
            const debugText = `ResizeCalc: FrameH=${frameH}, InternalH=${internalHeight}, TargetScale=${targetScale.toFixed(4)}`;
            console.log(debugText);

            model.scale.set(targetScale);

            // 1. 中央揃え (X軸)
            model.x = (frameW / 2) - (model.width / 2);

            // 2. スマホかPCかで高さを変える (Y軸)
            if (document.body.classList.contains('mobile-mode')) {
                // スマホモード: 
                // エリア自体が「画面上半分」になったので、
                // そのエリアの「真ん中より少し下」くらいに顔が来ると丁度いいです

                // frameH が「上半分の高さ」になっています
                // モデルの基準点にもよりますが、0.2〜0.3 くらいがバランス良いはず
                // → 初期表示で埋もれるとのことなので、ガッツリ上げます (マイナス指定)
                model.y = -frameH * 0.1;
            } else {
                // PCモード: 元の計算式
                model.y = (frameH * 0.4) - (model.height * 0.15);
            }

            const status = `ModelState: X=${model.x.toFixed(1)}, Y=${model.y.toFixed(1)}, Scale=${targetScale.toFixed(3)}`;
            console.log(status);
            fetch('/api/debug_log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: status })
            }).catch(() => { });
        };

        // Expose for external calls (e.g. Layout change)
        // @ts-ignore
        window.resizeModel = resizeModel;

        // Check/Load Live2DModel
        let ModelClass = (window as any).Live2DModel;

        if (!ModelClass) {
            // Fallback
            if ((window as any).PIXI.live2d && (window as any).PIXI.live2d.Live2DModel) {
                ModelClass = (window as any).PIXI.live2d.Live2DModel;
            } else {
                console.error('Available globals:', Object.keys(window));
                throw new Error('Live2DModel is not loaded. Ensure pixi-live2d-display script is correct.');
            }
        }

        const modelPath = 'models/fav_usaneko_alwb/fav_usaneko_alwb.model3.json';
        console.log('Loading model from:', modelPath);
        fetch('/api/debug_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: `Init: Loading Model from ${modelPath}` })
        }).catch(e => { });

        const model = await ModelClass.from(modelPath);

        fetch('/api/debug_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Init: Model Loaded Successfully" })
        }).catch(e => { });

        app.stage.addChild(model);

        fetch('/api/debug_log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: "Init: Model Added to Stage" })
        }).catch(e => { });

        // Expose model to global scope for LipSync
        live2dModel = model;
        // @ts-ignore
        window.live2d_model = model; // For global access (resize)

        // Initial Resize
        // @ts-ignore
        if (typeof resizeModel === 'function') resizeModel();

        // Initial Layout (500x500 Fixed Frame)
        const frameW = characterArea.clientWidth; // 500
        const frameH = characterArea.clientHeight; // 500

        // Scale: User requested "More Zoomed in"
        // Previous was 1.5x, let's go for 2.2x to really show the face.
        const baseScale = (frameH * 2.2) / model.height;
        model.scale.set(baseScale);

        // Position: 
        // X: Center
        model.x = (frameW / 2) - (model.width / 2);

        // Y: Move down drastically to center face.
        // Y: Move down drastically to center face.
        model.y = (frameH * 0.4) - (model.height * 0.15); // Adjust Y to bring face down to view

        // ★追加: 画面リサイズ時にモデル位置を再計算する関数


        // リサイズイベントに登録
        window.addEventListener('resize', () => {
            setTimeout(resizeModel, 100);
        });

        // 初回実行
        resizeModel();

        // --- Zoom Control ---
        window.addEventListener('wheel', (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                // Finer zoom control as requested
                const sensitivity = 0.0002;
                const scaleAmount = -e.deltaY * sensitivity;

                model.scale.x += scaleAmount;
                model.scale.y += scaleAmount;

                if (model.scale.x < 0.1) model.scale.set(0.1);

                // Adjust position to keep centered roughly
                model.x = (frameW / 2) - (model.width / 2);
            }
        }, { passive: false });

        console.log('Live2D model loaded successfully');

    } catch (e: any) {
        showError('Live2D Init Failed: ' + e.message + '\n' + (e.stack || ''));
    }
})();

// --- Idle Motion Logic (Blink & Breath) ---
function startIdleMotion(model: any) {
    // Tuning: Frequency increased (was 2-5s, now 1-4s)
    let nextBlinkTime = Date.now() + Math.random() * 3000 + 1000;
    let blinkState = 0; // 0: Open, 1: Closing, 2: Closed, 3: Opening
    let blinkStartTime = 0;
    const blinkDuration = 200; // ms

    const updateIdle = () => {
        if (!model || !model.internalModel || !model.internalModel.coreModel) {
            requestAnimationFrame(updateIdle);
            return;
        }

        const now = Date.now();

        // 1. Breathing (Sine Wave)
        // Cycle every 3 seconds (approx)
        const t = (now / 1000) * 2;
        const breathValue = (Math.sin(t) + 1) / 2; // 0.0 to 1.0
        model.internalModel.coreModel.setParameterValueById('ParamBreath', breathValue);

        // 2. Blinking
        if (blinkState === 0) {
            // Waiting for next blink
            if (now > nextBlinkTime) {
                blinkState = 1;
                blinkStartTime = now;
            }
        } else {
            // Blinking in progress
            const elapsed = now - blinkStartTime;
            let eyeValue = 1.0;

            if (elapsed < blinkDuration / 2) {
                // Closing
                eyeValue = 1.0 - (elapsed / (blinkDuration / 2));
            } else if (elapsed < blinkDuration) {
                // Opening
                eyeValue = (elapsed - (blinkDuration / 2)) / (blinkDuration / 2);
            } else {
                // Done
                blinkState = 0;
                eyeValue = 1.0;
                // Tuning: Interval set to 1-4s
                nextBlinkTime = now + Math.random() * 3000 + 1000;
            }

            // Set Parameters (Standard IDs)
            model.internalModel.coreModel.setParameterValueById('ParamEyeLOpen', eyeValue);
            model.internalModel.coreModel.setParameterValueById('ParamEyeROpen', eyeValue);
        }

        requestAnimationFrame(updateIdle);
    };

    requestAnimationFrame(updateIdle);
}





// Mobile Settings Button Logic (added Phase 18.5)
window.addEventListener('DOMContentLoaded', () => {
    const mobileSettingsBtn = document.getElementById('mobile-settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const settingsCloseBtn = document.getElementById('settings-close-btn');

    if (mobileSettingsBtn && settingsModal) {
        mobileSettingsBtn.addEventListener('click', () => {
            settingsModal.style.display = 'block';
        });
    }

    if (settingsCloseBtn && settingsModal) {
        settingsCloseBtn.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });
    }
});

// Settings Sync Logic (Phase 18.7)
window.addEventListener('pywebviewready', async () => {
    // Only verify/sync if not in Desktop mode (or always? Desktop usually loads from local file anyway?)
    // Desktop PyWebview usually injects values or we might want to sync UI there too if not done.
    // Existing code might not populate Settings Modal on load?
    // Let's populate it.

    try {
        const settings = await api.get_settings();
        if (settings) {
            console.log("Syncing Settings:", settings);

            // API Key
            const apiKeyInput = document.getElementById('api-key-input') as HTMLInputElement;
            if (apiKeyInput && settings.api_key) {
                apiKeyInput.value = settings.api_key;
            }

            // Model
            const modelSelect = document.getElementById('model-select') as HTMLSelectElement;
            // Note: HTML id might be 'setting-model' or 'model-select'. 
            // In index.html it was 'model-select' in my previous view (lines 1095).
            // But I also saw 'setting-model' in target content replace.
            // Let's try both or check. 'model-select' was in the large HTML block.
            if (modelSelect && settings.model_name) {
                // Try to match value.
                modelSelect.value = settings.model_name;
                // If value doesn't exist (e.g. custom), might default.
            }

            // Font Size (If available in settings)
            if (settings.font_size) {
                const range = document.getElementById('font-size-range') as HTMLInputElement;
                const label = document.getElementById('font-size-value');
                if (range) range.value = String(settings.font_size);
                if (label) label.innerText = settings.font_size + 'px';
                document.documentElement.style.setProperty('--chat-font-size', settings.font_size + 'px');
            }

            // Opacity
            if (settings.background_opacity !== undefined) {
                const range = document.getElementById('bg-opacity-range') as HTMLInputElement;
                const label = document.getElementById('bg-opacity-value');
                if (range) range.value = String(settings.background_opacity);
                if (label) label.innerText = settings.background_opacity + '%';
                // Apply opacity logic presumably exists elsewhere or we trigger input event?
                // Let's manually trigger change if needed, or just set style if we know it.
                // Assuming existing event listeners handle 'input'. 
                // We might need to dispatch event.
                if (range) range.dispatchEvent(new Event('input'));
            }
        }
    } catch (e) {
        console.error("Settings Sync Error:", e);
    }
    // Settings Save Logic (Mobile/Web)
    const settingsSaveBtn = document.getElementById('settings-save-btn');
    if (settingsSaveBtn) {
        settingsSaveBtn.addEventListener('click', async () => {
            const apiKeyInput = document.getElementById('api-key-input') as HTMLInputElement;
            const modelSelect = document.getElementById('model-select') as HTMLSelectElement;

            // Note: Font Size and Opacity inputs are checked inside 'input' events but we should save them too.
            // We need to grab them.
            const fontSizeRange = document.getElementById('font-size-range') as HTMLInputElement;
            const bgOpacityRange = document.getElementById('bg-opacity-range') as HTMLInputElement;

            const settings: any = {};

            if (apiKeyInput) settings.api_key = apiKeyInput.value.trim();
            if (modelSelect) settings.model_name = modelSelect.value;
            if (fontSizeRange) settings.font_size = parseInt(fontSizeRange.value);
            if (bgOpacityRange) settings.background_opacity = parseInt(bgOpacityRange.value);

            console.log("Saving settings:", settings);

            try {
                await api.save_settings(settings);
                alert("設定を保存しました。");

                // Close Modal
                const settingsModal = document.getElementById('settings-modal');
                if (settingsModal) settingsModal.style.display = 'none';

            } catch (e) {
                console.error("Save failed:", e);
                alert("保存に失敗しました。");
            }
        });
    }
});

// --- Vision Feature (Phase 35) ---
window.addEventListener('DOMContentLoaded', () => {
    const visionBtn = document.getElementById('vision-btn');
    const chatInput = document.getElementById('chat-input') as HTMLTextAreaElement;

    if (visionBtn) {
        visionBtn.addEventListener('click', async () => {
            // Resume Audio
            if (!audioCtx) {
                // @ts-ignore
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') audioCtx.resume();

            const message = chatInput ? chatInput.value.trim() : "";
            if (chatInput) chatInput.value = "";

            // UI Feedback
            addLog(message || "(画面を見て)", 'user');
            const thinkingId = addLog('画像を確認中... (Vision)', 'ai', true);
            updateStatus("Viewing...", true);

            try {
                // Call API
                const response = await api.chat_with_vision(message);

                removeLog(thinkingId);
                updateStatus("Active", true);

                let text = "";
                let audio = null;
                let suggestions: string[] = [];

                if (typeof response === 'string') {
                    text = response;
                } else {
                    text = response.text;
                    audio = response.audio;
                    suggestions = response.suggestions || [];
                }

                processAIResponse(text, audio);
                // @ts-ignore
                if (typeof updateSuggestions === 'function') updateSuggestions(suggestions);

            } catch (e: any) {
                removeLog(thinkingId);
                addLog("Error: " + e.message, 'ai');
                updateStatus("Error", false);
            }
        });
    }
});