"""
session_runner.py — FormaFix
==============================
Reads plan.json, lets the user choose a week/day, then runs each
exercise in sequence with live MediaPipe pose tracking.

Usage:
    python session_runner.py
"""

import json
import os
import urllib.request
from collections import deque
from datetime import datetime

import cv2
import mediapipe as mp
import numpy as np

from angle_calculator import get_all_angles
from audio_feedback import AudioFeedback
from feedback_engine import FeedbackEngine
from form_evaluator import FormEvaluator
from rep_counter import RepCounter

# ── MediaPipe setup ──────────────────────────────────────────────────────────
BaseOptions           = mp.tasks.BaseOptions
PoseLandmarker        = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode     = mp.tasks.vision.RunningMode

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)

CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28),
]

# ── Joint mapping per exercise ───────────────────────────────────────────────
EXERCISE_JOINT: dict[str, str] = {
    "straight_leg_raise":      "left_hip",
    "terminal_knee_extension": "left_knee",
    "mini_squat":              "left_knee",
    "hamstring_curl":          "left_knee",
    "pendulum":                "left_shoulder",
    "external_rotation":       "left_elbow",
    "wall_slide":              "left_shoulder",
    "shoulder_abduction":      "left_shoulder",
    "bicep_curl":              "left_elbow",
    "squat":                   "left_knee",
    "shoulder_raise":          "left_shoulder",
}

