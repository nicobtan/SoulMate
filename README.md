# SoulMate: Active AI Desktop Partner

**SoulMate** is an interactive desktop mascot application that combines Live2D visuals, Google Gemini AI, and various system integrations (Calendar, News, etc.) to provide a comforting and helpful partner on your screen.

## ✨ Features

- **Live2D Mascot**: A cute, animated character that follows your mouse and reacts to interactions.
- **AI Conversation**: Powered by Google Gemini. Remembers context and past conversations.
- **Google Calendar Integration**:
    - "Show me my schedule" (`[ACTION:OPEN_CALENDAR]`) -> Opens your Google Calendar.
    - "Add event" (`[ACTION:ADD_EVENT]`) -> Adds events directly to your calendar.
- **Active Intellect**:
    - **News Trigger**: Occasionally suggests news topics when idle.
    - **Auto-Auth**: Automatically handles Google API authentication in the background.
- **System Integration**:
    - **TTS (Text-to-Speech)**: Speaks responses using Google Cloud Neural voices.
    - **Window Control**: Resizable, draggable, and toggleable UI.

## 📂 Project Structure

Verified Refactored Structure (Dec 2025):

```text
src/
├── core/               # Low-level infrastructure
│   ├── config_manager.py
│   └── ...
├── services/           # Business Logic & External Integrations
│   ├── ai_engine.py    # Gemini API Wrapper
│   ├── active_engine.py# Idle/Trigger Logic
│   ├── calendar_manager.py # Google Calendar API
│   ├── memory_manager.py   # ChromaDB + JSONL Logging
│   ├── tts_engine.py       # Google Cloud TTS
│   └── ...
├── api/                # Application Layer (Main.py Mixins)
│   ├── window_api.py   # Window Resize/Move
│   ├── settings_api.py # Settings UI Bridge
│   └── chat_api.py     # Chat & Action Logic
└── ... (Frontend files: index.ts, html, etc.)
```

`main.py` is the entry point, orchestrating these modules via the Mixin pattern.

## 🚀 Getting Started (Windows)

### Prerequisites
- Python 3.10+
- Node.js & npm (for building frontend)
- Google Cloud Credentials (`google-credentials.json`, `client_secret.json`)

### Installation

1.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Node Dependencies:**
    ```bash
    npm install
    ```

3.  **Build Frontend:**
    ```bash
    npm run build
    ```
    (This compiles TypeScript to `dist/index.html` and `bundle.js`)

4.  **Run Application:**
    - Double-click `run.bat`
    - OR run `python main.py`

## 📖 Usage Guide

- **Right-Click Character**: Open Context Menu (Exit App).
- **Chat Button (Bottom-Right)**: Toggle Chat Window.
- **Settings Button (New!)**: Open Settings Modal (API Key, Voice, Persona).
- **Debug Log**: Toggle Debug Panel (Left side).

Enjoy your life with SoulMate!
