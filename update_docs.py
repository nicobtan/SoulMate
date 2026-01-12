
import os

path = r"c:\work\Soulmate\docs\tasklist.md"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the start of Phase 116
start_index = -1
for i, line in enumerate(lines):
    if "## Phase 116: Emotion Model Optimization (ONNX) [進行中]" in line:
        start_index = i
        break

if start_index != -1:
    # Truncate from here
    lines = lines[:start_index]

# Append new content
new_content = """## Phase 115: High-End Hearing (SoulMateEars) [完了] (2026-01-11)
- [x] **SoulMateEars 実装**
    - [x] `faster-whisper` による高速ASR (`large-v3-turbo`)
    - [x] `webrtcvad` によるVAD (発話区間検出)
    - [x] `ActiveEngine` への統合とバックグラウンドスレッド化

## Phase 116: Emotion Model Optimization (ONNX) [完了] (2026-01-11)
- [x] **Dependencies**
    - [x] Add onnx, onnxruntime-gpu to requirements.txt
    - [x] Install packages
- [x] **Implementation**
    - [x] Create tools/convert_emotion_model.py (Export & Quantize)
    - [x] Create src/services/voice/onnx_emotion_recognizer.py (Inference)
- [x] **Verification**
    - [x] Run conversion and verify accuracy comparison

## Phase 117: Continuous Listening Mode [完了] (2026-01-12)
- [x] **Backend Implementation**
    - [x] `active_engine.py`: Listening Loop (Threaded)
    - [x] `voice_api.py`: `toggle_continuous_listening` API
- [x] **Frontend Implementation**
    - [x] Right-click logic on Mic button
    - [x] `setContinuousListening` frontend API
    - [x] Visual Feedback (`.mic-listening` CSS)
    - [x] Direct execution (No intermediate text input)
"""

lines.append(new_content)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("tasklist.md updated successfully.")
