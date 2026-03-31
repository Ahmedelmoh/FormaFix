"""
session_runner.py — FormaFix
=============================
بيقرأ plan.json ويشغّل تمارين اليوم مع MediaPipe tracking.
كل التمارين بدون معدات — MGH + MOON Protocol.
"""

import json
import os
import cv2
import mediapipe as mp
import numpy as np
import urllib.request
from datetime import datetime
from collections import deque

import time

from angle_calculator import get_all_angles
from rep_counter      import RepCounter
from form_evaluator   import FormEvaluator
from feedback_engine  import FeedbackEngine
from audio_feedback   import AudioFeedback
from rest_day_tips    import show_rest_day_screen

BaseOptions           = mp.tasks.BaseOptions
PoseLandmarker        = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode     = mp.tasks.vision.RunningMode

# ── FIX 1: جانب الإصابة (يتحدد من plan.json أو يسأل اليوزر) ────────────────────
def get_injured_side(plan: dict) -> str:
    """بيقرأ جانب الإصابة من plan.json أو يسأل اليوزر."""
    injury = plan.get("patient", {}).get("injury", "").lower()
    if "right" in injury or "يمين" in injury:
        return "right"
    elif "left" in injury or "يسار" in injury or "شمال" in injury:
        return "left"
    # لو مش واضح من النص — اسأل
    print("\n  Which leg is injured?")
    print("  1. Right (يمين)")
    print("  2. Left  (يسار)")
    choice = input("  Enter 1 or 2: ").strip()
    return "right" if choice == "1" else "left"


def adapt_joint(joint_key: str, side: str) -> str:
    """بيحول left/right بناءً على جانب الإصابة."""
    if side == "right":
        return joint_key.replace("left_", "right_")
    return joint_key


# ── المفصل الرئيسي لكل تمرين (دايماً left — بيتحول لـ right لو محتاج) ──────
EXERCISE_JOINT = {
    # Phase 1 (0-2 weeks) — protect graft
    'quad_set':                'left_knee',
    'ankle_pump':              'left_ankle',
    'heel_slide_p1':           'left_knee',
    'straight_leg_raise':      'left_hip',
    'hip_abduction':           'left_hip',
    'terminal_knee_extension': 'left_knee',
    'calf_raise':              'left_ankle',
    # Phase 2 (3-5 weeks)
    'heel_slide_p2':           'left_knee',
    'mini_squat':              'left_knee',
    'hamstring_curl_p2':       'left_knee',
    'bridge':                  'left_knee',
    'step_up':                 'left_knee',
    'single_leg_stand':        'left_knee',
    # Phase 3 (6-8 weeks)
    'squat_p3':                'left_knee',
    'hamstring_curl_p3':       'left_knee',
    'lateral_lunge':           'left_knee',
    'romanian_deadlift':       'left_knee',
    # Phase 4 (9-12 weeks)
    'full_squat':              'left_knee',
    'lunge':                   'left_knee',
    # Shoulder
    'pendulum':                'left_shoulder',
    'external_rotation':       'left_elbow',
    'wall_slide':              'left_shoulder',
    'shoulder_abduction':      'left_shoulder',
}

# ── كل التمارين الواقفة المتاحة ──────────────────────────────────────────────
STANDING_EXERCISES = {
    # Phase 1
    'single_leg_stand', 'mini_squat', 'hamstring_curl_p2',
    # Phase 2
    'step_up',
    # Phase 3
    'squat_p3', 'hamstring_curl_p3', 'lateral_lunge', 'romanian_deadlift',
    # Phase 4
    'full_squat', 'lunge',
    # Shoulder
    'pendulum', 'external_rotation', 'wall_slide', 'shoulder_abduction',
}

DEMO_MODE = True   # True = واقف بس | False = كل التمارين

