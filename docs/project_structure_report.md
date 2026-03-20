# SoulMate Project Structure & Line Count Report

## Summary
- **Total Source Files**: ~40
- **Major Achievement**: `src/index.ts` successfully split into Managers. Current size: **85 lines**.
- **Largest File**: `src/css/style.css` (678 lines) - Reflects rich UI styling.
- **Second Largest**: `server.py` (641 lines) [WARNING] - Next Refactoring Target?

## Analysis
The **Frontend Refactoring Phase** is complete. The "God Object" `index.ts` has been dismantled into modular Managers (`UIManager`, `ChatManager`, `Live2DManager`, `LogManager`). This significantly improves maintainability.

The **Backend** `server.py` and `bubble_service.py` are growing larger and may need attention in the next phase.

## File Line Counts (Source Only)

### Frontend Core (`src/`)
- `index.ts`: 85 lines (Entry Point) [OPTIMIZED]
- `api_client.ts`: 230 lines
- `soul_bubble.ts`: 216 lines
- `settings.ts`: 96 lines
- `constants.ts`: 66 lines
- `types.d.ts`: 49 lines
- `index.html`: 173 lines
- `history.ts`: ~140 lines [NEW]
- `history.html`: ~200 lines [NEW]

### Frontend Managers (`src/managers/`) [NEW]
- `chat_manager.ts`: 397 lines (Chat, Audio, Vision)
- `ui_manager.ts`: 311 lines (DOM, Clock, Buttons)
- `live2d_manager.ts`: 512 lines (Model, Motion, LipSync) [UPDATED]
- `log_manager.ts`: 145 lines (Logging, Debug)
- `config_manager.ts`: 133 lines (Settings I/O)

### Styles
- `src/css/style.css`: 678 lines [Dark Mode / Animations]

### Backend Core (`src/services/`)
- `bubble_service.py`: 403 lines
- `ai_engine.py`: 308 lines (w/ JSON Fix)
- `calendar_manager.py`: 195 lines
- `voice_service.py`: 164 lines
- `memory_service.py`: 163 lines
- `active_engine.py`: 143 lines
- `memory_manager.py`: 122 lines
- `news_collector.py`: 121 lines
- `user_manager.py`: 116 lines
- `tts_engine.py`: 68 lines
- `persona_manager.py`: 66 lines
- `interest_manager.py`: 56 lines
- `metadata_fetcher.py`: 45 lines
- `history_manager.py`: 174 lines
- `db_manager.py`: ~160 lines [CORE]

### Backend API (`src/api/` & Root)
- [WARNING] `server.py`: 641 lines (FastAPI/SocketIO)
- `main.py`: 321 lines
- `src/api/chat_api.py`: ~400 lines
- `src/api/window_api.py`: ~70 lines
- `src/api/settings_api.py`: ~160 lines

### Documentation (`docs/`)
- `tasklist.md`: 532 lines
- `project_structure_report.md`: ~70 lines

## Recommendations for Next Phase

### 1. Refactor `server.py`
The `server.py` file is now the largest backend component (640+ lines).
- **Action**: Split routes into `src/routers/*.py`.
- **Method**: Use FastAPI `APIRouter` to modularize endpoints (e.g., `routers/chat.py`, `routers/settings.py`).

### 2. Refactor `bubble_service.py`
Growing large (400+ lines).
- **Action**: Consider splitting Generation logic and Scheduling/Event logic.

### 3. CSS Maintenance
`style.css` is large.
- **Action**: Consider splitting into `base.css`, `components.css`, `layout.css` if it grows further.

**Verdict**: Frontend Refactoring successful. Focus shifts to Backend Modularization.
