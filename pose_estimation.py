import cv2
import mediapipe as mp
import os
import urllib.request

from angle_calculator import get_all_angles
from rep_counter import RepCounter
from form_evaluator import FormEvaluator
from feedback_engine import FeedbackEngine
from exercise_selector import select_exercise
from audio_feedback import AudioFeedback
audio = AudioFeedback()
# ── MediaPipe Setup ──────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

model_path = 'pose_landmarker.task'
if not os.path.exists(model_path):
    print("Downloading pose model...")
    urllib.request.urlretrieve(
        'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
        model_path
    )
    print("Model downloaded!")

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.IMAGE
)

# ── Skeleton Connections ─────────────────────────────────────────
CONNECTIONS = [
    (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27),
    (24, 26), (26, 28),
]

# ── Joint mapping per exercise ───────────────────────────────────
JOINT_MAP = {
    'left_elbow':    'left_elbow',
    'right_elbow':   'right_elbow',
    'left_knee':     'left_knee',
    'right_knee':    'right_knee',
    'left_hip':      'left_hip',
    'left_shoulder': 'left_shoulder',
}

EXERCISE_JOINT = {
    'straight_leg_raise':      'left_hip',
    'terminal_knee_extension': 'left_knee',
    'mini_squat':              'left_knee',
    'hamstring_curl':          'left_knee',
    'pendulum':                'left_shoulder',
    'external_rotation':       'left_elbow',
    'wall_slide':              'left_shoulder',
    'shoulder_abduction':      'left_shoulder',
    'bicep_curl':              'left_elbow',
    'squat':                   'left_knee',
    'shoulder_raise':          'left_shoulder',
}

def run_pose_estimation(exercise_info):
    # Inside run_pose_estimation(exercise_info):
# 1. Initialize data tracking
all_scores = []
max_angle_reached = 0

# ... (inside the while loop) ...
if results.pose_landmarks:
    # ... (your existing logic) ...
    
    # 2. Collect data every frame
    all_scores.append(score)
    if current_angle > max_angle_reached:
        max_angle_reached = current_angle

# ... (after the while loop breaks - when user presses 'q') ...

# 3. Prepare the Session Data Bundle
if all_scores:
    session_results = {
        "exercise_name": exercise_display,
        "reps": reps,
        "avg_score": round(sum(all_scores) / len(all_scores)),
        "best_angle": max_angle_reached
    }

    # 4. Call the Agent
    from progress_agent import ProgressSummaryAgent
    summary_agent = ProgressSummaryAgent()
    
    print("\n" + "="*40)
    print("📝 GENERATING PROGRESS SUMMARY...")
    report = summary_agent.generate_report(session_results)
    print("-" * 40)
    print(report)
    print("="*40 + "\n")
    exercise_name = exercise_info['name']
    exercise_display = exercise_info['display']
    joint_key = EXERCISE_JOINT.get(exercise_name, 'left_elbow')

    counter = RepCounter()
    evaluator = FormEvaluator()
    feedback_eng = FeedbackEngine()

    cap = cv2.VideoCapture(0)

    with PoseLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = landmarker.detect(mp_image)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks[0]

                # Draw skeleton
                for start, end in CONNECTIONS:
                    x1 = int(landmarks[start].x * w)
                    y1 = int(landmarks[start].y * h)
                    x2 = int(landmarks[end].x * w)
                    y2 = int(landmarks[end].y * h)
                    cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)

                for lm in landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

                # Calculate all angles
                angles = get_all_angles(landmarks, w, h)
                current_angle = angles[joint_key]

                # Rep counter
                reps, stage = counter.count(current_angle)

                # Form evaluation
                score, form_feedback = evaluator.evaluate(
                    exercise_name, joint_key, current_angle
                )

                # Feedback engine
                tip = feedback_eng.get_feedback(exercise_name, angles)
                
                # Audio feedback لما الـ score يقل عن 75
                if score < 75:
                    audio.speak(tip)

                # ── Display ──────────────────────────────────────
                cv2.putText(frame, f'Exercise: {exercise_display}',
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.putText(frame, f'{joint_key}: {current_angle} deg',
                           (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                cv2.putText(frame, f'Reps: {reps}',
                           (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)

                cv2.putText(frame, f'Stage: {stage}',
                           (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                cv2.putText(frame, f'Score: {score}/100',
                           (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                cv2.putText(frame, form_feedback,
                           (10, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.putText(frame, tip,
                           (10, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

                # Press R to reset reps
                cv2.putText(frame, 'Press R to reset | Q to quit',
                           (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow('FormaFix', frame)

            key = cv2.waitKey(10) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                counter.reset()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    exercise = select_exercise()
    run_pose_estimation(exercise)