# ── Thresholds لعدّ الـ reps لكل تمرين ───────────────────────────────────────
# ── كيف يشتغل الـ RepCounter ──────────────────────────────────────────────────
# كل تمرين عنده:
#   'down' = زاوية الوضع التحتاني (النزول/الثني) — لما يوصلها يبدأ
#   'up'   = زاوية العودة للأعلى — لما يرجع منها تكتمل الـ rep
#
# المبدأ الطبي الصح:
#   Rep = نزول (down) ثم عودة جزئية (up) — مش لازم full extension
#   مثلاً mini_squat: ينزل لـ 120° ثم يرجع لـ 150° (مش 165°)
#   ده بيحمي المفصل ومش بيطلب full extension
#
EXERCISE_THRESHOLDS = {
    # ── كيف تشتغل الـ Thresholds ─────────────────────────────────────────────
    # 'down' = زاوية النزول/الثني (rep تبدأ هنا)
    # 'up'   = زاوية العودة الجزئية (rep تكتمل هنا — مش لازم full extension!)
    # المبدأ: نزول ثم عودة جزئية = rep كاملة — لا تطلب 165° من مريض ACL

    # Phase 1 lying (compatibility)
    'quad_set':                {'up': 155, 'down': 130},
    'ankle_pump':              {'up': 130, 'down': 80},
    'heel_slide_p1':           {'up': 155, 'down': 135},
    'straight_leg_raise':      {'up': 150, 'down': 65},
    'hip_abduction':           {'up': 35,  'down': 10},
    'terminal_knee_extension': {'up': 155, 'down': 130},
    'calf_raise':              {'up': 130, 'down': 85},

    # Phase 2 standing — عودة جزئية فقط (مش full extension)
    'mini_squat':              {'up': 150, 'down': 120},  # نزول 60° ← عودة جزئية 30°
    'hamstring_curl_p2':       {'up': 150, 'down': 110},  # ثني 70° ← يرجع جزئياً
    'step_up':                 {'up': 150, 'down': 130},  # طلوع ← نزول بتحكم
    'single_leg_stand':        {'up': 155, 'down': 120},  # رفع الرجل ← وضعها
    'heel_slide_p2':           {'up': 150, 'down': 90},
    'bridge':                  {'up': 110, 'down': 80},

    # Phase 3 — عمق أكبر
    'squat_p3':                {'up': 145, 'down': 90},   # نزول 90° ← يرجع 35°
    'hamstring_curl_p3':       {'up': 150, 'down': 90},
    'lateral_lunge':           {'up': 150, 'down': 120},
    'romanian_deadlift':       {'up': 158, 'down': 145},

    # Phase 4 — مدى كامل
    'full_squat':              {'up': 145, 'down': 70},
    'lunge':                   {'up': 145, 'down': 90},

    # Shoulder
    'pendulum':                {'up': 25,  'down': 5},
    'external_rotation':       {'up': 85,  'down': 60},
    'wall_slide':              {'up': 145, 'down': 65},
    'shoulder_abduction':      {'up': 75,  'down': 15},
}

# ── الهيكل العظمي لكل تمرين ──────────────────────────────────────────────────
JOINT_COLOR = {
    "shoulder": (0,  255, 150),
    "elbow":    (0,  200, 255),
    "wrist":    (0,  150, 255),
    "hip":      (255, 200,  0),
    "knee":     (0,  100, 255),
    "ankle":    (180,  0, 255),
}

