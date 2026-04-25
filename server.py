"""
server.py — FormaFix Backend
=============================
FastAPI server — persistent JSON storage + score fix + day tracking
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json, os, uuid, threading, time, base64, math
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

class WebTrainingStartRequest(BaseModel):
    exercise_name: str
    target_reps: int = 10
    target_sets: int = 1
    injured_side: str = "left"

class FrameRequest(BaseModel):
    image: str

# ── Browser Camera Training State ────────────────────────────────────────────
web_training_sessions: dict = {}
web_training_lock = threading.Lock()

_pose_landmarker = None
_pose_landmarker_lock = threading.Lock()

def _get_pose_landmarker():
    """Create one shared PoseLandmarker for frame-by-frame web inference."""
    global _pose_landmarker
    if _pose_landmarker is not None:
        return _pose_landmarker

    with _pose_landmarker_lock:
        if _pose_landmarker is not None:
            return _pose_landmarker

        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        model_path = _ensure_model()
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
        )
        _pose_landmarker = PoseLandmarker.create_from_options(options)
        return _pose_landmarker

def _calc_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Return angle ABC in degrees."""
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc))
    if denom == 0:
        return 0.0
    cos_v = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(math.degrees(math.acos(cos_v)))

def _extract_leg_angle(pose_landmarks, side: str) -> tuple[float, float]:
    """Extract hip-knee-ankle angle and average visibility for chosen side."""
    if side == "right":
        hip_i, knee_i, ankle_i = 24, 26, 28
    else:
        hip_i, knee_i, ankle_i = 23, 25, 27

    hip = pose_landmarks[hip_i]
    knee = pose_landmarks[knee_i]
    ankle = pose_landmarks[ankle_i]

    a = np.array([hip.x, hip.y], dtype=np.float32)
    b = np.array([knee.x, knee.y], dtype=np.float32)
    c = np.array([ankle.x, ankle.y], dtype=np.float32)
    angle = _calc_angle(a, b, c)
    visibility = float((hip.visibility + knee.visibility + ankle.visibility) / 3.0)
    return angle, visibility

