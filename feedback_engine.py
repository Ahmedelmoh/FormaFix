"""
feedback_engine.py — FormaFix
===============================
Rule-based, phase-aware feedback for each rehabilitation exercise.
Returns a plain-English instruction string based on the current joint angle.
"""


class FeedbackEngine:
    """Generates specific, phase-aware coaching cues for each exercise."""

    def get_feedback(self, exercise: str, joint_angles: dict) -> str:
        """
        Return a coaching cue for the given exercise and current joint angles.

        Parameters
        ----------
        exercise     : exercise name key (e.g. 'mini_squat')
        joint_angles : dict of {joint_name: angle_degrees}

        Returns
        -------
        str : human-readable coaching instruction
        """
        handler = self._HANDLERS.get(exercise)
        if handler is None:
            return "Keep going!"
        return handler(self, joint_angles)

    # ── Individual exercise handlers ─────────────────────────────────────────

    def _bicep_curl(self, ja: dict) -> str:
        elbow  = ja.get("left_elbow", 0)
        target = 50
        diff   = round(abs(elbow - target), 1)
        if elbow > 160:
            return f"Lower your arm — target {target}°, you are {diff}° away"
        if elbow < 40:
            return "Don't over-curl — release slightly!"
        if 50 <= elbow <= 80:
            return "Perfect curl position — hold it!"
        return f"Keep curling — {diff}° to target"

    def _squat(self, ja: dict) -> str:
        knee   = ja.get("left_knee", 0)
        target = 90
        diff   = round(abs(knee - target), 1)
        if knee > 160:
            return f"Go deeper — target {target}°, you are {diff}° away"
        if knee < 70:
            return "Too deep — come up slightly!"
        if 85 <= knee <= 110:
            return "Perfect squat depth — great form!"
        return f"Almost there — {diff}° to target"

    def _straight_leg_raise(self, ja: dict) -> str:
        hip    = ja.get("left_hip", 0)
        target = 65
        diff   = round(abs(hip - target), 1)
        if hip > 140:
            return f"Phase 1 — lift your leg up, target is {target}°"
        if 100 < hip <= 140:
            return f"Phase 2 — keep raising, {diff}° to target"
        if 55 <= hip <= 80:
            return "Phase 3 — perfect! Hold for 3 seconds"
        if hip < 55:
            return f"Too high — lower {diff}°"
        return "Raise your leg steadily"

    def _terminal_knee_extension(self, ja: dict) -> str:
        knee   = ja.get("left_knee", 0)
        target = 165
        diff   = round(abs(knee - target), 1)
        if knee < 30:
            return f"Phase 1 — start from ~45°, you are at {knee}°"
        if knee < 90:
            return f"Phase 2 — straighten your knee, {diff}° to go"
        if knee < 140:
            return f"Phase 3 — halfway there! {diff}° remaining"
        if knee < 155:
            return f"Almost there — push {diff}° more!"
        return "Full extension — excellent form!"

    def _mini_squat(self, ja: dict) -> str:
        knee   = ja.get("left_knee", 0)
        target = 125
        diff   = round(abs(knee - target), 1)
        if knee > 155:
            return f"Phase 1 — bend your knees, target is {target}°"
        if 130 <= knee <= 155:
            return f"Phase 2 — go a bit deeper, {diff}° to target"
        if 110 <= knee < 130:
            return "Phase 3 — perfect mini-squat depth!"
        return f"Too deep — come up {diff}°"

    def _hamstring_curl(self, ja: dict) -> str:
        knee   = ja.get("left_knee", 0)
        target = 95
        diff   = round(abs(knee - target), 1)
        if knee > 155:
            return f"Phase 1 — curl your leg up, target {target}°"
        if 120 <= knee <= 155:
            return f"Phase 2 — keep curling, {diff}° to target"
        if 80 <= knee < 120:
            return "Phase 3 — great curl! Hold briefly"
        return f"Too far — release {diff}°"

    def _pendulum(self, ja: dict) -> str:
        shoulder = ja.get("left_shoulder", 0)
        target   = 25
        diff     = round(abs(shoulder - target), 1)
        if shoulder < 5:
            return "Phase 1 — let your arm hang and swing gently"
        if shoulder <= 30:
            return f"Phase 2 — good pendulum! {diff}° to target"
        return f"Too much — reduce by {diff}°"

    def _external_rotation(self, ja: dict) -> str:
        elbow    = ja.get("left_elbow", 0)
        shoulder = ja.get("left_shoulder", 0)
        diff_e   = round(abs(elbow - 90), 1)
        if not (75 <= elbow <= 105):
            return f"Fix elbow first — must be 90°, you are {diff_e}° off"
        target = 70
        diff   = round(abs(shoulder - target), 1)
        if shoulder < 50:
            return f"Phase 2 — rotate outward more, {diff}° to target"
        if shoulder <= 85:
            return "Perfect rotation range — hold it!"
        return f"Too much — reduce by {diff}°"

    def _wall_slide(self, ja: dict) -> str:
        shoulder = ja.get("left_shoulder", 0)
        target   = 155
        diff     = round(abs(shoulder - target), 1)
        if shoulder < 50:
            return "Phase 1 — start with arms at shoulder height"
        if shoulder < 90:
            return f"Phase 2 — slide up, {diff}° to target"
        if shoulder < 130:
            return f"Phase 3 — halfway! {diff}° remaining"
        if shoulder <= 165:
            return "Phase 4 — excellent! Full slide reached"
        return "Stay within pain-free range"

    def _shoulder_abduction(self, ja: dict) -> str:
        shoulder = ja.get("left_shoulder", 0)
        target   = 85
        diff     = round(abs(shoulder - target), 1)
        if shoulder < 20:
            return f"Phase 1 — raise arm to the side, target {target}°"
        if shoulder < 60:
            return f"Phase 2 — keep raising, {diff}° to target"
        if shoulder <= 95:
            return "Phase 3 — perfect! Arm parallel to ground"
        return f"Too high — lower by {diff}°"

    def _shoulder_raise(self, ja: dict) -> str:
        shoulder = ja.get("left_shoulder", 0)
        target   = 90
        diff     = round(abs(shoulder - target), 1)
        if shoulder < 80:
            return f"Raise higher — {diff}° to target {target}°"
        if shoulder > 100:
            return f"Lower slightly — {diff}° above target"
        return "Perfect shoulder position!"

    # ── Dispatch table ───────────────────────────────────────────────────────
    _HANDLERS = {
        "bicep_curl":              _bicep_curl,
        "squat":                   _squat,
        "straight_leg_raise":      _straight_leg_raise,
        "terminal_knee_extension": _terminal_knee_extension,
        "mini_squat":              _mini_squat,
        "hamstring_curl":          _hamstring_curl,
        "pendulum":                _pendulum,
        "external_rotation":       _external_rotation,
        "wall_slide":              _wall_slide,
        "shoulder_abduction":      _shoulder_abduction,
        "shoulder_raise":          _shoulder_raise,
    }