# النقاط والعظام لكل تمرين (بس المستخدمة في التمرين)
EXERCISE_SKELETON = {
    # Phase 1 — كلها مستلقي: أرجل + ورك
    'quad_set':                {'joints': {23:(JOINT_COLOR["hip"],8), 25:(JOINT_COLOR["knee"],9), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27)]},
    'ankle_pump':              {'joints': {25:(JOINT_COLOR["knee"],7), 27:(JOINT_COLOR["ankle"],9), 28:(JOINT_COLOR["ankle"],9)}, 'bones': [(25,27)]},
    'heel_slide_p1':           {'joints': {23:(JOINT_COLOR["hip"],8), 25:(JOINT_COLOR["knee"],9), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27)]},
    'straight_leg_raise':      {'joints': {11:(JOINT_COLOR["shoulder"],7), 23:(JOINT_COLOR["hip"],9), 25:(JOINT_COLOR["knee"],8), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(11,23),(23,25),(25,27)]},
    'hip_abduction':           {'joints': {23:(JOINT_COLOR["hip"],9), 24:(JOINT_COLOR["hip"],9), 25:(JOINT_COLOR["knee"],8), 26:(JOINT_COLOR["knee"],8)}, 'bones': [(23,25),(24,26),(23,24)]},
    'terminal_knee_extension': {'joints': {23:(JOINT_COLOR["hip"],8), 25:(JOINT_COLOR["knee"],9), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27)]},
    'calf_raise':              {'joints': {25:(JOINT_COLOR["knee"],7), 27:(JOINT_COLOR["ankle"],9)}, 'bones': [(25,27)]},
    # Phase 2 — واقف + مستلقي
    'heel_slide_p2':           {'joints': {23:(JOINT_COLOR["hip"],8), 25:(JOINT_COLOR["knee"],9), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27)]},
    'mini_squat':              {'joints': {23:(JOINT_COLOR["hip"],8),24:(JOINT_COLOR["hip"],8),25:(JOINT_COLOR["knee"],9),26:(JOINT_COLOR["knee"],9),27:(JOINT_COLOR["ankle"],7),28:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27),(24,26),(26,28),(23,24)]},
    'hamstring_curl_p2':       {'joints': {23:(JOINT_COLOR["hip"],8), 25:(JOINT_COLOR["knee"],9), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27)]},
    'bridge':                  {'joints': {23:(JOINT_COLOR["hip"],9),24:(JOINT_COLOR["hip"],9),25:(JOINT_COLOR["knee"],8),26:(JOINT_COLOR["knee"],8)}, 'bones': [(23,25),(24,26),(23,24)]},
    'step_up':                 {'joints': {23:(JOINT_COLOR["hip"],8), 25:(JOINT_COLOR["knee"],9), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27)]},
    'single_leg_stand':        {'joints': {23:(JOINT_COLOR["hip"],8),24:(JOINT_COLOR["hip"],8),25:(JOINT_COLOR["knee"],9),26:(JOINT_COLOR["knee"],9),27:(JOINT_COLOR["ankle"],7),28:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27),(24,26),(26,28),(23,24)]},
    # Phase 3
    'squat_p3':                {'joints': {23:(JOINT_COLOR["hip"],8),24:(JOINT_COLOR["hip"],8),25:(JOINT_COLOR["knee"],9),26:(JOINT_COLOR["knee"],9),27:(JOINT_COLOR["ankle"],7),28:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27),(24,26),(26,28),(23,24)]},
    'hamstring_curl_p3':       {'joints': {23:(JOINT_COLOR["hip"],8), 25:(JOINT_COLOR["knee"],9), 27:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27)]},
    'lateral_lunge':           {'joints': {23:(JOINT_COLOR["hip"],8),24:(JOINT_COLOR["hip"],8),25:(JOINT_COLOR["knee"],9),26:(JOINT_COLOR["knee"],9),27:(JOINT_COLOR["ankle"],7),28:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27),(24,26),(26,28),(23,24)]},
    'romanian_deadlift':       {'joints': {23:(JOINT_COLOR["hip"],9),24:(JOINT_COLOR["hip"],9),25:(JOINT_COLOR["knee"],8),26:(JOINT_COLOR["knee"],8)}, 'bones': [(23,25),(24,26),(23,24)]},
    # Phase 4
    'full_squat':              {'joints': {23:(JOINT_COLOR["hip"],8),24:(JOINT_COLOR["hip"],8),25:(JOINT_COLOR["knee"],9),26:(JOINT_COLOR["knee"],9),27:(JOINT_COLOR["ankle"],7),28:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27),(24,26),(26,28),(23,24)]},
    'lunge':                   {'joints': {23:(JOINT_COLOR["hip"],8),24:(JOINT_COLOR["hip"],8),25:(JOINT_COLOR["knee"],9),26:(JOINT_COLOR["knee"],9),27:(JOINT_COLOR["ankle"],7),28:(JOINT_COLOR["ankle"],7)}, 'bones': [(23,25),(25,27),(24,26),(26,28),(23,24)]},
    # Shoulder
    'pendulum':                {'joints': {11:(JOINT_COLOR["shoulder"],9), 13:(JOINT_COLOR["elbow"],7), 15:(JOINT_COLOR["wrist"],6)}, 'bones': [(11,13),(13,15)]},
    'external_rotation':       {'joints': {11:(JOINT_COLOR["shoulder"],8), 13:(JOINT_COLOR["elbow"],9), 15:(JOINT_COLOR["wrist"],7)}, 'bones': [(11,13),(13,15)]},
    'wall_slide':              {'joints': {23:(JOINT_COLOR["hip"],7), 11:(JOINT_COLOR["shoulder"],9), 13:(JOINT_COLOR["elbow"],7)}, 'bones': [(23,11),(11,13)]},
    'shoulder_abduction':      {'joints': {23:(JOINT_COLOR["hip"],7), 11:(JOINT_COLOR["shoulder"],9), 13:(JOINT_COLOR["elbow"],7)}, 'bones': [(23,11),(11,13)]},
}

JOINT_NAME_IDX = {
    'left_shoulder': 11, 'right_shoulder': 12,
    'left_elbow': 13,    'right_elbow': 14,
    'left_hip': 23,      'right_hip': 24,
    'left_knee': 25,     'right_knee': 26,
    'left_ankle': 27,    'right_ankle': 28,
}



