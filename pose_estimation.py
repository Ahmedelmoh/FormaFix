"""
pose_estimation.py — FormaFix  (fixed)
=======================================
Fixes applied:
  1. Exercise selector screen before starting
  2. Angle smoothing (moving average) to avoid noise
  3. ASCII-only text in OpenCV (no more ???)
  4. Press M to return to menu
"""

import cv2
import mediapipe as mp
import numpy as np
import urllib.request
import os
from collections import deque

from angle_calculator import calculate_angle
from rep_counter      import RepCounter
from form_evaluator   import FormEvaluator
from feedback_engine  import FeedbackEngine

# ─────────────────────────────────────────────────────────────────────────────
# EXERCISE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
EXERCISE_CONFIG = {
    'bicep_curl': {
        'display_name':   'Bicep Curl',
        'joint_key':      'left_elbow',
        'angle_points':   (11, 13, 15),
        'angles_dict':    lambda a: {'left_elbow': a},
        'up_threshold':   160,
        'down_threshold':  40,
    },
    'squat': {
        'display_name':   'Squat',
        'joint_key':      'left_knee',
        'angle_points':   (23, 25, 27),
        'angles_dict':    lambda a: {'left_knee': a},
        'up_threshold':   160,
        'down_threshold':  80,
    },
    'shoulder_raise': {
        'display_name':   'Shoulder Raise',
        'joint_key':      'left_shoulder',
        'angle_points':   (23, 11, 13),
        'angles_dict':    lambda a: {'left_shoulder': a},
        'up_threshold':    85,
        'down_threshold':  20,
    },
    'straight_leg_raise': {
        'display_name':   'Straight Leg Raise (ACL)',
        'joint_key':      'left_hip',
        'angle_points':   (11, 23, 25),
        'angles_dict':    lambda a: {'left_hip': a},
        'up_threshold':   160,
        'down_threshold':  70,
    },
    'terminal_knee_extension': {
        'display_name':   'Terminal Knee Extension (ACL)',
        'joint_key':      'left_knee',
        'angle_points':   (23, 25, 27),
        'angles_dict':    lambda a: {'left_knee': a},
        'up_threshold':   155,
        'down_threshold':  50,
    },
    'mini_squat': {
        'display_name':   'Mini Squat (ACL)',
        'joint_key':      'left_knee',
        'angle_points':   (23, 25, 27),
        'angles_dict':    lambda a: {'left_knee': a},
        'up_threshold':   150,
        'down_threshold': 115,
    },
    'hamstring_curl': {
        'display_name':   'Hamstring Curl (ACL)',
        'joint_key':      'left_knee',
        'angle_points':   (23, 25, 27),
        'angles_dict':    lambda a: {'left_knee': a},
        'up_threshold':   155,
        'down_threshold':  95,
    },
    'pendulum': {
        'display_name':   'Pendulum (Shoulder)',
        'joint_key':      'left_shoulder',
        'angle_points':   (23, 11, 13),
        'angles_dict':    lambda a: {'left_shoulder': a},
        'up_threshold':    25,
        'down_threshold':   5,
    },
    'external_rotation': {
        'display_name':   'External Rotation (Shoulder)',
        'joint_key':      'left_elbow',
        'angle_points':   (11, 13, 15),
        'angles_dict':    lambda a: {'left_elbow': a, 'left_shoulder': a},
        'up_threshold':    85,
        'down_threshold':  60,
    },
    'wall_slide': {
        'display_name':   'Wall Slide (Shoulder)',
        'joint_key':      'left_shoulder',
        'angle_points':   (23, 11, 13),
        'angles_dict':    lambda a: {'left_shoulder': a},
        'up_threshold':   145,
        'down_threshold':  65,
    },
    'shoulder_abduction': {
        'display_name':   'Shoulder Abduction',
        'joint_key':      'left_shoulder',
        'angle_points':   (23, 11, 13),
        'angles_dict':    lambda a: {'left_shoulder': a},
        'up_threshold':    75,
        'down_threshold':  15,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# FIX 3: strip non-ASCII so OpenCV never shows ???
# ─────────────────────────────────────────────────────────────────────────────
def safe_text(text):
    return text.encode('ascii', errors='replace').decode('ascii')


# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: Exercise selector screen
# ─────────────────────────────────────────────────────────────────────────────
def show_exercise_selector():
    """
    Opens a window listing all exercises.
    User presses the number key (1-9) to select.
    Returns the exercise name string, or None if ESC pressed.
    """
    exercises = list(EXERCISE_CONFIG.keys())
    win_h     = 80 + len(exercises) * 46 + 50
    canvas    = np.zeros((win_h, 660, 3), dtype=np.uint8)

    cv2.putText(canvas, 'FormaFix  -  Select Exercise',
                (20, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 255, 200), 2)

    for i, ex in enumerate(exercises):
        y     = 88 + i * 46
        label = f"  [{i+1}]  {EXERCISE_CONFIG[ex]['display_name']}"
        color = (200, 200, 200)
        cv2.putText(canvas, label,
                    (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.68, color, 1)

    cv2.putText(canvas, 'Press number to select  |  ESC to quit',
                (20, win_h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (100, 100, 100), 1)

    cv2.imshow('FormaFix', canvas)

    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == 27:
            return None
        if ord('1') <= key <= ord('9'):
            idx = key - ord('1')
            if idx < len(exercises):
                return exercises[idx]


# ─────────────────────────────────────────────────────────────────────────────
# Model download
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_model():
    model_path = 'pose_landmarker.task'
    if not os.path.exists(model_path):
        print("Downloading pose model...")
        urllib.request.urlretrieve(
            'https://storage.googleapis.com/mediapipe-models/pose_landmarker/'
            'pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
            model_path
        )
        print("Model downloaded!")
    return model_path


# ─────────────────────────────────────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────────────────────────────────────
def run_pose_estimation(exercise=None, source=0):
    """
    exercise : str or None  (None = show selector)
    source   : 0 = webcam  |  'path/to/video.mp4'
    """

    # FIX 1: show selector if no exercise given
    if exercise is None:
        exercise = show_exercise_selector()
        if exercise is None:
            print("No exercise selected. Exiting.")
            cv2.destroyAllWindows()
            return

    if exercise not in EXERCISE_CONFIG:
        print(f"[ERROR] Exercise '{exercise}' not found.")
        print(f"Available: {list(EXERCISE_CONFIG.keys())}")
        return

    cfg = EXERCISE_CONFIG[exercise]
    print(f"[FormaFix] Starting: {cfg['display_name']}")
    print("Keys: Q = quit  |  R = reset reps  |  M = back to menu")

    feedback_engine = FeedbackEngine()
    evaluator       = FormEvaluator()
    counter         = RepCounter()

    # FIX 2: smoothing buffer — last 5 readings
    angle_buffer = deque(maxlen=5)

    model_path            = _ensure_model()
    BaseOptions           = mp.tasks.BaseOptions
    PoseLandmarker        = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode     = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.IMAGE
    )

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source}")
        return

    go_to_menu = False

    with PoseLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                if isinstance(source, str):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

            h, w, _ = frame.shape

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB,
                                 data=rgb_frame)
            results   = landmarker.detect(mp_image)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks[0]

                def get_point(idx):
                    return [landmarks[idx].x * w, landmarks[idx].y * h]

                _draw_skeleton(frame, landmarks, w, h)

                a_idx, b_idx, c_idx = cfg['angle_points']
                raw_angle = calculate_angle(
                    get_point(a_idx),
                    get_point(b_idx),
                    get_point(c_idx)
                )

                # FIX 2: smoothed angle
                angle_buffer.append(raw_angle)
                smooth_angle = float(np.mean(angle_buffer))

                reps, stage = counter.count(
                    smooth_angle,
                    up_threshold   = cfg['up_threshold'],
                    down_threshold = cfg['down_threshold']
                )

                score, eval_fb = evaluator.evaluate(
                    exercise, cfg['joint_key'], smooth_angle
                )

                angles_dict = cfg['angles_dict'](smooth_angle)
                tip = feedback_engine.get_feedback(exercise, angles_dict)

                _draw_info(frame, cfg['display_name'], smooth_angle,
                           reps, stage, score, eval_fb, tip,
                           cfg['joint_key'])

            cv2.imshow('FormaFix', frame)

            key = cv2.waitKey(10) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                counter.reset()
                angle_buffer.clear()
                print("[FormaFix] Reps reset.")
            elif key == ord('m'):
                go_to_menu = True
                break

    cap.release()
    cv2.destroyAllWindows()

    # back to menu
    if go_to_menu:
        run_pose_estimation(exercise=None, source=source)


# ─────────────────────────────────────────────────────────────────────────────
# Skeleton drawing
# ─────────────────────────────────────────────────────────────────────────────
def _draw_skeleton(frame, landmarks, w, h):
    connections = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24),
        (23, 25), (25, 27), (24, 26), (26, 28),
    ]
    for s, e in connections:
        x1 = int(landmarks[s].x * w);  y1 = int(landmarks[s].y * h)
        x2 = int(landmarks[e].x * w);  y2 = int(landmarks[e].y * h)
        cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
    for lm in landmarks:
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 5, (0, 255, 0), -1)


