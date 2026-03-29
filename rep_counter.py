"""
rep_counter.py — FormaFix
==========================
Counts repetitions based on joint angle crossing two thresholds.
"""


class RepCounter:
    """
    Counts exercise repetitions using a simple up/down state machine.

    A rep is completed when the angle rises above *up_threshold* after
    having previously fallen below *down_threshold*.
    """

    def __init__(self):
        self.counter: int = 0
        self.stage: str | None = None   # "up" | "down" | None

    def count(
        self,
        angle: float,
        up_threshold: float = 160,
        down_threshold: float = 90,
    ) -> tuple[int, str | None]:
        """
        Update the rep counter based on the current angle.

        Parameters
        ----------
        angle          : current joint angle in degrees
        up_threshold   : angle above which the joint is considered "up"
        down_threshold : angle below which the joint is considered "down"

        Returns
        -------
        (counter, stage) : current rep count and stage string
        """
        if angle < down_threshold:
            self.stage = "down"
        elif angle > up_threshold and self.stage == "down":
            self.stage = "up"
            self.counter += 1

        return self.counter, self.stage

    def reset(self) -> None:
        """Reset counter and stage to initial state."""
        self.counter = 0
        self.stage   = None
