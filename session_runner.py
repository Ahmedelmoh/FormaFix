"""
session_runner.py — FormaFix
==============================
Reads plan.json, lets the user choose a week/day, then runs each
exercise in sequence with live MediaPipe pose tracking.

Fixes applied:
  - patient name fallback: never stores null
  - plan.json validation: unknown exercises are skipped gracefully
  - avg_score calculated per-rep set (not per-frame)
  - automatic fallback to plan_generator if plan.json missing
  - progress_viewer shown automatically after session

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

KNOWN_EXERCISES = set(EXERCISE_JOINT.keys())


def _safe_text(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def _ensure_model(path: str = "pose_landmarker.task") -> str:
    if not os.path.exists(path):
        print("Downloading pose model...")
        urllib.request.urlretrieve(MODEL_URL, path)
        print("Model downloaded!")
    return path


def _get_patient_name(plan: dict) -> str:
    """FIX 1 — never return null for patient name."""
    name = plan.get("patient", {}).get("name")
    return name if name and str(name).strip() else "Patient"


def _validate_exercises(exercises: list[dict]) -> list[dict]:
    """FIX 2 — skip unknown exercises instead of crashing."""
    valid, invalid = [], []
    for ex in exercises:
        if ex.get("name") in KNOWN_EXERCISES:
            valid.append(ex)
        else:
            invalid.append(ex.get("name", "?"))
    if invalid:
        print(f"\n  Warning: Skipping unknown exercise(s): {', '.join(invalid)}")
    return valid


def load_plan(filepath: str = "plan.json") -> dict:
    """FIX 3 — auto fallback to plan_generator if plan.json is missing."""
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

    print("\n  plan.json not found.")
    print("  1. Run  python rehab_agent.py    (AI - needs API key)")
    print("  2. Run  python plan_generator.py (offline - no API needed)")
    choice = input("\n  Generate an offline plan now? (y/n): ").strip().lower()
    if choice == "y":
        from plan_generator import generate_and_save
        return generate_and_save(filepath)
    raise FileNotFoundError("plan.json not found. Generate one first.")


def select_day(plan: dict) -> tuple[list, int, int]:
    plan_body = plan.get("plan")
    if not plan_body or "weeks" not in plan_body:
        raise KeyError(
            "plan.json is missing the 'plan.weeks' structure. "
            "Regenerate it with rehab_agent.py or plan_generator.py."
        )
    weeks = plan_body["weeks"]
    print(f"\n{'='*45}")
    print(f"  Patient : {_get_patient_name(plan)}")
    print(f"  Injury  : {plan['patient'].get('injury', 'Unknown')}")
    print(f"  Phase   : {plan_body.get('phase', 'unknown')}")
    print(f"{'='*45}")

    for w in weeks:
        print(f"  Week {w['week']}: {w.get('focus','')}")

    wn   = int(input("\nEnter week number: ").strip())
    week = next((w for w in weeks if w["week"] == wn), None)
    if week is None:
        raise ValueError(f"Week {wn} not found.")

    for d in week["days"]:
        names = [e["name"] for e in d["exercises"]] or ["Rest"]
        print(f"  Day {d['day']}: {', '.join(names)}")

    dn  = int(input("\nEnter day number: ").strip())
    day = next((d for d in week["days"] if d["day"] == dn), None)
    if day is None:
        raise ValueError(f"Day {dn} not found.")

    exercises = _validate_exercises(day.get("exercises", []))
    if not exercises:
        print("\n  REST DAY - take it easy!")
        return [], wn, dn

    print(f"\n  Today: {len(exercises)} exercise(s)")
    for i, ex in enumerate(exercises, 1):
        print(f"  {i}. {ex['name']} - {ex['sets']}x{ex['reps']}")
        if ex.get("notes"):
            print(f"     {ex['notes']}")

    input("\nPress Enter to start...")
    return exercises, wn, dn


def run_exercise(ex_info: dict, landmarker, audio: AudioFeedback) -> dict:
    """
    FIX 4 — avg_score is now the mean of per-SET scores,
    where each set score = mean of frame scores during that set.
    This gives a far more accurate performance measure.
    """
    name   = ex_info["name"]
    sets   = ex_info["sets"]
    reps   = ex_info["reps"]
    notes  = ex_info.get("notes", "")
    joint  = EXERCISE_JOINT.get(name, "left_knee")
    thresh = EXERCISE_THRESHOLDS.get(name, {"up": 160, "down": 90})

    evaluator    = FormEvaluator()
    feedback_eng = FeedbackEngine()
    angle_buf    = deque(maxlen=5)

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
    print(f"\n  {name}  -  {sets} sets x {reps} reps")
    if notes:
        print(f"  {notes}")

    while cap.isOpened() and current_set <= sets:
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        det    = landmarker.detect(mp_img)

        if det.pose_landmarks:
            lms = det.pose_landmarks[0]

            for s, e in CONNECTIONS:
                cv2.line(frame,
                    (int(lms[s].x*w), int(lms[s].y*h)),
                    (int(lms[e].x*w), int(lms[e].y*h)),
                    (255, 255, 0), 2)
            for lm in lms:
                cv2.circle(frame, (int(lm.x*w), int(lm.y*h)), 5, (0, 255, 0), -1)

            angles = get_all_angles(lms, w, h)
            angle_buf.append(angles.get(joint, 0))
            angle = float(np.mean(angle_buf))

            rep_count, stage = counter.count(
                angle,
                up_threshold=thresh["up"],
                down_threshold=thresh["down"],
            )

            score, form_fb = evaluator.evaluate(name, joint, angle)
            frame_scores.append(score)   # collect every frame

            tip = feedback_eng.get_feedback(name, {joint: angle})
            if score < 75:
                audio.speak(tip)

            if rep_count >= reps:
                set_score = round(float(np.mean(frame_scores)))  # average over the set
                result["scores"].append(set_score)
                result["completed_sets"] += 1
                print(f"  Set {current_set}/{sets} done - score: {set_score}/100")
                current_set += 1
                counter.reset()
                frame_scores = []
                angle_buf.clear()

                if current_set <= sets:
                    rest  = ex_info.get("rest_seconds", 30)
                    blank = np.zeros_like(frame)
                    for remaining in range(rest, 0, -1):
                        d = blank.copy()
                        cv2.putText(d, "REST", (180, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 255), 4)
                        cv2.putText(d, f"Set {current_set}/{sets} in {remaining}s",
                            (80, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
                        cv2.imshow("FormaFix", d)
                        if cv2.waitKey(1000) & 0xFF == ord("q"):
                            current_set = sets + 1
                            break

            # HUD
            ov = frame.copy()
            cv2.rectangle(ov, (0,0), (480, 310), (0,0,0), -1)
            cv2.addWeighted(ov, 0.45, frame, 0.55, 0, frame)

            cv2.putText(frame, _safe_text(f"{name}  Set {current_set}/{sets}"),
                (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.putText(frame, _safe_text(f"{joint}: {angle:.1f} deg"),
                (10,65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(frame, _safe_text(f"Reps: {rep_count} / {reps}"),
                (10,108), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0,255,255), 3)
            cv2.putText(frame, _safe_text(f"Stage: {stage or 'ready'}"),
                (10,148), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,255,255), 2)

            sc = (0,220,0) if score>=85 else (0,200,255) if score>=60 else (0,80,255)
            cv2.putText(frame, _safe_text(f"Score: {score}/100  {form_fb}"),
                (10,188), cv2.FONT_HERSHEY_SIMPLEX, 0.7, sc, 2)
            cv2.putText(frame, _safe_text(tip),
                (10,228), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0,165,255), 2)
            if notes:
                cv2.putText(frame, _safe_text(f"Note: {notes}"),
                    (10,265), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,200,200), 1)
            cv2.putText(frame, "Q:skip  R:reset",
                (10,300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)

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


def save_session(
    plan: dict,
    week: int,
    day: int,
    ex_results: list[dict],
    filepath: str = "session_data.json",
) -> dict:
    sessions: list[dict] = []
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            sessions = json.load(f)

    scores = [r["avg_score"] for r in ex_results if r["avg_score"] > 0]
    session = {
        "timestamp":     datetime.now().isoformat(),
        "patient":       _get_patient_name(plan),   # FIX 1 - never null
        "injury":        plan["patient"].get("injury", "Unknown"),
        "week":          week,
        "day":           day,
        "phase":         plan.get("plan", {}).get("phase", "unknown"),
        "exercises":     ex_results,
        "overall_score": round(float(np.mean(scores))) if scores else 0,
    }
    sessions.append(session)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

    print(f"\n  Session saved - overall score: {session['overall_score']}/100")
    return session


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
            print(f"\n{'='*45}")
            print(f"  Exercise {i}/{len(exercises)}: {ex['name']}")
            print(f"{'='*45}")
            input("Press Enter when ready...")
            results.append(run_exercise(ex, lm, audio))

    session = save_session(plan, wn, dn, results)
    print(f"\n  Session complete! Overall: {session['overall_score']}/100")

    # FIX 5 - show progress automatically after every session
    try:
        from progress_agent import show_progress
        show_progress()
    except Exception as e:
        print(f"  [Info] Progress viewer: {e}")


if __name__ == "__main__":
    run_session()