# ── FIX 2: شرح كل تمرين قبل ما يبدأ ────────────────────────────────────────
EXERCISE_INSTRUCTIONS = {
    'quad_set': {
        'position': 'LYING on your back',
        'how_to': [
            "Lie flat on your back with both legs straight",
            "Tighten the thigh muscle of your injured leg",
            "Push the back of your knee DOWN into the floor",
            "Hold for 10 seconds — you should see your kneecap move up",
            "Relax and repeat",
        ],
        'watch_out': "Do NOT bend your knee — keep it flat throughout",
        'why': "Most important Phase 1 exercise — reactivates the quad muscle",
    },
    'ankle_pump': {
        'position': 'LYING on your back',
        'how_to': [
            "Lie flat, legs straight",
            "Pull your foot UP toward your nose (flex)",
            "Push your foot DOWN away from you (point)",
            "Keep it rhythmic and gentle",
        ],
        'watch_out': "Keep knee straight — this is ankle movement only",
        'why': "Improves circulation and reduces swelling",
    },
    'heel_slide_p1': {
        'position': 'LYING on your back',
        'how_to': [
            "Lie flat on your back",
            "Slowly slide your heel toward your buttock",
            "Bend ONLY to 45° — stop if you feel pain",
            "Hold 2 seconds at 45°, then slide back slowly",
        ],
        'watch_out': "STOP at 45° — do not force beyond this in Phase 1!",
        'why': "Gently restores knee flexion within safe Phase 1 limits",
    },
    'straight_leg_raise': {
        'position': 'LYING on your back',
        'how_to': [
            "Lie flat — bend your GOOD leg, keep injured leg straight",
            "Tighten your quad first (quad set position)",
            "Lift your injured leg to match height of your good knee",
            "Hold 2 seconds, lower slowly in 3 counts",
        ],
        'watch_out': "If your knee bends when you lift — master quad_set first!",
        'why': "Strengthens quad without stressing the knee joint",
    },
    'hip_abduction': {
        'position': 'LYING on your side',
        'how_to': [
            "Lie on your GOOD side, injured leg on top",
            "Keep injured leg straight, toes pointing forward",
            "Lift leg upward about 45cm, hold 2 sec",
            "Lower slowly — control the descent",
        ],
        'watch_out': "Don't rotate your hip — toes stay facing forward",
        'why': "Strengthens glutes and hip stabilizers",
    },
    'terminal_knee_extension': {
        'position': 'LYING or SITTING',
        'how_to': [
            "Place a rolled towel/pillow under your knee",
            "Starting with knee slightly bent (~30°)",
            "Straighten your knee fully — lift heel off floor",
            "Hold at full extension for 5 seconds",
            "Lower slowly",
        ],
        'watch_out': "Goal is FULL 0° extension — this is critical for recovery",
        'why': "Most important: restores full knee extension",
    },
    'calf_raise': {
        'position': 'STANDING with support',
        'how_to': [
            "Stand near a wall or chair for balance",
            "Rise up slowly onto your toes",
            "Hold at top for 2 seconds",
            "Lower slowly in 3 counts — control the descent",
        ],
        'watch_out': "Keep weight equal on both feet",
        'why': "Strengthens calf and improves circulation",
    },
    'heel_slide_p2': {
        'position': 'LYING on your back',
        'how_to': [
            "Lie flat on your back",
            "Slide heel toward buttock",
            "Phase 2 goal: reach 90° flexion",
            "Compare with your other leg",
        ],
        'watch_out': "Should be pain-free — if pain, stop at comfortable range",
        'why': "Phase 2: restoring full flexion range",
    },
    'mini_squat': {
        'position': 'STANDING',
        'how_to': [
            "Stand with feet shoulder-width apart",
            "Hold chair/wall for support if needed",
            "Slowly bend knees to 60° only (NOT deeper)",
            "Keep back straight, knees track over toes",
            "Rise slowly back up",
        ],
        'watch_out': "Phase 2: MAX 60° bend only — do not squat deeper!",
        'why': "Phase 2 strengthening within safe range",
    },
    'hamstring_curl_p2': {
        'position': 'STANDING',
        'how_to': [
            "Stand on your good leg, hold support",
            "Slowly bend your injured knee backward",
            "Bring heel toward your back — target ~70°",
            "Lower slowly with control",
        ],
        'watch_out': "Phase 2: gentle curl only, no forcing",
        'why': "Phase 2 hamstring activation",
    },
    'bridge': {
        'position': 'LYING on your back',
        'how_to': [
            "Lie on back, both knees bent ~90°, feet flat",
            "Press feet into floor and lift hips up",
            "Squeeze glutes at the top — hold 3 seconds",
            "Lower slowly, one vertebra at a time",
        ],
        'watch_out': "Keep hips level — don't let one side drop",
        'why': "Strengthens glutes and hamstrings safely",
    },
    'step_up': {
        'position': 'STANDING at a stair step (10-15cm)',
        'how_to': [
            "Stand facing a small step (first stair)",
            "Step UP with your injured leg",
            "Bring good leg up to join — straighten up fully",
            "Step DOWN with injured leg, lower with control",
        ],
        'watch_out': "Knee tracks over 2nd toe — no inward collapse",
        'why': "Functional strengthening, normal gait pattern",
    },
    'single_leg_stand': {
        'position': 'STANDING near a wall',
        'how_to': [
            "Stand near wall for safety",
            "Lift good leg off floor",
            "Balance on injured leg with slight knee bend",
            "Hold 30 seconds — look at fixed point ahead",
        ],
        'watch_out': "Slight bend in knee — NEVER lock it straight",
        'why': "Proprioception and balance training",
    },
    'squat_p3': {
        'position': 'STANDING',
        'how_to': [
            "Feet shoulder-width, toes slightly out",
            "Arms forward for balance",
            "Squat down to 90° — like sitting on a chair",
            "Chest up, weight equal on both legs",
            "Push through heels to stand up",
        ],
        'watch_out': "Equal weight both legs — don't favor good side",
        'why': "Phase 3 progressive strengthening",
    },
    'hamstring_curl_p3': {
        'position': 'STANDING or PRONE',
        'how_to': [
            "Stand on good leg, hold support",
            "Curl injured leg up to 90°",
            "Hold briefly at top",
            "Lower in 3 seconds — control the descent",
        ],
        'watch_out': "Full 90° curl — equal to good leg",
        'why': "Phase 3 hamstring strengthening",
    },
    'lateral_lunge': {
        'position': 'STANDING',
        'how_to': [
            "Stand with feet together",
            "Step wide to the SIDE with one leg",
            "Bend into that leg — knee over toes",
            "Push back to start",
        ],
        'watch_out': "Both feet face forward — no turning out",
        'why': "Phase 3 multi-directional strengthening",
    },
    'romanian_deadlift': {
        'position': 'STANDING',
        'how_to': [
            "Stand on both feet, slight knee bend",
            "Hinge FORWARD at hips — not at knees",
            "Arms hang down — feel hamstring stretch",
            "Return to upright by squeezing glutes",
        ],
        'watch_out': "This is a HIP hinge — keep back straight",
        'why': "Phase 3 posterior chain strengthening",
    },
    'full_squat': {
        'position': 'STANDING',
        'how_to': [
            "Feet shoulder-width, toes out slightly",
            "Squat as deep as comfortable",
            "Heels stay on floor throughout",
            "Chest up, knees track over toes",
        ],
        'watch_out': "Phase 4: full range now allowed if pain-free",
        'why': "Phase 4 full range strengthening",
    },
    'lunge': {
        'position': 'STANDING',
        'how_to': [
            "Step FORWARD with one leg",
            "Lower back knee toward floor",
            "Front knee stays over ankle",
            "Push back to start",
        ],
        'watch_out': "Front knee tracks over 2nd toe",
        'why': "Phase 4 functional strength",
    },
    'pendulum': {
        'position': 'STANDING, leaning forward',
        'how_to': [
            "Lean forward with good arm on table",
            "Let injured arm HANG completely loose",
            "Allow gravity to swing it gently",
            "Small circles — no muscle effort",
        ],
        'watch_out': "Zero muscle effort — pure gravity swing",
        'why': "Phase 1 shoulder: reduces stiffness gently",
    },
}

