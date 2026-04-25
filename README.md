# FormaFix 🏋️‍♂️🤖

> **AI-Based Physical Therapy and Exercise Monitoring System**
> An intelligent rehabilitation companion that combines computer vision, large language models, and biomechanical analysis to deliver personalized, real-time physical therapy — without any wearable equipment.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.21-FF6F00?logo=tensorflow&logoColor=white)](https://www.tensorflow.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Pose-00C853?logo=google&logoColor=white)](https://developers.google.com/mediapipe)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.13-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Anthropic](https://img.shields.io/badge/Claude-Anthropic-D97757?logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Overview

**FormaFix** is an end-to-end AI-driven physiotherapy platform that helps patients recover from musculoskeletal injuries — with a primary focus on **ACL (Anterior Cruciate Ligament) rehabilitation** — through real-time pose tracking, intelligent form evaluation, and adaptive treatment planning.

The system replaces the need for constant in-person supervision by acting as a virtual rehabilitation coach. It captures the patient's movement through a standard webcam, analyzes biomechanics using deep learning–based pose estimation, evaluates the quality of every repetition, and dynamically adjusts the treatment plan using a large language model (Claude / OpenAI GPT) that reasons over clinical protocols.

The clinical knowledge base is grounded in evidence-based protocols, including:

- **MGH ACL Rehabilitation Protocol (2024)**
- **MOON Knee Group ACL Rehabilitation Program**
- **Benha University Rehabilitation Guidelines (2022)**

---

## ✨ Key Features

- 🧠 **AI Rehab Agent** — Conducts a structured clinical interview (injury type, surgery date, pain level, ROM, swelling) and generates a fully personalized rehabilitation plan.
- 🎥 **Real-Time Pose Estimation** — Uses Google's MediaPipe Pose Landmarker to extract 33 3D body landmarks at high frame rates.
- 📐 **Biomechanical Angle Calculation** — Computes joint angles (knee flexion, hip flexion, ankle dorsiflexion, etc.) frame by frame for objective form analysis.
- 🏃 **Repetition Counter** — Automatically detects and counts valid reps based on motion thresholds and rep cadence.
- ✅ **Form Evaluator** — Compares each rep against ideal biomechanical ranges and flags compensations or unsafe movement patterns.
- 🔊 **Real-Time Audio Feedback** — Provides instant verbal cues using offline TTS (`pyttsx3`) so patients can train hands-free.
- 📊 **Progress Summary** — Aggregates session data and generates progress reports across reps, sets, and rehab phases.
- 🔁 **Adaptive Planning** — The agent re-evaluates patient progress after each session and adjusts intensity, volume, or exercise selection automatically.
- 💤 **Rest Day Recommendations** — AI-generated tips for active recovery on non-training days.
- 🌐 **REST API (FastAPI)** — All capabilities are exposed as HTTP endpoints, making the system embeddable in mobile or web clients.
- 🖥️ **Cross-Platform UI (Flet)** — A modern, Flutter-powered desktop/mobile interface for patient interaction.

---

## 🏗️ System Architecture

```
                    ┌─────────────────────────────────────────┐
                    │            Patient (Webcam)             │
                    └────────────────────┬────────────────────┘
                                         │  RGB Frames
                                         ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                       PERCEPTION LAYER                               │
   │   pose_estimation.py  ──▶  MediaPipe Pose Landmarker (33 keypoints)  │
   │   angle_calculator.py ──▶  Joint angles (knee, hip, ankle, …)        │
   └────────────────────────────┬─────────────────────────────────────────┘
                                ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                       ANALYSIS LAYER                                 │
   │   rep_counter.py      ──▶  Repetition detection                      │
   │   form_evaluator.py   ──▶  Movement quality scoring                  │
   │   feedback_engine.py  ──▶  Cue generation (text + audio)             │
   └────────────────────────────┬─────────────────────────────────────────┘
                                ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                        REASONING LAYER (LLM)                         │
   │   ai_client.py        ──▶  Anthropic Claude / OpenAI provider        │
   │   rehab_agent.py      ──▶  Diagnosis + plan generation               │
   │   plan_generator.py   ──▶  Phase-aware exercise scheduling           │
   │   adaptive_plan.py    ──▶  Post-session plan refinement              │
   │   progress_summary.py ──▶  Longitudinal progress reporting           │
   └────────────────────────────┬─────────────────────────────────────────┘
                                ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                       INTERFACE LAYER                                │
   │   server.py (FastAPI) │ app.py (Flet UI) │ main.py (CLI entry point) │
   └──────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

| Module | Description |
|---|---|
| `main.py` | CLI entry point — orchestrates the full rehab workflow (new patient → session → summary → adaptive plan). |
| `app.py` | Flet-based graphical user interface for end-users. |
| `server.py` | FastAPI server exposing the system as a REST API. |
| `api_client.py` | HTTP client for consuming the FormaFix API from external apps. |
| `ai_client.py` | Unified LLM client supporting Anthropic Claude and OpenAI providers. |
| `rehab_agent.py` | Clinical reasoning agent — interviews the patient and generates a rehab plan grounded in ACL protocols. |
| `plan_generator.py` | Builds phase-specific exercise plans (Phase 1–4) based on time-since-injury and clinical state. |
| `adaptive_plan.py` | Updates the active plan based on the latest session performance. |
| `exercise_selector.py` | Chooses appropriate exercises per phase, respecting the *no-equipment* constraint. |
| `pose_estimation.py` | MediaPipe-based 3D pose landmark extraction. |
| `pose_landmarker.task` | Pre-trained MediaPipe pose model weights. |
| `angle_calculator.py` | Computes joint angles from 3D landmarks. |
| `rep_counter.py` | Detects and counts valid repetitions. |
| `form_evaluator.py` | Scores movement quality against ideal biomechanical ranges. |
| `feedback_engine.py` | Generates corrective cues from form-evaluation output. |
| `audio_feedback.py` | Offline text-to-speech delivery via `pyttsx3`. |
| `session_runne.py` | Runs an end-to-end live training session. |
| `progress_summary.py` | Aggregates and reports patient progress. |
| `rest_day_tips.py` | LLM-generated active recovery recommendations. |
| `requirements.txt` | Python dependency manifest. |
| `.env.example` | Template for environment variables (API keys, model selection). |

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10 or higher
- A working **webcam**
- An API key for **Anthropic Claude** *or* **OpenAI** (set in `.env`)
- Windows / macOS / Linux (some audio dependencies are Windows-specific via `pywin32`)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Ahmedelmoh/FormaFix.git
cd FormaFix

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Then open .env and add your ANTHROPIC_API_KEY (or OPENAI_API_KEY)
```

### Running the CLI

```bash
python main.py
```

You will be greeted with the interactive menu:

```
==================================================
 FormaFix — AI Physical Therapy
==================================================

 1. New Patient (generate rehab plan)
 2. Start Session (follow today's plan)
 3. View Summary (last session report)
 4. Adaptive Plan (update plan by AI)
 5. Exit
```

### Running the API Server

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at `http://localhost:8000/docs`.

### Running the Desktop App

```bash
python app.py
```

---

## 🧪 Typical Workflow

1. **Onboarding** — The Rehab Agent interviews the patient (injury type, surgery date, current pain level 1–10, range of motion, swelling).
2. **Plan Generation** — A phase-aware plan (Phase 1: 0–2 weeks → Phase 4: return-to-sport) is produced and persisted to `plan.json`.
3. **Live Session** — The webcam is activated; pose estimation, rep counting, and form evaluation run in real time with audio feedback.
4. **Progress Logging** — Each rep, set, and session metric is stored in `session_data.json`.
5. **Adaptive Update** — After the session, the LLM reviews performance and adjusts the next day's plan (intensity, volume, or exercise swaps).

---

## 🧩 Tech Stack

| Layer | Technologies |
|---|---|
| **Computer Vision** | MediaPipe Pose Landmarker, OpenCV |
| **Deep Learning** | TensorFlow 2.21, Keras 3.13 |
| **Classical ML** | scikit-learn, SciPy, NumPy, Pandas |
| **LLM Reasoning** | Anthropic Claude (`anthropic` SDK), OpenAI-compatible providers |
| **API Layer** | FastAPI, Uvicorn, Starlette, Pydantic v2 |
| **UI** | Flet (Flutter for Python) |
| **Audio** | `pyttsx3` (offline TTS), `sounddevice` |
| **Visualization** | Matplotlib, Seaborn |
| **Tooling** | pytest, python-dotenv, rich |

---

## 🔐 Environment Variables

Create a `.env` file (see `.env.example`) and configure:

```env
# Choose your LLM provider: "anthropic" or "openai"
PROVIDER=anthropic

# API credentials
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional model overrides
ANTHROPIC_MODEL=claude-sonnet-4-5
OPENAI_MODEL=gpt-4o-mini
```

> ⚠️ **Never commit your `.env` file.** It is already excluded via `.gitignore`.

---

## 🗺️ Roadmap

- [ ] Mobile-native client (iOS / Android) via Flet packaging
- [ ] Cloud deployment with Docker + GPU inference
- [ ] Multi-injury support (rotator cuff, lower back, ankle sprain)
- [ ] Patient dashboard with longitudinal analytics
- [ ] Tele-rehab mode with clinician oversight
- [ ] Integration with wearable IMU sensors for fused estimation
- [ ] HIPAA-compliant data storage layer

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Commit your changes with clear messages.
4. Open a Pull Request describing the motivation and changes.

For major changes, please open an issue first to discuss what you would like to change.

---

## ⚠️ Medical Disclaimer

FormaFix is a **research and educational tool** designed to assist with physical therapy. It is **not a substitute for professional medical advice, diagnosis, or treatment**. Always consult a licensed physician or physical therapist before starting any rehabilitation program.

---

## 📜 License

This project is released under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 👥 Authors & Acknowledgments

Developed by the **FormaFix Team** as a graduation / research project in AI-assisted physical rehabilitation.

Special thanks to the authors of the **MGH ACL Rehabilitation Protocol**, the **MOON Knee Group**, and **Benha University** for the open clinical guidelines that grounded this work.

---

<p align="center">
  <i>Recover smarter. Train safer. Move better.</i> 💪
</p>
