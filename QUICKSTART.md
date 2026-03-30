# FormaFix — Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies (3 min)

Open terminal/PowerShell in the FormaFix directory:

```bash
pip install -r requirements.txt
```

### Step 2: Configure AI (1 min)

**Option A: Use Google Gemini (Recommended - Free)**

1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Open `.env` file and paste it:
   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_key_here
   ```

**Option B: Use Anthropic Claude (Paid)**

1. Go to: https://console.anthropic.com/
2. Get your API key
3. Edit `.env`:
   ```
   AI_PROVIDER=anthropic
   ANTHROPIC_API_KEY=your_key_here
   ```

**Option C: Use Local Ollama (Free, Offline)**

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3
ollama serve
```

Then edit `.env`:
```
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
```

### Step 3: Run the App (1 min)

```bash
python app.py
```

The Flet app will open in a window!

## 📱 How to Use

### First Time:

1. **Sign Up** — Create account with email/password
2. **Welcome** — You'll see the welcome page
3. **Create Plan** — Click "Create Plan with Agent"
   - Answer questions about your injury
   - AI will create 4-week personalized plan
4. **Training** — Go to "Start Training"
   - Select week and day
   - See exercises for that day
5. **Dashboard** — View your progress

### Returning Users:

1. **Login** with your email/password
2. **Dashboard** shows your current plan
3. Choose to train or view history

## 🏋️ Training Session

When you start training:
1. Select week and day
2. Camera opens (make sure it works)
3. Do the exercise while the app tracks your form
4. Real-time feedback appears on screen
5. App counts reps automatically
6. After session, see your score

## 💾 Your Data

Everything is saved to `formafix.db`:
- Your account info
- All plans created
- Every training session
- Progress history

## 🔑 API Keys (Security)

- `.env` contains your API keys
- **NEVER commit .env to Git** (it's in .gitignore)
- Keys are only used to call AI provider APIs
- Your data stays local in database

## 📋 Exercises Available

**Knee/ACL:**
- Straight Leg Raise
- Terminal Knee Extension
- Mini Squat
- Hamstring Curl

**Shoulder:**
- Pendulum
- External Rotation
- Wall Slide
- Shoulder Abduction

## ⚡ Pro Tips

1. **Use good lighting** for camera tracking
2. **Position camera** to see full body
3. **Move slowly** for better angle tracking
4. **Follow feedback** for better form
5. **Save plans** so you don't lose progress

## 🐛 Troubleshooting

### "flet not found"
```bash
pip install flet
```

### "AI_PROVIDER error"
Check your `.env` file has correct format:
```
AI_PROVIDER=gemini
GEMINI_API_KEY=sk_...
```

### "Camera not working"
- Check camera permissions
- Try different camera in settings
- Restart the app

### "Ollama connection error"
Make sure you ran: `ollama serve` in another terminal

## 📚 Learn More

- Full docs: `APP_README.md`
- Code structure: See comments in Python files
- API reference: Function docstrings

## 🎯 Example Workflow

```
Day 1:
├─ Sign up with email: john@example.com
├─ Get "Jump to our agent" welcome message
├─ Click "Create Plan with Agent"
├─ Answer: ACL surgery 2 months ago, pain level 4/10, goal is to walk normally
├─ AI creates personalized 4-week plan
├─ Save plan
├─ Go to dashboard, see the plan
├─ Start training on Week 1, Day 1
├─ Do exercises with video feedback
├─ See score: 82/100
└─ Plan saved to database

Day 2-28:
├─ Login
├─ Dashboard shows plan + recent session (82/100)
├─ Continue training on next days
├─ Watch score improve: 82 → 85 → 88 → 91
├─ View history of all sessions
└─ Complete 4-week plan successfully!
```

## 🎓 Next Steps

1. **Setup complete?** → Run `python app.py`
2. **Try demo?** → Create test account to explore
3. **Integrate camera?** → Training page uses your webcam
4. **Share feedback?** → Customize exercises in `exercise_selector.py`

---

**Ready?** Run `python app.py` and start rebuilding! 💪
