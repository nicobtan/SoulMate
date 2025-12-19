# SoulMate Project Structure & Line Count Report

## Summary
- **Total Source Files**: ~40
- **Largest File**: `src/index.ts` (1525 lines) [CRITICAL]
- **Second Largest**: `server.py` (580 lines) [WARNING]

## Analysis
The folder structure is generally well-organized (Service-oriented architecture + API Mixins). However, the **Frontend Entry Point (`index.ts`)** has become a "God Object," handling initialization, UI events, Live2D logic, and debug logging.

## File Line Counts (Source Only)

### Frontend (`src/`)
- [CRITICAL] `index.ts`: 1525 lines (Requires Splitting)
- `settings.html`: 564 lines
- `api_client.ts`: 210 lines
- `soul_bubble.ts`: 176 lines
- `index.html`: 173 lines
- `settings.ts`: 85 lines
- `types.d.ts`: 41 lines

### Backend Core (`src/services/`)
- `ai_engine.py`: 217 lines
- `calendar_manager.py`: 176 lines
- `voice_service.py`: 151 lines
- `memory_service.py`: 144 lines
- `memory_manager.py`: 116 lines
- `news_collector.py`: 113 lines
- `user_manager.py`: 104 lines
- `persona_manager.py`: 60 lines
- `tts_engine.py`: 58 lines
- `interest_manager.py`: 50 lines
- `metadata_fetcher.py`: 43 lines
- `history_manager.py`: 166 lines

### Backend API (`src/api/` & Root)
- [WARNING] `server.py`: 580 lines
- `main.py`: 287 lines
- `src/api/chat_api.py`: ~400 lines
- `src/api/window_api.py`: 66 lines
- `src/api/base.py`: 23 lines

### Documentation (`docs/`)
- `tasklist.md`: 532 lines
- `realtime_reaction_spec.md`: 49 lines
- `fix_name_placeholder.md`: 56 lines

## Recommendations for Refactoring

### 1. Split `src/index.ts`
This file is too large and risky to maintain. Suggest splitting into:
- `src/managers/ui_manager.ts`: Handling DOM elements and generic UI toggle logic.
- `src/managers/event_manager.ts`: Central event bus or listener setup.
- `src/managers/live2d_manager.ts`: Move more Live2D logic here completely.

### 2. Modularize `server.py`
If `server.py` contains many route definitions, verify if they can be moved to `src/routers/` using FastAPI's `APIRouter` (if used) or separate blueprints.

### 3. Folder Structure Check
The current structure is **Good**.
- `src/services/`: Clear separation of business logic.
- `src/api/`: Mixins for desktop app API.
- `dist/`: Build artifacts.

**Verdict**: Focus strictly on splitting `src/index.ts` in the near future.