def safe_text(t):
    return t.encode('ascii', errors='replace').decode('ascii')


def _ensure_model():
    p = 'pose_landmarker.task'
    if not os.path.exists(p):
        print("Downloading model...")
        urllib.request.urlretrieve(
            'https://storage.googleapis.com/mediapipe-models/pose_landmarker/'
            'pose_landmarker_lite/float16/1/pose_landmarker_lite.task', p)
    return p


def load_plan(f="plan.json") -> dict:
    if not os.path.exists(f):
        raise FileNotFoundError("plan.json not found. Run rehab_agent.py first.")
    with open(f, encoding="utf-8") as fp:
        return json.load(fp)


def draw_skeleton(frame, landmarks, w, h, exercise: str = "", active_joint: str = ""):
    skel       = EXERCISE_SKELETON.get(exercise, {})
    joints_cfg = skel.get('joints', {})
    bones_cfg  = skel.get('bones', [])
    active_idx = JOINT_NAME_IDX.get(active_joint, -1)

    for s, e in bones_cfg:
        x1 = int(landmarks[s].x * w); y1 = int(landmarks[s].y * h)
        x2 = int(landmarks[e].x * w); y2 = int(landmarks[e].y * h)
        cv2.line(frame, (x1, y1), (x2, y2), (80, 80, 80), 2)

    for idx, (color, radius) in joints_cfg.items():
        cx = int(landmarks[idx].x * w)
        cy = int(landmarks[idx].y * h)
        if idx == active_idx:
            cv2.circle(frame, (cx, cy), radius + 6, (255, 255, 255), 2)
            cv2.circle(frame, (cx, cy), radius + 3, color, -1)
        else:
            cv2.circle(frame, (cx, cy), radius, color, -1)
            cv2.circle(frame, (cx, cy), radius, (0, 0, 0), 1)


