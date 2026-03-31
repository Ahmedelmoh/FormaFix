"""
server.py — FormaFix Backend
=============================
FastAPI server — persistent JSON storage + score fix + day tracking
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json, os, uuid, threading, time
from datetime import datetime
import cv2
import mediapipe as mp
import numpy as np

from session_runne import run_exercise, _ensure_model
from audio_feedback import AudioFeedback
from ai_client import ask_ai
from rehab_agent import SYSTEM_PROMPT

app = FastAPI(title="FormaFix API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ── JSON File Storage ─────────────────────────────────────────────────────────
DB_DIR        = "formafix_db"
os.makedirs(DB_DIR, exist_ok=True)
USERS_FILE    = os.path.join(DB_DIR, "users.json")
PLANS_FILE    = os.path.join(DB_DIR, "plans.json")
SESSIONS_FILE = os.path.join(DB_DIR, "sessions.json")

def _load(path: str):
    if not os.path.exists(path):
        return {} if path.endswith(("users.json", "plans.json")) else []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _save(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

agent_sessions: dict = {}

# ── Models ────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str; email: str; password: str; age: Optional[int] = None

class LoginRequest(BaseModel):
    email: str; password: str

class AgentStartRequest(BaseModel):
    patient_name: str

class AgentContinueRequest(BaseModel):
    session_id: str; message: str

class SavePlanRequest(BaseModel):
    customer_id: str; plan_json: dict

class SaveSessionRequest(BaseModel):
    customer_id: str; plan_id: int; week: int; day: int
    exercise_name: str; score: int; reps: int
    notes: Optional[str] = ""; video_path: Optional[str] = None

class MarkDayRequest(BaseModel):
    customer_id: str; plan_id: int; week: int; day: int

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/register")
def register(req: RegisterRequest):
    users = _load(USERS_FILE)
    if req.email in users:
        return {"success": False, "message": "Email already exists"}
    uid = str(uuid.uuid4())[:8]
    users[req.email] = {
        "id": uid, "name": req.name, "email": req.email,
        "password": req.password, "age": req.age,
    }
    _save(USERS_FILE, users)
    return {"success": True, "message": "Account created"}

@app.post("/login")
def login(req: LoginRequest):
    users = _load(USERS_FILE)
    user  = users.get(req.email)
    if not user or user["password"] != req.password:
        return {"success": False, "message": "Invalid email or password"}
    return {"success": True, "customer": user}

# ── Agent ─────────────────────────────────────────────────────────────────────
@app.post("/agent/start")
def agent_start(req: AgentStartRequest):
    sid     = str(uuid.uuid4())
    initial = f"Hi {req.patient_name}! Please choose your preferred language: Arabic or English?"
    agent_sessions[sid] = {
        "history": [{"role": "assistant", "content": initial}],
        "patient_name": req.patient_name, "plan": None,
    }
    return {"session_id": sid, "initial_message": initial}

@app.post("/agent/continue")
def agent_continue(req: AgentContinueRequest):
    import re
    session = agent_sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    session["history"].append({"role": "user", "content": req.message})
    response  = ask_ai(session["history"], system_prompt=SYSTEM_PROMPT)
    plan_json = None
    if "PLAN_READY" in response:
        m = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if m:
            try:
                plan_json = json.loads(m.group(1))
                session["plan"] = plan_json
            except Exception:
                pass
        clean    = re.sub(r"PLAN_READY", "", response)
        clean    = re.sub(r"```json.*?```", "", clean, flags=re.DOTALL).strip()
        response = clean or "✅ Your rehabilitation plan is ready!"
    session["history"].append({"role": "assistant", "content": response})
    return {"response": response, "plan_json": plan_json}

# ── Plans ─────────────────────────────────────────────────────────────────────
@app.post("/plans/save")
def save_plan(req: SavePlanRequest):
    plans   = _load(PLANS_FILE)
    plan_id = (max(int(k) for k in plans.keys()) + 1) if plans else 1
    patient = req.plan_json.get("patient", {})
    plans[str(plan_id)] = {
        "id": plan_id, "customer_id": req.customer_id,
        "plan": req.plan_json,
        "injury_type": patient.get("injury", "Unknown"),
        "pain_level":  patient.get("pain_level", "N/A"),
        "goal":        patient.get("goal", "Recovery"),
        "created_at":  datetime.now().isoformat(),
        "completed_days": [],   # e.g. ["W1D1", "W1D3"]
    }
    _save(PLANS_FILE, plans)
    return {"success": True, "plan_id": plan_id}

@app.get("/plans/latest/{customer_id}")
def get_latest_plan(customer_id: str):
    plans      = _load(PLANS_FILE)
    user_plans = [p for p in plans.values() if p["customer_id"] == customer_id]
    if not user_plans:
        return None
    return sorted(user_plans, key=lambda x: x["id"])[-1]

@app.get("/plans/all/{customer_id}")
def get_all_plans(customer_id: str):
    plans = _load(PLANS_FILE)
    return [p for p in plans.values() if p["customer_id"] == customer_id]

@app.post("/plans/mark_day")
def mark_day_complete(req: MarkDayRequest):
    """Mark week/day as done — prevents re-doing same day."""
    plans = _load(PLANS_FILE)
    key   = str(req.plan_id)
    if key not in plans or plans[key]["customer_id"] != req.customer_id:
        raise HTTPException(404, "Plan not found")
    entry = f"W{req.week}D{req.day}"
    if entry not in plans[key].get("completed_days", []):
        plans[key].setdefault("completed_days", []).append(entry)
        _save(PLANS_FILE, plans)
    return {"success": True, "completed_days": plans[key]["completed_days"]}

@app.get("/plans/next_day/{customer_id}/{plan_id}")
def get_next_day(customer_id: str, plan_id: int):
    """Return the next uncompleted training day."""
    plans = _load(PLANS_FILE)
    key   = str(plan_id)
    if key not in plans:
        raise HTTPException(404, "Plan not found")
    pdata          = plans[key]
    completed_days = set(pdata.get("completed_days", []))
    plan_content   = pdata["plan"].get("plan", pdata["plan"])
    weeks          = plan_content.get("weeks", [])

    for w in weeks:
        for d in w.get("days", []):
            exs = d.get("exercises", [])
            if not exs:
                continue
            entry = f"W{w.get('week',1)}D{d.get('day',1)}"
            if entry not in completed_days:
                return {
                    "week": w.get("week", 1), "day": d.get("day", 1),
                    "exercises": exs, "focus": w.get("focus", ""),
                }
    return {"week": None, "day": None, "exercises": [], "focus": "Plan complete!"}

# ── Sessions ──────────────────────────────────────────────────────────────────
@app.post("/sessions/save")
def save_session(req: SaveSessionRequest):
    sessions   = _load(SESSIONS_FILE)
    session_id = len(sessions) + 1
    sessions.append({
        "id":            session_id,
        "customer_id":   req.customer_id,
        "exercise":      req.exercise_name,
        "exercise_name": req.exercise_name,
        "score":         req.score,
        "reps":          req.reps,
        "week":          req.week,
        "day":           req.day,
        "notes":         req.notes,
        "date":          datetime.now().strftime("%Y-%m-%d"),
        "created_at":    datetime.now().isoformat(),
    })
    _save(SESSIONS_FILE, sessions)
    return {"success": True, "session_id": session_id}

@app.get("/sessions/history/{customer_id}")
def get_history(customer_id: str):
    sessions = _load(SESSIONS_FILE)
    return [s for s in sessions if s["customer_id"] == customer_id]

# ── Live Training ─────────────────────────────────────────────────────────────
@app.post("/training/live")
def live_training(
    exercise_name: str,
    target_reps:   int = 10,
    target_sets:   int = 3,
    injured_side:  str = "left",
):
    """Run camera + MediaPipe and return the real score."""
    BaseOptions           = mp.tasks.BaseOptions
    PoseLandmarker        = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode     = mp.tasks.vision.RunningMode

    model_path = _ensure_model()
    options    = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.IMAGE
    )
    audio = AudioFeedback()
    ex_info = {
        "name": exercise_name, "sets": target_sets,
        "reps": target_reps,   "rest_seconds": 30, "notes": "",
    }

    cap = cv2.VideoCapture(0)
    time.sleep(0.8)
    if not cap.isOpened():
        return {"success": False, "summary": {}, "error": "Cannot open camera"}
    for _ in range(15):
        ret, _ = cap.read()
        if ret:
            break
        time.sleep(0.1)

    result = {"avg_score": 0, "completed_sets": 0,
              "scores": [], "target_reps": target_reps}
    try:
        with PoseLandmarker.create_from_options(options) as lm:
            result = run_exercise(ex_info, lm, audio, cap, side=injured_side)
    except Exception as e:
        print(f"[ERROR] run_exercise: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    # ── Ensure avg_score is calculated ───────────────────────────────────────
    scores = result.get("scores", [])
    if scores:
        result["avg_score"] = round(float(np.mean(scores)))

    result["reps_completed"] = (
        target_reps
        if result.get("completed_sets", 0) >= target_sets
        else result.get("completed_sets", 0) * max(target_reps // target_sets, 1)
    )
    print(f"[Score] {exercise_name}: avg={result['avg_score']} "
          f"sets_done={result.get('completed_sets',0)} scores={scores}")
    return {"success": True, "summary": result}

# ── MJPEG Stream ──────────────────────────────────────────────────────────────
_stream_cap    = None
_stream_lock   = threading.Lock()
_stream_active = False

def _gen_frames():
    global _stream_cap, _stream_active
    while _stream_active:
        with _stream_lock:
            if _stream_cap is None or not _stream_cap.isOpened():
                break
            ret, frame = _stream_cap.read()
        if not ret:
            time.sleep(0.03); continue
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
               buf.tobytes() + b"\r\n")
        time.sleep(0.033)

@app.get("/camera/start")
def camera_start():
    global _stream_cap, _stream_active
    with _stream_lock:
        if _stream_cap is not None and _stream_cap.isOpened():
            _stream_active = True
            return {"success": True}
        cap = cv2.VideoCapture(0)
        time.sleep(0.5)
        if not cap.isOpened():
            return {"success": False, "message": "Cannot open camera"}
        _stream_cap = cap; _stream_active = True
    return {"success": True}

@app.get("/camera/stop")
def camera_stop():
    global _stream_cap, _stream_active
    _stream_active = False
    with _stream_lock:
        if _stream_cap is not None:
            _stream_cap.release(); _stream_cap = None
    return {"success": True}

@app.get("/camera/stream")
def camera_stream():
    global _stream_active
    if _stream_cap is None or not _stream_cap.isOpened():
        camera_start()
    _stream_active = True
    return StreamingResponse(
        _gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/health")
def health():
    return {"status": "ok", "server": "FormaFix API", "db": DB_DIR}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)