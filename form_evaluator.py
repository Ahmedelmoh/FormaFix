"""
form_evaluator.py — FormaFix
==============================
Scores exercise form (0–100) by comparing the current joint angle
against clinical reference ranges.
"""


class FormEvaluator:
    """
    Reference angles for every supported exercise.

    Each entry uses one of two formats:
      Legacy  — explicit angle keys (bicep_curl, squat, shoulder_raise)
      Current — start_angle / end_angle / tolerance / joint
    """

    REFERENCE_ANGLES: dict[str, dict] = {

        # ── Legacy exercises (min/max scoring) ──────────────────────────────
        "bicep_curl": {
            "elbow_down": 160,
            "elbow_up":    50,
        },
        "squat": {
            "knee_down": 90,
            "knee_up":  170,
        },
        "shoulder_raise": {
            "shoulder_up":   90,
            "shoulder_down": 10,
        },

        # ── ACL exercises ────────────────────────────────────────────────────

        # Patient supine, lifts leg without bending knee.
        # Measured: hip angle between trunk and thigh.
        "straight_leg_raise": {
            "start_angle": 170,
            "end_angle":    65,
            "tolerance":    15,
            "joint":       "hip",
        },

        # Patient standing, extends knee from ~45° to near full extension.
        # Measured: knee angle.
        "terminal_knee_extension": {
            "start_angle":  45,
            "end_angle":   165,
            "tolerance":    10,
            "joint":       "knee",
        },

        # Shallow squat — gentler than full squat post-ACL.
        # Measured: knee angle.
        "mini_squat": {
            "start_angle": 160,
            "end_angle":   125,
            "tolerance":    15,
            "joint":       "knee",
        },

        # Standing heel curl toward glutes.
        # Measured: knee angle.
        "hamstring_curl": {
            "start_angle": 170,
            "end_angle":    95,
            "tolerance":    15,
            "joint":       "knee",
        },

        # ── Shoulder exercises ───────────────────────────────────────────────

        # Bent-forward pendulum swings; small controlled arc.
        # Measured: shoulder angle.
        "pendulum": {
            "start_angle":   5,
            "end_angle":    25,
            "tolerance":    10,
            "joint":       "shoulder",
        },

        # Elbow fixed at 90°, forearm rotates outward.
        # Measured: elbow angle (must stay at 90°).
        "external_rotation": {
            "start_angle":  90,
            "end_angle":    70,
            "tolerance":    15,
            "joint":       "elbow",
        },

        # Arm slides up a wall from ~65° to ~155°.
        # Measured: shoulder angle.
        "wall_slide": {
            "start_angle":  65,
            "end_angle":   155,
            "tolerance":    20,
            "joint":       "shoulder",
        },

        # Lateral arm raise to shoulder height.
        # Measured: shoulder angle.
        "shoulder_abduction": {
            "start_angle":  12,
            "end_angle":    85,
            "tolerance":    15,
            "joint":       "shoulder",
        },
    }

    def evaluate(self, exercise: str, joint_name: str, current_angle: float) -> tuple[int, str]:
        """
        Score the current angle against the exercise's reference.

        Parameters
        ----------
        exercise      : exercise name key
        joint_name    : joint being measured (informational)
        current_angle : live angle from the camera

        Returns
        -------
        (score: int, feedback: str)
            score    — 0 (very wrong) to 100 (perfect)
            feedback — short coaching phrase
        """
        if exercise not in self.REFERENCE_ANGLES:
            return 100, "Exercise not configured"

        ref = self.REFERENCE_ANGLES[exercise]

        if "start_angle" not in ref:
            # Legacy min/max scoring
            angles    = list(ref.values())
            min_angle = min(angles)
            max_angle = max(angles)

            if current_angle < min_angle:
                deviation = min_angle - current_angle
            elif current_angle > max_angle:
                deviation = current_angle - max_angle
            else:
                deviation = 0

            score = max(0, 100 - int(deviation * 2))

        else:
            # Current start/end/tolerance scoring
            tol       = ref["tolerance"]
            deviation = abs(current_angle - ref["end_angle"])

            if deviation <= tol:
                score = 100
            elif deviation <= tol * 2:
                score = 75
            elif deviation <= tol * 3:
                score = 50
            else:
                score = max(0, 100 - int(deviation * 2))

        score = round(score)

        # Map score to a coaching phrase
        if score >= 90:
            feedback = "Great form!"
        elif score >= 75:
            feedback = "Almost there!"
        elif score >= 50:
            feedback = "Fix your form!"
        else:
            feedback = "Stop — incorrect position!"

        return score, feedback