def select_day(plan: dict):
    weeks = plan["plan"]["weeks"]
    assessment = plan.get("assessment", {})

    print(f"\n{'='*50}")
    print(f"  Patient : {plan['patient']['name']}")
    print(f"  Injury  : {plan['patient']['injury']}")
    print(f"  Phase   : {assessment.get('current_phase', '?')} — {assessment.get('phase_name', '')}")
    print(f"{'='*50}")

    for w in weeks:
        print(f"  Week {w['week']} (Phase {w.get('phase','?')}): {w.get('focus', '')}")

    wn = int(input("\nEnter week number: ").strip())
    week = next((w for w in weeks if w["week"] == wn), None)
    if not week:
        raise ValueError(f"Week {wn} not found.")

    for d in week["days"]:
        names = [e["name"] for e in d.get("exercises", [])] or ["Rest"]
        print(f"  Day {d['day']}: {', '.join(names)}")

    dn = int(input("\nEnter day number: ").strip())
    day = next((d for d in week["days"] if d["day"] == dn), None)
    if not day:
        raise ValueError(f"Day {dn} not found.")

    exercises = day.get("exercises", [])
    if not exercises:
        show_rest_day_screen(injury=plan["patient"]["injury"], day=dn, week=wn)
        return [], wn, dn

    # Demo mode: فلتر التمارين الواقفة بس
    if DEMO_MODE:
        original = exercises
        exercises = [ex for ex in exercises if ex["name"] in STANDING_EXERCISES]
        skipped = [ex["name"] for ex in original if ex not in exercises]
        if skipped:
            print(f"  [Demo mode] Skipped lying exercises: {', '.join(skipped)}")
        if not exercises:
            print("  [Demo mode] No standing exercises today — showing rest day.")
            show_rest_day_screen(injury=plan["patient"]["injury"], day=dn, week=wn)
            return [], wn, dn

    print(f"\nToday: {len(exercises)} exercises")
    for i, ex in enumerate(exercises, 1):
        print(f"  {i}. {ex['name']} — {ex['sets']}x{ex['reps']}")
        if ex.get("notes"):
            print(f"     {ex['notes']}")

    input("\nPress Enter to start...")
    return exercises, wn, dn


