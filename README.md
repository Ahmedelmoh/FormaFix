# FormaFix — AI-Powered Physiotherapy Assistant

Real-time rehabilitation exercise tracking using MediaPipe pose estimation
and an AI backend (Gemini / Claude / Ollama).

---

## Project Structure

```
formafix/
├── ai_client.py          # Unified AI provider (Gemini / Anthropic / Ollama)
├── angle_calculator.py   # Joint angle computation from MediaPipe landmarks
├── audio_feedback.py     # Non-blocking TTS feedback
├── exercise_selector.py  # CLI exercise menu (standalone mode)
├── feedback_engine.py    # Rule-based coaching cues per exercise
├── form_evaluator.py     # Form scoring 0–100 vs clinical reference angles
├── plan_generator.py     # (reserved for future use)
├── pose_estimation.py    # Standalone: one exercise at a time
├── progress_agent.py     # AI-generated post-session summary
├── rehab_agent.py        # AI-driven intake interview → plan.json
├── rep_counter.py        # State-machine rep counter
├── session_runner.py     # Full session: reads plan.json, runs all exercises
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your AI provider

```bash
cp .env.example .env
# Edit .env and fill in your API key
```

### 3a. Standalone mode (one exercise)

```bash
python pose_estimation.py
```

### 3b. Full rehab plan mode

```bash
# Step 1 — generate a personalised plan
python rehab_agent.py

# Step 2 — run today's session
python session_runner.py
```

---

## Supported Exercises

| # | Exercise | Target Joint |
|---|----------|-------------|
| 1 | Straight Leg Raise | Hip |
| 2 | Terminal Knee Extension | Knee |
| 3 | Mini Squat | Knee |
| 4 | Hamstring Curl | Knee |
| 5 | Pendulum | Shoulder |
| 6 | External Rotation | Elbow |
| 7 | Wall Slide | Shoulder |
| 8 | Shoulder Abduction | Shoulder |

---

## AI Providers

| Provider | Env var | Notes |
|----------|---------|-------|
| `gemini` | `GEMINI_API_KEY` | Default; free tier available |
| `anthropic` | `ANTHROPIC_API_KEY` | Claude models |
| `ollama` | — | Local; run `ollama serve` first |

Set `AI_PROVIDER` in `.env` to switch.

---

## Controls (during exercise)

| Key | Action |
|-----|--------|
| Q | Quit / skip to next exercise |
| R | Reset rep counter |