# ─────────────────────────────────────────────────────────────────────────────
# Info overlay  — FIX 3: all text goes through safe_text()
# ─────────────────────────────────────────────────────────────────────────────
def _draw_info(frame, display_name, angle, reps, stage,
               score, eval_fb, tip, joint_key):

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (470, 335), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    cv2.putText(frame, safe_text(f'Exercise: {display_name}'),
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    cv2.putText(frame, safe_text(f'{joint_key}: {angle:.1f} deg'),
                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 0), 2)

    cv2.putText(frame, safe_text(f'Reps: {reps}'),
                (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.10, (0, 255, 255), 3)

    cv2.putText(frame, safe_text(f'Stage: {stage if stage else "ready"}'),
                (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

    score_color = (0, 220, 0) if score >= 85 else \
                  (0, 200, 255) if score >= 60 else (0, 80, 255)

    cv2.putText(frame, safe_text(f'Score: {score}/100'),
                (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.80, score_color, 2)

    cv2.putText(frame, safe_text(eval_fb),
                (10, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.70, score_color, 2)

    cv2.putText(frame, safe_text(tip),
                (10, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 165, 255), 2)

    cv2.putText(frame, 'Q:quit  R:reset  M:menu',
                (10, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (150, 150, 150), 1)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='FormaFix Pose Estimation')
    parser.add_argument('--exercise', '-e', type=str, default=None,
                        help='Exercise name (omit to show selector screen)')
    parser.add_argument('--source',   '-s', default='0',
                        help='0=webcam  or  path/to/video.mp4')
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    run_pose_estimation(exercise=args.exercise, source=source)