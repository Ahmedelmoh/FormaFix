"""
rep_counter.py — FormaFix
==========================
Counts repetitions based on joint angle crossing two thresholds.
Supports multiple exercises with custom thresholds.
"""


class RepCounter:
    """
    Counts exercise repetitions using a simple up/down state machine.

    A rep is completed when the angle rises above *up_threshold* after
    having previously fallen below *down_threshold*.
    """

    # Exercise-specific thresholds
    EXERCISE_THRESHOLDS = {
        "bicep_curl": {"up": 160, "down": 50},
        "squat": {"up": 160, "down": 90},
        "straight_leg_raise": {"up": 140, "down": 65},
        "terminal_knee_extension": {"up": 155, "down": 45},
        "mini_squat": {"up": 155, "down": 125},
        "hamstring_curl": {"up": 170, "down": 95},
        "pendulum": {"up": 30, "down": 5},
        "external_rotation": {"up": 85, "down": 70},
        "wall_slide": {"up": 155, "down": 65},
        "shoulder_abduction": {"up": 95, "down": 12},
        "shoulder_raise": {"up": 100, "down": 80},
    }

    def __init__(self, exercise_name: str = "bicep_curl"):
        self.exercise_name = exercise_name
        self.counter = 0
        self.stage = None   # "up" | "down" | None
        
        # Get thresholds for exercise
        thresholds = self.EXERCISE_THRESHOLDS.get(exercise_name, {"up": 160, "down": 90})
        self.up_threshold = thresholds["up"]
        self.down_threshold = thresholds["down"]

    def count(
        self,
        angle: float,
        up_threshold: float = None,
        down_threshold: float = None,
    ) -> tuple[int, str | None]:
        """
        Update the rep counter based on the current angle.

        Parameters
        ----------
        angle          : current joint angle in degrees
        up_threshold   : angle above which the joint is considered "up" (uses default if None)
        down_threshold : angle below which the joint is considered "down" (uses default if None)

        Returns
        -------
        (counter, stage) : current rep count and stage string
        """
        if up_threshold is None:
            up_threshold = self.up_threshold
        if down_threshold is None:
            down_threshold = self.down_threshold

        if angle < down_threshold:
            self.stage = "down"
        elif angle > up_threshold and self.stage == "down":
            self.stage = "up"
            self.counter += 1

        return self.counter, self.stage

    def process(self, angle: float) -> dict:
        """
        Process an angle and return rep information.

        Returns dict with: {'rep_completed': bool, 'rep_count': int, 'stage': str}
        """
        stage_before = self.stage          # capture BEFORE count() mutates self.stage
        rep_count, stage_after = self.count(angle)
        # A rep completes exactly on the transition down→up, not on every "up" frame
        rep_completed = (stage_before == "down" and stage_after == "up")

        return {
            "rep_completed": rep_completed,
            "rep_count": rep_count,
            "stage": stage_after,
        }

    def reset(self) -> None:
        """Reset counter and stage to initial state."""
        self.counter = 0
        self.stage = None