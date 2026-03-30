# FormaFix — AI-Powered Rehabilitation App

## 🏥 Overview

FormaFix is a comprehensive rehabilitation companion app that uses computer vision and AI to:
- **Plan**: AI agent creates personalized exercise plans based on injury assessment
- **Track**: Live video analysis with MediaPipe pose estimation
- **Coach**: Real-time feedback on exercise form and technique
- **Progress**: Track training history and visualize improvements

## 📋 Features

### App Pages:
1. **Authentication** — Sign up / Login with customer database
2. **Dashboard** — Welcome screen if no plan, or view current plan with progress
3. **Agent** — Conversational AI to assess injury and create personalized plan
4. **Training** — Live exercise session with real-time form feedback and rep counting
5. **Plans** — View all saved rehabilitation plans
6. **History** — View training sessions and exercise statistics

### Backend Integration:
- **Pose Estimation**: MediaPipe for joint angle tracking
- **Form Evaluation**: Clinical reference ranges for each exercise
- **Feedback Engine**: Real-time coaching cues
- **Rep Counter**: Intelligent repetition counting
- **Database**: SQLite for customers, plans, and training sessions
- **AI Provider**: Support for Anthropic Claude, Google Gemini, or local Ollama

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure AI Provider

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
# Choose one: anthropic, gemini, or ollama
AI_PROVIDER=gemini

# If using Gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# If using Anthropic
ANTHROPIC_API_KEY=your_api_key_here

# If using Ollama (local)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### 3. Run the App

```bash
python app.py
```

## 📚 Workflow

### First Time User:
1. **Sign Up** → Create account with email/password
2. **Dashboard** → See welcome page
3. **Agent** → Answer 4-6 questions about your injury
4. **Plan Review** → AI creates personalized 4-week plan
5. **Training** → Start first exercise session
6. **Track Progress** → View history and statistics

### Returning User:
1. **Login** → Access account
2. **Dashboard** → See current plan and recent progress
3. **Training** → Continue with next exercise
4. **History** → Review past sessions

## 🏋️ Supported Exercises

### ACL Rehabilitation:
- Straight Leg Raise
- Terminal Knee Extension
- Mini Squat
- Hamstring Curl

### Shoulder Rehabilitation:
- Pendulum
- External Rotation
- Wall Slide
- Shoulder Abduction

## 🗄️ Database Schema

### customers
- id, name, email, password (hashed), age, created_at

### plans
- id, customer_id, injury_type, pain_level, goal, plan_json, created_at

### training_sessions
- id, customer_id, plan_id, week, day, exercise_name, score, reps, created_at

## 🔧 Technical Architecture

### Services:
- **AuthService** — User authentication
- **DatabaseService** — Data persistence
- **PlanService** — Plan creation with AI agent
- **TrainingService** — Real-time pose estimation and feedback

### Engines:
- **FeedbackEngine** — Real-time coaching cues
- **FormEvaluator** — Form scoring (0-100)
- **RepCounter** — Rep detection using angle thresholds
- **AngleCalculator** — Joint angle computation

## 🎯 AI Agent Prompt

The AI agent asks about:
- Injury type and location
- Date of injury
- Surgery (yes/no, when)
- Current pain level (1-10)
- Previous rehabilitation
- Goals

Then generates a JSON plan with:
- Patient assessment
- 4-week progression
- Exercise details (sets, reps, rest)
- Phase descriptions

## 📊 Form Scoring

Each exercise is scored 0-100 based on:
- Target angle accuracy
- Tolerance ranges (clinical standards)
- Progressive difficulty tiers

**Score Interpretation:**
- 90-100: Great form!
- 75-89: Almost there!
- 50-74: Fix your form!
- 0-49: Stop — incorrect position!

## 🎥 Video Recording

Training sessions can record video to:
- Review form after session
- Track progress visually
- Share with physical therapist

Videos saved to: `training_videos/`

## ⚙️ API Providers

### Google Gemini (Recommended Free Tier)
- Fast responses
- 2M requests/month free tier
- [Get API Key](https://makersuite.google.com/app/apikey)

### Anthropic Claude
- High quality reasoning
- Paid API
- [Get API Key](https://console.anthropic.com/)

### Ollama (Local, No API Key)
- Fully private
- Requires local installation
```bash
ollama pull llama3
ollama serve
```

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'flet'"
```bash
pip install flet
```

### "AI_PROVIDER not configured"
Create `.env` file with your provider settings

### "Cannot connect to Ollama"
Make sure Ollama is running: `ollama serve`

### "Camera/MediaPipe errors"
- Ensure webcam permissions are granted
- Check MediaPipe model download: `pose_landmarker_lite.task`

## 📖 API Reference

### AuthService
```python
from auth_service import AuthService
auth = AuthService()
success, msg, customer_id = auth.register(name, email, password, age)
success, msg, customer = auth.login(email, password)
```

### DatabaseService
```python
from database_service import DatabaseService
db = DatabaseService()
db.create_customer(name, email, password, age)
db.create_plan(customer_id, plan_data)
db.save_training_session(session_data)
db.get_training_history(customer_id, limit=10)
```

### PlanService
```python
from plan_service import PlanService
ps = PlanService()
initial_msg = ps.start_plan_creation(patient_name)
response, plan_json = ps.continue_conversation(user_message)
plan_id = ps.save_plan(customer_id, plan_data)
```

### TrainingSession
```python
from training_service import TrainingSession
session = TrainingSession("bicep_curl", target_reps=10)
result = session.process_frame(frame)  # Returns dict with feedback, score, etc
summary = session.get_session_summary()
```

## 📝 File Structure

```
FormaFix/
├── app.py                    # Main Flet app
├── auth_service.py          # User authentication
├── database_service.py       # SQLite database
├── plan_service.py          # AI plan generation
├── training_service.py      # Pose estimation & feedback
├── feedback_engine.py       # Real-time coaching cues
├── form_evaluator.py        # Form scoring
├── rep_counter.py           # Rep detection
├── angle_calculator.py      # Joint angle computation
├── ai_client.py             # AI provider integration
├── exercise_selector.py     # Exercise metadata
├── plan_generator.py        # Fallback plan generation
├── pose_estimation.py       # MediaPipe setup
├── audio_feedback.py        # Text-to-speech
├── requirements.txt         # Python dependencies
├── formafix.db             # SQLite database (auto-created)
└── README.md               # This file
```

## 🔐 Security

- Passwords are hashed with SHA-256
- No plain-text credentials stored
- API keys stored in `.env` (not in git)
- Database is local SQLite

## 📱 Cross-Platform

FormaFix works on:
- Windows
- macOS
- Linux
- Web (Flet web)

## 🤝 Contributing

Improvements welcome! Areas:
- More exercises
- Advanced pose tracking
- Video recording
- Social sharing
- Trainer dashboard

## 📄 License

FormaFix is commercial rehabilitation software. All rights reserved.

## 👨‍⚕️ Medical Disclaimer

FormaFix is a training tool and does NOTREPLACEMENT for professional medical advice. Always consult a licensed physical therapist before starting rehabilitation.

---

**Questions?** Check the troubleshooting section or review the code comments.
