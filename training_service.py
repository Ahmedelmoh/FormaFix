"""
training_service.py — FormaFix
===============================
Service for managing training sessions with pose estimation and real-time feedback.
Integrates MediaPipe, feedback_engine, and form_evaluator.
"""

import cv2
import numpy as np
import mediapipe as mp
import os
import urllib.request
from angle_calculator import get_all_angles
from feedback_engine import FeedbackEngine
from form_evaluator import FormEvaluator
from rep_counter import RepCounter
from database_service import DatabaseService
from audio_feedback import AudioFeedback

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

MODEL_PRIMARY_PATH = "pose_landmarker_lite.task"
MODEL_FALLBACK_PATH = "pose_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)


def _ensure_pose_model() -> str:
    """Ensure a pose model exists locally and return its path."""
    if os.path.exists(MODEL_PRIMARY_PATH):
        return MODEL_PRIMARY_PATH
    if os.path.exists(MODEL_FALLBACK_PATH):
        return MODEL_FALLBACK_PATH
    urllib.request.urlretrieve(MODEL_URL, MODEL_PRIMARY_PATH)
    return MODEL_PRIMARY_PATH


class TrainingSession:
    """Manages a single exercise training session."""

    def __init__(self, exercise_name: str, target_reps: int = 10):
        self.exercise_name = exercise_name
        self.target_reps = target_reps
        self.reps_completed = 0
        self.scores = []
        self.frames_processed = 0
        self.session_active = True

        self.feedback_engine = FeedbackEngine()
        self.form_evaluator = FormEvaluator()
        self.rep_counter = RepCounter(exercise_name)
        self.db = DatabaseService()
        self.audio = AudioFeedback()

        # MediaPipe setup — use IMAGE (synchronous) mode; LIVE_STREAM requires a callback
        model_path = _ensure_pose_model()
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
        )
        self.pose_landmarker = PoseLandmarker.create_from_options(options)

    def process_frame(self, frame, counting_enabled: bool = True) -> dict:
        """
        Process a frame and return feedback/score.
        Returns dict with: {'feedback': str, 'score': int, 'rep_detected': bool, 'frame': processed_frame}
        """
        self.frames_processed += 1

        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape

        # Detect pose (synchronous — detect() returns a result object directly)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.pose_landmarker.detect(mp_image)

        feedback = "Detecting pose..."
        score = 0
        rep_detected = False
        current_angle = 0
        display_frame = frame.copy()

        if result and result.pose_landmarks:
            landmarks = result.pose_landmarks[0]

            # Calculate angles
            angles = get_all_angles(landmarks, w, h)

            # Choose best visible side for target joint (left/right fallback).
            left_joint, right_joint = self._get_joint_candidates()
            joint_name, current_angle = self._pick_joint_angle(angles, left_joint, right_joint)

            # Feedback engine uses left-side keys; mirror when right side was selected.
            if left_joint not in angles and right_joint in angles:
                angles[left_joint] = angles[right_joint]
            elif current_angle > 0 and joint_name == right_joint:
                angles[left_joint] = current_angle

            # Get feedback
            feedback = self.feedback_engine.get_feedback(self.exercise_name, angles)

            # Evaluate form
            score, form_feedback = self.form_evaluator.evaluate(self.exercise_name, joint_name, current_angle)

            # Count reps only after readiness gate is satisfied.
            if counting_enabled:
                rep_info = self.rep_counter.process(current_angle)
                if rep_info["rep_completed"]:
                    rep_detected = True
                    self.reps_completed += 1
            else:
                feedback = "Hold steady in full frame. Counting will start when body points are clear."

            self.scores.append(score)

            # Draw skeleton on frame
            display_frame = self._draw_skeleton(frame, landmarks, w, h)
            self._draw_angle(display_frame, {joint_name: current_angle}, joint_name)

        # Add text overlay
        cv2.putText(display_frame, f"Score: {score}/100", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Reps: {self.reps_completed}/{self.target_reps}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_frame, feedback, (10, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return {
            "feedback": feedback,
            "score": score,
            "rep_detected": rep_detected,
            "frame": display_frame,
            "angle": current_angle
        }

    @staticmethod
    def _landmarks_ready(landmarks, visibility_threshold: float = 0.5) -> bool:
        """Return True when required body points are visible enough to start counting."""
        required_indices = [11, 12, 13, 14, 23, 24, 25, 26]
        for idx in required_indices:
            if idx >= len(landmarks) or landmarks[idx].visibility < visibility_threshold:
                return False
        return True

    def _get_exercise_joint(self) -> str:
        """Get the primary joint being measured for this exercise."""
        exercise_joints = {
            "straight_leg_raise": "left_hip",
            "terminal_knee_extension": "left_knee",
            "mini_squat": "left_knee",
            "hamstring_curl": "left_knee",
            "pendulum": "left_shoulder",
            "external_rotation": "left_elbow",
            "wall_slide": "left_shoulder",
            "shoulder_abduction": "left_shoulder",
            "bicep_curl": "left_elbow",
            "squat": "left_knee",
            "shoulder_raise": "left_shoulder",
        }
        return exercise_joints.get(self.exercise_name, "left_knee")

    def _get_joint_candidates(self) -> tuple[str, str]:
        """Return left/right joint candidates for the exercise."""
        left_joint = self._get_exercise_joint()
        right_joint = left_joint.replace("left_", "right_") if left_joint.startswith("left_") else left_joint
        return left_joint, right_joint

    @staticmethod
    def _pick_joint_angle(angles: dict, left_joint: str, right_joint: str) -> tuple[str, float]:
        """Pick best available angle between left and right joint values."""
        left_val = float(angles.get(left_joint, 0) or 0)
        right_val = float(angles.get(right_joint, 0) or 0)

        if left_val > 0 and right_val > 0:
            # Prefer the side closer to target mid-range to reduce noisy side selection.
            if abs(left_val - 90.0) <= abs(right_val - 90.0):
                return left_joint, left_val
            return right_joint, right_val
        if left_val > 0:
            return left_joint, left_val
        if right_val > 0:
            return right_joint, right_val
        return left_joint, 0.0

    @staticmethod
    def _open_best_camera(max_indices: int = 5):
        """Try available camera indices/backends and return the first working capture."""
        backends = [None]
        if hasattr(cv2, "CAP_DSHOW"):
            backends.append(cv2.CAP_DSHOW)
        if hasattr(cv2, "CAP_MSMF"):
            backends.append(cv2.CAP_MSMF)

        for backend in backends:
            for index in range(max_indices):
                cap = cv2.VideoCapture(index) if backend is None else cv2.VideoCapture(index, backend)

                if cap is None or not cap.isOpened():
                    if cap is not None:
                        cap.release()
                    continue

                ok, _ = cap.read()
                if ok:
                    return cap
                cap.release()

        return None

    @staticmethod
    def _draw_skeleton(frame, landmarks, w: int, h: int):
        """Draw body skeleton on frame."""
        # Define connections between joints
        connections = [
            (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
            (11, 23), (12, 24), (23, 24),
            (23, 25), (25, 27), (24, 26), (26, 28),
        ]

        # Draw joints
        for landmark in landmarks:
            if landmark.visibility > 0.5:
                x, y = int(landmark.x * w), int(landmark.y * h)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        # Draw connections
        for start, end in connections:
            if landmarks[start].visibility > 0.5 and landmarks[end].visibility > 0.5:
                start_pos = (int(landmarks[start].x * w), int(landmarks[start].y * h))
                end_pos = (int(landmarks[end].x * w), int(landmarks[end].y * h))
                cv2.line(frame, start_pos, end_pos, (0, 255, 0), 2)

        return frame

    @staticmethod
    def _draw_angle(frame, angles: dict, joint_name: str):
        """Draw the measured angle on frame."""
        angle = angles.get(joint_name, 0)
        cv2.putText(frame, f"{joint_name}: {angle}°", (10, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    def get_session_summary(self) -> dict:
        """Get summary of the training session."""
        avg_score = round(np.mean(self.scores), 1) if self.scores else 0
        max_score = max(self.scores) if self.scores else 0
        min_score = min(self.scores) if self.scores else 0

        return {
            "exercise": self.exercise_name,
            "reps_completed": self.reps_completed,
            "target_reps": self.target_reps,
            "avg_score": avg_score,
            "best_score": max_score,
            "worst_score": min_score,
            "frames_processed": self.frames_processed,
        }

    def end_session(self):
        """End the training session."""
        self.session_active = False
        self.pose_landmarker.close()

    def run_live_camera_session(self, require_clear_start: bool = True, clear_frames_needed: int = 8) -> dict:
        """Run live camera session; optionally gate counting until posture is clear."""
        cap = self._open_best_camera()

        if cap is None or not cap.isOpened():
            raise RuntimeError("Could not detect/open a camera device")

        clear_frames = 0
        counting_enabled = not require_clear_start

        try:
            while cap.isOpened() and self.session_active:
                ret, frame = cap.read()
                if not ret:
                    break

                if require_clear_start and not counting_enabled:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                    result = self.pose_landmarker.detect(mp_image)

                    if result and result.pose_landmarks:
                        if self._landmarks_ready(result.pose_landmarks[0]):
                            clear_frames += 1
                        else:
                            clear_frames = 0
                    else:
                        clear_frames = 0

                    if clear_frames >= max(1, clear_frames_needed):
                        counting_enabled = True
                        self.audio.speak("Body detected. Counting started.")

                info = self.process_frame(frame, counting_enabled=counting_enabled)
                display = info["frame"]

                # Speak corrections when quality is poor.
                if info["score"] < 75 and info["feedback"] != "Detecting pose...":
                    self.audio.speak(info["feedback"])

                cv2.putText(
                    display,
                    "Press Q to quit",
                    (10, display.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (200, 200, 200),
                    1,
                )

                if not counting_enabled:
                    cv2.putText(
                        display,
                        "Align full body in frame. Counting is paused.",
                        (10, display.shape[0] - 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 200, 255),
                        2,
                    )

                cv2.imshow("FormaFix Live Training", display)

                if self.reps_completed >= self.target_reps:
                    self.audio.speak("Great job. Target reps completed.")
                    break

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.end_session()

        return self.get_session_summary()


def detect_body_points_precheck(timeout_sec: int = 6, visibility_threshold: float = 0.5) -> dict:
    """Open camera briefly and verify all key body points are visible."""
    model_path = _ensure_pose_model()
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.IMAGE,
    )

    required_points = {
        11: "left_shoulder",
        12: "right_shoulder",
        13: "left_elbow",
        14: "right_elbow",
        15: "left_wrist",
        16: "right_wrist",
        23: "left_hip",
        24: "right_hip",
        25: "left_knee",
        26: "right_knee",
        27: "left_ankle",
        28: "right_ankle",
    }

    cap = TrainingSession._open_best_camera()
    if cap is None or not cap.isOpened():
        return {
            "ok": False,
            "message": "Could not detect/open a camera device",
            "detected_points": [],
            "missing_points": list(required_points.values()),
        }

    max_frames = max(30, int(timeout_sec * 10))
    detected = set()

    with PoseLandmarker.create_from_options(options) as landmarker:
        try:
            frames = 0
            while cap.isOpened() and frames < max_frames:
                ret, frame = cap.read()
                if not ret:
                    frames += 1
                    continue

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                result = landmarker.detect(mp_image)

                if result and result.pose_landmarks:
                    landmarks = result.pose_landmarks[0]
                    for idx, name in required_points.items():
                        if idx < len(landmarks) and landmarks[idx].visibility >= visibility_threshold:
                            detected.add(name)

                    if len(detected) == len(required_points):
                        break

                frames += 1
        finally:
            cap.release()
            cv2.destroyAllWindows()

    missing = [name for name in required_points.values() if name not in detected]
    ok = len(missing) == 0
    return {
        "ok": ok,
        "message": "All body points detected" if ok else "Some body points are not visible",
        "detected_points": sorted(list(detected)),
        "missing_points": missing,
    }