def _build_web_summary(session: dict) -> dict:
    scores = session.get("scores", [])
    avg_score = round(float(np.mean(scores))) if scores else 0
    target_reps = int(session.get("target_reps", 10) or 10)
    target_sets = int(session.get("target_sets", 1) or 1)
    reps_completed = int(session.get("reps_completed", 0) or 0)
    completed_sets = min(target_sets, reps_completed // max(1, target_reps))
    return {
        "avg_score": avg_score,
        "completed_sets": completed_sets,
        "scores": scores,
        "target_reps": target_reps,
        "reps_completed": reps_completed,
    }

def _update_web_session(session: dict, angle: float, visibility: float) -> None:
    """Update rep-counting state from one analyzed frame."""
    if visibility < 0.45:
        session["tip"] = "Keep your full body visible in camera"
        return

    up_th = 155.0
    down_th = 120.0
    stage = session.get("stage", "up")

    if angle <= down_th and stage != "down":
        stage = "down"
    elif angle >= up_th and stage == "down":
        stage = "up"
        session["reps_completed"] = int(session.get("reps_completed", 0)) + 1

    center = (up_th + down_th) / 2.0
    radius = (up_th - down_th) / 2.0
    dist = min(abs(angle - center) / max(radius, 1e-6), 1.0)
    frame_score = int(round(100 - dist * 35))
    frame_score = max(45, min(100, frame_score))

    scores = session.setdefault("scores", [])
    scores.append(frame_score)
    if len(scores) > 250:
        del scores[0:len(scores) - 250]

    total_target_reps = max(1, int(session.get("target_reps", 10)) * int(session.get("target_sets", 1)))
    if session.get("reps_completed", 0) >= total_target_reps:
        session["finished"] = True

    session["stage"] = stage
    session["last_angle"] = round(angle, 1)
    session["tip"] = "Good form, keep controlled movement"

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

# ── Web Camera Training (User Camera) ────────────────────────────────────────
@app.post("/training/web/start")
def web_training_start(req: WebTrainingStartRequest):
        session_id = str(uuid.uuid4())
        with web_training_lock:
                web_training_sessions[session_id] = {
                        "exercise_name": req.exercise_name,
                        "target_reps": max(1, int(req.target_reps)),
                        "target_sets": max(1, int(req.target_sets)),
                        "injured_side": (req.injured_side or "left").lower(),
                        "reps_completed": 0,
                        "scores": [],
                        "stage": "up",
                        "tip": "Start camera and begin moving",
                        "last_angle": None,
                        "finished": False,
                        "created_at": datetime.now().isoformat(),
                }

        return {
                "success": True,
                "session_id": session_id,
                "camera_path": f"/training/webcam/{session_id}",
        }

@app.get("/training/webcam/{session_id}", response_class=HTMLResponse)
def web_training_camera_page(session_id: str):
        with web_training_lock:
                if session_id not in web_training_sessions:
                        raise HTTPException(404, "Training session not found")

        html = f"""
<!doctype html>
<html>
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>FormaFix Camera Trainer</title>
    <style>
        body {{ background: #0f172a; color: #e2e8f0; font-family: Segoe UI, sans-serif; margin: 0; padding: 16px; }}
        .box {{ max-width: 760px; margin: 0 auto; }}
        video {{ width: 100%; border-radius: 12px; background: #020617; }}
        .row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }}
        button {{ border: none; border-radius: 10px; padding: 12px 16px; font-weight: 600; cursor: pointer; }}
        .start {{ background: #22c55e; color: white; }}
        .finish {{ background: #3b82f6; color: white; }}
        .stop {{ background: #334155; color: #e2e8f0; }}
        .card {{ background: #1e293b; padding: 12px; border-radius: 10px; margin-top: 12px; }}
    </style>
</head>
<body>
    <div class=\"box\">
        <h2>FormaFix User Camera Training</h2>
        <p>This page uses your device camera and streams frames to AI processing.</p>
        <video id=\"video\" autoplay playsinline muted></video>
        <canvas id=\"canvas\" width=\"320\" height=\"240\" style=\"display:none\"></canvas>
        <div class=\"row\">
            <button class=\"start\" id=\"startBtn\">Start Camera</button>
            <button class=\"finish\" id=\"finishBtn\">Finish Exercise</button>
            <button class=\"stop\" id=\"stopBtn\">Stop Camera</button>
        </div>
        <div class=\"card\" id=\"status\">Waiting for camera...</div>
    </div>

    <script>
        const sessionId = \"{session_id}\";
        const video = document.getElementById("video");
        const canvas = document.getElementById("canvas");
        const ctx = canvas.getContext("2d");
        const statusBox = document.getElementById("status");
        let stream = null;
        let frameTimer = null;
        let pollTimer = null;

        async function postFrame() {{
            if (!video.videoWidth || !video.videoHeight) return;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const image = canvas.toDataURL("image/jpeg", 0.75);
            try {{
                await fetch(`/training/web/frame/${{sessionId}}`, {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ image }})
                }});
            }} catch (e) {{
                statusBox.textContent = "Frame upload error: " + e;
            }}
        }}

        async function pollStatus() {{
            try {{
                const res = await fetch(`/training/web/status/${{sessionId}}`);
                const data = await res.json();
                const reps = data.summary?.reps_completed ?? 0;
                const score = data.summary?.avg_score ?? 0;
                const tip = data.tip ?? "";
                statusBox.textContent = `Reps: ${{reps}} | Score: ${{score}}/100 | Tip: ${{tip}}`;
                if (data.finished) {{
                    statusBox.textContent += " | Target reached";
                }}
            }} catch (e) {{
                statusBox.textContent = "Status error: " + e;
            }}
        }}

        async function startCamera() {{
            stream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
            video.srcObject = stream;
            frameTimer = setInterval(postFrame, 120);
            pollTimer = setInterval(pollStatus, 450);
            statusBox.textContent = "Camera running...";
        }}

        async function finishExercise() {{
            const res = await fetch(`/training/web/finish/${{sessionId}}`, {{ method: "POST" }});
            const data = await res.json();
            const summary = data.summary || {{}};
            statusBox.textContent = `Finished. Reps: ${{summary.reps_completed || 0}}, Score: ${{summary.avg_score || 0}}/100`;
        }}

        function stopCamera() {{
            if (frameTimer) clearInterval(frameTimer);
            if (pollTimer) clearInterval(pollTimer);
            frameTimer = null;
            pollTimer = null;
            if (stream) {{
                stream.getTracks().forEach(t => t.stop());
            }}
            stream = null;
            statusBox.textContent = "Camera stopped";
        }}

        document.getElementById("startBtn").onclick = startCamera;
        document.getElementById("finishBtn").onclick = finishExercise;
        document.getElementById("stopBtn").onclick = stopCamera;
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html)

@app.post("/training/web/frame/{session_id}")
def web_training_frame(session_id: str, req: FrameRequest):
        with web_training_lock:
                session = web_training_sessions.get(session_id)
        if not session:
                raise HTTPException(404, "Training session not found")

        if not req.image or "," not in req.image:
                raise HTTPException(400, "Invalid image data")

        try:
                image_b64 = req.image.split(",", 1)[1]
                img_bytes = base64.b64decode(image_b64)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is None:
                        raise ValueError("Unable to decode frame")
        except Exception as exc:
                raise HTTPException(400, f"Bad frame payload: {exc}")

        try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                det = _get_pose_landmarker().detect(mp_image)
        except Exception as exc:
                raise HTTPException(500, f"Pose inference failed: {exc}")

        with web_training_lock:
                session = web_training_sessions.get(session_id)
                if not session:
                        raise HTTPException(404, "Training session not found")

                if det.pose_landmarks:
                        pose_landmarks = det.pose_landmarks[0]
                        angle, visibility = _extract_leg_angle(
                                pose_landmarks,
                                session.get("injured_side", "left"),
                        )
                        _update_web_session(session, angle, visibility)
                else:
                        session["tip"] = "No pose detected. Step back and center your body"

                summary = _build_web_summary(session)
                return {
                        "success": True,
                        "finished": bool(session.get("finished", False)),
                        "tip": session.get("tip", ""),
                        "summary": summary,
                }

@app.get("/training/web/status/{session_id}")
def web_training_status(session_id: str):
        with web_training_lock:
                session = web_training_sessions.get(session_id)
                if not session:
                        raise HTTPException(404, "Training session not found")
                return {
                        "success": True,
                        "finished": bool(session.get("finished", False)),
                        "tip": session.get("tip", ""),
                        "summary": _build_web_summary(session),
                }

@app.post("/training/web/finish/{session_id}")
def web_training_finish(session_id: str):
        with web_training_lock:
                session = web_training_sessions.get(session_id)
                if not session:
                        raise HTTPException(404, "Training session not found")
                session["finished"] = True
                summary = _build_web_summary(session)

        return {"success": True, "summary": summary}

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

_stream_cap = None
_stream_lock = threading.Lock()
_stream_active = False

def _gen_frames():
    global _stream_cap, _stream_active
    while _stream_active:
        with _stream_lock:
            if _stream_cap is None or not _stream_cap.isOpened():
                break
            ret, frame = _stream_cap.read()
        
        if not ret:
            time.sleep(0.03)
            continue
            
        # AI Operations happen here on the server
        # (You can add your run_exercise logic inside this loop)
        
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
        cap = cv2.VideoCapture(0) # Opens camera on server machine
        if not cap.isOpened():
            return {"success": False, "message": "Cannot open camera"}
        _stream_cap = cap
        _stream_active = True
    return {"success": True}

@app.get("/camera/stream")
def camera_stream():
    return StreamingResponse(_gen_frames(), 
                             media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/camera/stop")
def camera_stop():
    global _stream_active, _stream_cap
    _stream_active = False
    with _stream_lock:
        if _stream_cap:
            _stream_cap.release()
            _stream_cap = None
    return {"success": True}

@app.get("/health")
def health():
    return {"status": "ok", "server": "FormaFix API", "db": DB_DIR}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)