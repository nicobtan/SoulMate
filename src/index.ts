export { }; // Ensure this file is treated as a module

import { Live2DModel } from 'pixi-live2d-display';

// Debug: Check Renderer
const userAgent = navigator.userAgent;
console.log('UserAgent:', userAgent);
if (userAgent.indexOf('Edg') === -1) {
    console.warn('Warning: Not using Edge Chromium? Transparency might fail.');
}

declare global {
    var PIXI: any;
}

// --- Type Definitions for Globals ---
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

// Global reference to Model for LipSync
let live2dModel: any = null;
let audioCtx: AudioContext | null = null;
const suggestionToggleBtn = document.getElementById('suggestion-toggle-btn');
const suggestionPopup = document.getElementById('suggestion-popup');

// --- Lip Sync Logic ---
function playAudioWithLipSync(url: string) {
    if (!live2dModel) {
        new Audio(url).play();
        return;
    }

    const audio = new Audio(url);
    audio.crossOrigin = "anonymous";

    if (!audioCtx) {
        // @ts-ignore
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }

    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }

    const source = audioCtx.createMediaElementSource(audio);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);
    analyser.connect(audioCtx.destination);

    audio.play().catch((e: any) => console.error("Audio play failed:", e));

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    let currentMouthY = 0; // Current smoothed value

    const updateLip = () => {
        if (audio.paused || audio.ended) {
            if (live2dModel && live2dModel.internalModel && live2dModel.internalModel.coreModel) {
                // Smoothly close? Nah, just snap to 0 for end is fine, or fast decay.
                // Let's snap to 0 to ensure closure.
                live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', 0);
            }
            return;
        }

        requestAnimationFrame(updateLip);
        analyser.getByteFrequencyData(dataArray);

        let sum = 0;
        // Optimization: Check mostly low-mid freq? Nah, standard avg is fine for voice.
        for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
        let average = sum / bufferLength;

        // --- Sensitivity Tuning ---
        // RMS-like behavior: 
        // 0-255 is byte data.
        // Sensitivity: / 60 feels right based on tuning.
        let targetOpenAmount = (average / 60);

        // Noise Gate
        if (targetOpenAmount < 0.1) targetOpenAmount = 0;
        // Cluster to Max
        if (targetOpenAmount > 1.0) targetOpenAmount = 1.0;

        // --- Smoothing (Lerp) ---
        // val = current + (target - current) * factor
        // factor 0.3 = 30% towards target per frame.
        const smoothing = 0.3;
        currentMouthY += (targetOpenAmount - currentMouthY) * smoothing;

        if (live2dModel && live2dModel.internalModel && live2dModel.internalModel.coreModel) {
            live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', currentMouthY);
        }
    };

    audio.onplay = () => updateLip();
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
if (forceTalkBtn) {
    forceTalkBtn.addEventListener('click', () => triggerForceTalk());
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

    // 2. Call Backend
    if (window.pywebview && window.pywebview.api) {
        try {
            const response = await window.pywebview.api.force_talk();

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
    } else {
        removeLog(thinkingId);
        addLog('Debug: Force Talk Triggered (No Backend)', 'ai');
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
    suggestionToggleBtn.addEventListener('click', () => {
        const isVisible = suggestionPopup.style.display === 'flex';
        suggestionPopup.style.display = isVisible ? 'none' : 'flex';
    });
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
    if (window.pywebview && window.pywebview.api) {
        try {
            const response = await window.pywebview.api.chat(message);
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
    } else {
        removeLog(thinkingId);
        addLog('Error: Backend not connected.', 'ai');
        updateStatus("Offline", false);
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
// Load basic settings for appearance (Font/Opacity)
async function loadSettings() {
    if (window.pywebview && window.pywebview.api) {
        try {
            const settings = await window.pywebview.api.get_settings();
            if (bgOpacityRange) updateBackgroundOpacity(settings.background_opacity || 0);

            // Apply opacity directly if helper or range is missing (though range exists in DOM?)
            // Actually ranges are missing from index.html now, so we need to just apply styles.
            const opacity = (settings.background_opacity || 0) / 100 * 0.4;
            const characterAreaBg = document.getElementById('character-area');
            if (characterAreaBg) {
                if (settings.background_opacity === 0) {
                    characterAreaBg.style.backgroundColor = 'transparent';
                } else {
                    characterAreaBg.style.backgroundColor = `rgba(255, 255, 255, ${opacity.toFixed(2)})`;
                }
            }

            if (settings.font_size) {
                document.documentElement.style.setProperty('--chat-font-size', settings.font_size + 'px');
            }
        } catch (err) {
            console.error("Failed to load settings:", err);
        }
    }
}
window.addEventListener('pywebviewready', loadSettings);

// Open Settings Window
if (settingsButton) {
    settingsButton.addEventListener('click', function () {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.open_settings();
        }
    });
}

// Prevent drag when clicking on settings modal (Stop EasyDrag)
if (settingsModal) {
    settingsModal.addEventListener('mousedown', (e) => {
        e.stopPropagation();
    });
    // Also stop propagation for children inputs to be safe
    const inputs = settingsModal.querySelectorAll('input, button');
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
    chatWidth: 350, // width + margin
    logWidth: 410, // width 400 + margin 10
    isChatOpen: false,
    isLogOpen: false
};

const leftPanel = document.getElementById('left-panel') as HTMLElement;
// rightPanel is already defined above
const debugContent = document.getElementById('debug-content');

// --- Chat Toggle Logic ---
if (chatToggleBtn && rightPanel) {
    chatToggleBtn.addEventListener('click', async () => {
        uiState.isChatOpen = !uiState.isChatOpen;
        rightPanel.classList.toggle('open', uiState.isChatOpen);
        chatToggleBtn.classList.toggle('active', uiState.isChatOpen);

        if (window.pywebview && window.pywebview.api) {
            try {
                // Margin Logic: 
                // Right Panel CSS has margin-left: 40px. Width 350. Total 390.
                const chatTotalWidth = 390;

                let w = uiState.charWidth;
                if (uiState.isLogOpen) w += uiState.logWidth;
                if (uiState.isChatOpen) w += chatTotalWidth;

                await window.pywebview.api.resize_window(w, 500);
            } catch (err) {
                console.error("Resize failed:", err);
            }
        }
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

// --- Debug/Log Toggle Logic ---
const debugBtn = document.getElementById('debug-btn');
const closeDebugBtn = document.getElementById('close-debug');

async function toggleLogPanel() {
    if (!leftPanel || !window.pywebview || !window.pywebview.api) return;

    const wasOpen = uiState.isLogOpen;
    uiState.isLogOpen = !wasOpen;

    leftPanel.classList.toggle('open', uiState.isLogOpen);

    try {
        const { x, y } = await window.pywebview.api.get_window_pos();
        // Width calculation
        const chatTotalWidth = 390;
        let baseW = uiState.charWidth + (uiState.isChatOpen ? chatTotalWidth : 0);

        if (uiState.isLogOpen) {
            // OPENING: Move Left, Resize Width +
            // Move Left by LogWidth
            await window.pywebview.api.move_window(x - uiState.logWidth, y);
            await window.pywebview.api.resize_window(baseW + uiState.logWidth, 500);
        } else {
            // CLOSING: Resize Width -, Move Right
            // Move back to original pos
            await window.pywebview.api.move_window(x + uiState.logWidth, y);
            await window.pywebview.api.resize_window(baseW, 500);
        }
    } catch (e) {
        console.error("Log Toggle Failed", e);
    }
}

if (debugBtn) debugBtn.addEventListener('click', toggleLogPanel);
if (closeDebugBtn) closeDebugBtn.addEventListener('click', toggleLogPanel);

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

        // Insert Canvas INSIDE the character area (behind button)
        const canvas = app.view as HTMLCanvasElement;
        characterArea.appendChild(canvas);

        // Ensure menu is top
        if (menu) menu.style.zIndex = "4000";

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

        const model = await ModelClass.from(modelPath);

        app.stage.addChild(model);

        // Expose model to global scope for LipSync
        live2dModel = model;

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
        model.y = (frameH * 0.4) - (model.height * 0.15); // Adjust Y to bring face down to view

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