def run_exercise(ex_info: dict, landmarker, audio, cap, side: str = 'left') -> dict:
    # 1. الإعدادات الأساسية
    name   = ex_info["name"]
    sets   = ex_info["sets"]
    reps   = ex_info["reps"]
    notes  = ex_info.get("notes", "")

    joint_base = EXERCISE_JOINT.get(name, "left_knee")
    joint      = adapt_joint(joint_base, side)
    thresh     = EXERCISE_THRESHOLDS.get(name, {"up": 160, "down": 90})

    # 2. أدوات العداد والتقييم
    evaluator    = FormEvaluator()
    feedback_eng = FeedbackEngine()
    angle_buffer = deque(maxlen=8) 
    result = {"name": name, "target_sets": sets, "target_reps": reps,
              "completed_sets": 0, "scores": [], "avg_score": 0}

    current_set      = 1
    # تعديل: confirm_frames زادت لـ 24 لضمان دقة العد ومنع القفز
    counter          = RepCounter(confirm_frames=24) 
    STABILIZE_FRAMES = 50 # زيادة وقت الثبات في البداية
    frame_count      = 0
    counting_active  = False
    frame_scores     = []
    all_frame_scores = []

    # 3. الـ Loop الأساسي للتمرين
    # تأكدنا إن الشرط مربوط بعدد المجموعات (current_set)
    while cap.isOpened() and current_set <= sets:
        ret, frame = cap.read()
        if not ret: break

        h, w, _ = frame.shape
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        det     = landmarker.detect(mp_img)

        if det.pose_landmarks:
            lms = det.pose_landmarks[0]
            draw_skeleton(frame, lms, w, h, exercise=name, active_joint=joint)

            # حساب الزوايا
            angles_data = get_all_angles(lms, w, h)
            joint_info = angles_data.get(joint, {'angle': 0, 'vis': 0})
            raw_angle = joint_info['angle']
            visibility = joint_info['vis']

            # منع العد لو المريض مش باين كفاية
            if visibility < 0.5:
                cv2.putText(frame, "KEEP YOUR FULL BODY IN VIEW", (w//2-150, 400), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            
            angle_buffer.append(raw_angle)
            angle = float(np.mean(angle_buffer))

            # نظام الاستقرار (Hold still...)
            if not counting_active:
                frame_count += 1
                remaining = max(0, STABILIZE_FRAMES - frame_count)
                cv2.putText(frame, f"STABILIZING... {remaining}", (w//2-100, h//2), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                if frame_count >= STABILIZE_FRAMES:
                    audio.speak("Ready, start moving")
                    counting_active = True
                    counter.reset()
                    frame_scores = []
            
            else:
                # العداد الحقيقي (بيستخدم المنطق الجديد اللي فيه Time Delay)
                rep_count, stage = counter.count(angle, thresh["up"], thresh["down"])
                
                # التقييم
                score, form_fb = evaluator.evaluate(name, joint, angle)
                if visibility > 0.4:  # بنسجل السكور بس لو الرؤية واضحة (lowered threshold from 0.6 to 0.4)
                    frame_scores.append(score)
                    all_frame_scores.append(score)
                
                # إحضار الـ Tip (تم تصحيح متغير angles ليكون angles_data)
                elbow_key = f'{side}_elbow'
                current_angles_values = {k: v['angle'] for k, v in angles_data.items()}
                tip = feedback_eng.get_feedback(name, {joint: angle, elbow_key: current_angles_values.get(elbow_key, 90)})

                # HUD عرض المعلومات
                draw_hud(frame, name, current_set, sets, angle, rep_count, reps, stage, score, form_fb, tip, notes)

                # ── منطق انتهاء المجموعة (قفل الأمان) ────────────────
                if rep_count >= reps:
                    # حساب متوسط السكور للمجموعة دي
                    s_score = round(float(np.mean(frame_scores))) if frame_scores else 100
                    result["scores"].append(s_score)
                    result["completed_sets"] += 1
                    
                    audio.speak(f"Set {current_set} complete")

                    if current_set < sets:
                        # شاشة الراحة (بتقفل الكاميرا مؤقتاً أو بتعرض عد تنازلي)
                        show_rest_screen(cap, current_set + 1, sets, ex_info.get("rest_seconds", 10))
                        
                        # ريست لكل العدادات للمجموعة الجديدة
                        current_set    += 1
                        counting_active = False
                        frame_count     = 0
                        counter.reset()
                        frame_scores    = []
                    else:
                        # لو خلصنا كل المجموعات
                        current_set += 1 # عشان يكسر الـ while loop

        cv2.imshow("FormaFix Training", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"): 
            break
        elif key == ord("r"): 
            counter.reset(); frame_scores = []; angle_buffer.clear()

    # حساب النتيجة النهائية للتمرين
    if result["scores"]:
        result["avg_score"] = round(float(np.mean(result["scores"])))
    elif all_frame_scores:
        # Fallback: if no set was fully completed, still return the tracked form score.
        result["avg_score"] = round(float(np.mean(all_frame_scores)))
        result["scores"] = [result["avg_score"]]
    
    return result

def draw_hud(frame, name, current_set, sets, angle, rep_count, reps, stage, score, form_fb, tip, notes):
    """دالة مساعدة لرسم واجهة المستخدم عشان الكود ميبقاش طويل"""
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (480, 320), (0, 0, 0), -1)
    cv2.addWeighted(ov, 0.45, frame, 0.55, 0, frame)
    
    # استخدم safe_text هنا لو إنت معرفها في ملفك
    cv2.putText(frame, f"{name} | Set {current_set}/{sets}", (10, 30), 2, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Angle: {angle:.1f}", (10, 65), 2, 0.7, (255, 255, 0), 2)
    cv2.putText(frame, f"Reps: {rep_count}/{reps}", (10, 110), 2, 1.1, (0, 255, 255), 3)
    
    sc_color = (0,220,0) if score>=85 else (0,200,255) if score>=60 else (0,80,255)
    cv2.putText(frame, f"Score: {score} {form_fb}", (10, 188), 2, 0.7, sc_color, 2)
    cv2.putText(frame, f"Tip: {tip}", (10, 228), 2, 0.6, (0, 165, 255), 2)

def show_rest_screen(cap, next_set, total_sets, duration):
    """شاشة الراحة"""
    for i in range(duration, 0, -1):
        ret, frame = cap.read()
        if not ret: break
        h, w, _ = frame.shape
        cv2.rectangle(frame, (0,0), (w,h), (0,0,0), -1)
        cv2.putText(frame, f"REST: {i}s", (w//2-100, h//2), 2, 2, (0, 255, 255), 3)
        cv2.putText(frame, f"Next: Set {next_set}/{total_sets}", (w//2-120, h//2+60), 2, 1, (255, 255, 255), 2)
        cv2.imshow("FormaFix", frame)
        if cv2.waitKey(1000) & 0xFF == ord('q'): break


def save_session(plan, week, day, ex_results, f="session_data.json"):
    sessions = []
    if os.path.exists(f):
        with open(f, encoding="utf-8") as fp:
            sessions = json.load(fp)

    scores = [r["avg_score"] for r in ex_results if r["avg_score"] > 0]
    session = {
        "timestamp":     datetime.now().isoformat(),
        "patient":       plan["patient"]["name"],
        "injury":        plan["patient"]["injury"],
        "week":          week, "day": day,
        "phase":         plan.get("assessment", {}).get("current_phase", 1),
        "exercises":     ex_results,
        "overall_score": round(float(np.mean(scores))) if scores else 0,
    }
    sessions.append(session)
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(sessions, fp, indent=2, ensure_ascii=False)
    print(f"\n[OK] Session saved — overall score: {session['overall_score']}/100")
    return session


    def run_session(plan_file="plan.json"):
        # 1. تحميل الخطة والبيانات الأساسية
        plan = load_plan(plan_file)
        side = get_injured_side(plan)
        side_display = "RIGHT leg" if side == "right" else "LEFT leg"

        exercises, wn, dn = select_day(plan)
        if not exercises:
            return

        # 2. إعداد الموديل والصوت (مرة واحدة خارج اللوب للأداء)
        model_path = _ensure_model()
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE
        )
        audio = AudioFeedback()
        results = []

        print(f"\n[FormaFix] Tracking: {side_display}")
        
        # استخدام context manager للموديل لضمان كفاءة الأداء
        with PoseLandmarker.create_from_options(options) as lm:
            for i, ex in enumerate(exercises, 1):
                print(f"\n{'='*50}")
                print(f"  Exercise {i}/{len(exercises)}: {ex['display']}")
                print(f"  Target: {ex['sets']} sets x {ex['reps']} reps")
                print(f"  {'='*50}")

                # ── التعديل الجوهري: الانتظار اليدوي ──────────────────────
                input("\n>>> Position yourself and press ENTER to start the camera...")

                # فتح الكاميرا لهذا التمرين فقط
                cap = cv2.VideoCapture(0)
                
                if not cap.isOpened():
                    print("[ERROR] Camera failed — skipping exercise")
                    continue

                # تنظيف الـ Buffer (أمان إضافي)
                for _ in range(5): cap.read()

                # مرحلة الـ Warm-up (تثبيت الموديل قبل العد)
                print("[FormaFix] Stabilizing pose model... Stay still.")
                for _ in range(30): 
                    ret, frame = cap.read()
                    if not ret: break
                    cv2.putText(frame, "STABILIZING... STAY STILL", (50, 50), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.imshow("FormaFix - Tracking", frame)
                    cv2.waitKey(1)

                # تشغيل التمرين الفعلي
                result = run_exercise(ex, lm, audio, cap, side=side)
                results.append(result)

                # ── التعديل الجوهري: قفل الكاميرا تماماً بعد التمرين ──────
                cap.release()
                cv2.destroyAllWindows()
                cv2.waitKey(1) # مهم جداً عشان الويندوز يقفل النافذة فعلياً
                
                print(f"\n--- Completed: {ex['display']} ---")
                print("Take a rest. Press Enter when ready for the next one.")

        # 3. حفظ نتائج الجلسة بعد انتهاء كل التمارين
        session = save_session(plan, wn, dn, results)
        print(f"\n  Session complete! Overall score: {session['overall_score']}/100")


    if __name__ == "__main__":
        run_session()