# ── Per-exercise rep-counting thresholds ─────────────────────────────────────
EXERCISE_THRESHOLDS: dict[str, dict] = {
    "straight_leg_raise":      {"up": 160, "down": 70},
    "terminal_knee_extension": {"up": 155, "down": 50},
    "mini_squat":              {"up": 150, "down": 115},
    "hamstring_curl":          {"up": 155, "down": 95},
    "pendulum":                {"up": 25,  "down": 5},
    "external_rotation":       {"up": 85,  "down": 60},
    "wall_slide":              {"up": 145, "down": 65},
    "shoulder_abduction":      {"up": 75,  "down": 15},
    "bicep_curl":              {"up": 160, "down": 40},
    "squat":                   {"up": 160, "down": 80},
    "shoulder_raise":          {"up": 85,  "down": 20},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_text(text: str) -> str:
    """Strip non-ASCII characters so OpenCV putText never crashes."""
    return text.encode("ascii", errors="replace").decode("ascii")


def _ensure_model(path: str = "pose_landmarker.task") -> str:
    if not os.path.exists(path):
        print("Downloading pose model...")
        urllib.request.urlretrieve(MODEL_URL, path)
        print("Model downloaded!")
    return path


def load_plan(filepath: str = "plan.json") -> dict:
    """Load and return the plan JSON; raise FileNotFoundError if missing."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            "plan.json not found. Run  python rehab_agent.py  first."
        )
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def select_day(plan: dict) -> tuple[list, int, int]:
    """
    Interactively ask the user which week and day to perform.

    Returns
    -------
    (exercises, week_number, day_number)
    """
    weeks = plan["plan"]["weeks"]
    print(f"\n{'=' * 45}")
    print(f"  Patient : {plan['patient']['name']}")
    print(f"  Injury  : {plan['patient']['injury']}")
    print(f"  Phase   : {plan['plan']['phase']}")
    print(f"{'=' * 45}")

    for w in weeks:
        print(f"  Week {w['week']}: {w.get('focus', '')}")

    wn   = int(input("\nEnter week number: ").strip())
    week = next((w for w in weeks if w["week"] == wn), None)
    if week is None:
        raise ValueError(f"Week {wn} not found in plan.")

    for d in week["days"]:
        names = [e["name"] for e in d["exercises"]] or ["Rest"]
        print(f"  Day {d['day']}: {', '.join(names)}")

    dn  = int(input("\nEnter day number: ").strip())
    day = next((d for d in week["days"] if d["day"] == dn), None)
    if day is None:
        raise ValueError(f"Day {dn} not found in week {wn}.")

    exercises = day.get("exercises", [])
    if not exercises:
        print("\n[FormaFix] REST DAY — take it easy! 😴")
        return [], wn, dn

    print(f"\nToday: {len(exercises)} exercise(s)")
    for i, ex in enumerate(exercises, 1):
        print(f"  {i}. {ex['name']} — {ex['sets']}×{ex['reps']}")
        if ex.get("notes"):
            print(f"     💡 {ex['notes']}")

    input("\nPress Enter to start...")
    return exercises, wn, dn


# ── Core exercise runner ──────────────────────────────────────────────────────

def run_exercise(ex_info: dict, landmarker, audio: AudioFeedback) -> dict:
    """
    Run a single exercise with live camera tracking.

    Returns a result dict with completion stats.
    """
    name   = ex_info["name"]
    sets   = ex_info["sets"]
    reps   = ex_info["reps"]
    notes  = ex_info.get("notes", "")
    joint  = EXERCISE_JOINT.get(name, "left_knee")
    thresh = EXERCISE_THRESHOLDS.get(name, {"up": 160, "down": 90})

    evaluator    = FormEvaluator()
    feedback_eng = FeedbackEngine()
    angle_buf    = deque(maxlen=5)   # smoothing buffer

    result = {
        "name":           name,
        "target_sets":    sets,
        "target_reps":    reps,
        "completed_sets": 0,
        "scores":         [],
        "avg_score":      0,
    }

    counter      = RepCounter()
    frame_scores: list[int] = []
    current_set  = 1

    cap = cv2.VideoCapture(0)
    print(f"\n  ▶  {name}  —  {sets} sets × {reps} reps")
    if notes:
        print(f"     {notes}")

    while cap.isOpened() and current_set <= sets:
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        det      = landmarker.detect(mp_img)

        if det.pose_landmarks:
            lms = det.pose_landmarks[0]

            # ── Draw skeleton ────────────────────────────────────────────────
            for s, e in CONNECTIONS:
                cv2.line(
                    frame,
                    (int(lms[s].x * w), int(lms[s].y * h)),
                    (int(lms[e].x * w), int(lms[e].y * h)),
                    (255, 255, 0), 2,
                )
            for lm in lms:
                cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 5, (0, 255, 0), -1)

            # ── Angle smoothing ──────────────────────────────────────────────
            angles = get_all_angles(lms, w, h)
            angle_buf.append(angles.get(joint, 0))
            angle = float(np.mean(angle_buf))

            # ── Rep counting ─────────────────────────────────────────────────
            rep_count, stage = counter.count(
                angle,
                up_threshold=thresh["up"],
                down_threshold=thresh["down"],
            )

            # ── Form scoring ─────────────────────────────────────────────────
            score, form_fb = evaluator.evaluate(name, joint, angle)
            frame_scores.append(score)

            tip = feedback_eng.get_feedback(name, {joint: angle})
            if score < 75:
                audio.speak(tip)

            # ── Set completion ───────────────────────────────────────────────
            if rep_count >= reps:
                set_score = round(float(np.mean(frame_scores)))
                result["scores"].append(set_score)
                result["completed_sets"] += 1
                print(f"  ✅  Set {current_set}/{sets} done — score: {set_score}/100")
                current_set  += 1
                counter.reset()
                frame_scores = []
                angle_buf.clear()

                if current_set <= sets:
                    rest = ex_info.get("rest_seconds", 30)
                    blank = np.zeros_like(frame)
                    for remaining in range(rest, 0, -1):
                        display = blank.copy()
                        cv2.putText(display, "REST",
                                    (180, 200), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 255), 4)
                        cv2.putText(display,
                                    f"Set {current_set}/{sets} starts in {remaining}s",
                                    (80, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
                        cv2.imshow("FormaFix", display)
                        if cv2.waitKey(1000) & 0xFF == ord("q"):
                            current_set = sets + 1  # force exit
                            break

            # ── HUD overlay ──────────────────────────────────────────────────
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (480, 310), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

            cv2.putText(frame, _safe_text(f"{name}  —  Set {current_set}/{sets}"),
                        (10, 30),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, _safe_text(f"{joint}: {angle:.1f}°"),
                        (10, 65),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, _safe_text(f"Reps: {rep_count} / {reps}"),
                        (10, 108), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 3)
            cv2.putText(frame, _safe_text(f"Stage: {stage or 'ready'}"),
                        (10, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

            score_colour = (0, 220, 0) if score >= 85 else (0, 200, 255) if score >= 60 else (0, 80, 255)
            cv2.putText(frame, _safe_text(f"Score: {score}/100  {form_fb}"),
                        (10, 188), cv2.FONT_HERSHEY_SIMPLEX, 0.7, score_colour, 2)
            cv2.putText(frame, _safe_text(tip),
                        (10, 228), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 165, 255), 2)
            if notes:
                cv2.putText(frame, _safe_text(f"Note: {notes}"),
                            (10, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
            cv2.putText(frame, "Q: skip exercise   R: reset reps",
                        (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        cv2.imshow("FormaFix", frame)
        key = cv2.waitKey(10) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            counter.reset()
            frame_scores = []
            angle_buf.clear()

    cap.release()
    cv2.destroyAllWindows()

    if result["scores"]:
        result["avg_score"] = round(float(np.mean(result["scores"])))
    return result


# ── Session persistence ───────────────────────────────────────────────────────

def save_session(
    plan: dict,
    week: int,
    day: int,
    ex_results: list[dict],
    filepath: str = "session_data.json",
) -> dict:
    """Append the completed session to session_data.json and return it."""
    sessions: list[dict] = []
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            sessions = json.load(f)

    scores = [r["avg_score"] for r in ex_results if r["avg_score"] > 0]
    session = {
        "timestamp":     datetime.now().isoformat(),
        "patient":       plan["patient"]["name"],
        "injury":        plan["patient"]["injury"],
        "week":          week,
        "day":           day,
        "phase":         plan["plan"]["phase"],
        "exercises":     ex_results,
        "overall_score": round(float(np.mean(scores))) if scores else 0,
    }
    sessions.append(session)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Session saved — overall score: {session['overall_score']}/100")
    return session


# ── Entry point ───────────────────────────────────────────────────────────────

def run_session(plan_file: str = "plan.json") -> None:
    plan = load_plan(plan_file)
    exercises, wn, dn = select_day(plan)
    if not exercises:
        return

    model_path = _ensure_model()
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.IMAGE,
    )
    audio   = AudioFeedback()
    results: list[dict] = []

    with PoseLandmarker.create_from_options(options) as lm:
        for i, ex in enumerate(exercises, 1):
            print(f"\n{'=' * 45}")
            print(f"  Exercise {i}/{len(exercises)}: {ex['name']}")
            print(f"{'=' * 45}")
            input("Press Enter when ready...")
            results.append(run_exercise(ex, lm, audio))

    session = save_session(plan, wn, dn, results)
    print(f"\n  🎉 Session complete! Overall: {session['overall_score']}/100")
    print("  Check session_data.json for your history.\n")


if __name__ == "__main__":
    run_session()
