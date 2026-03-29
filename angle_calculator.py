"""
angle_calculator.py — FormaFix
================================
Utility to compute joint angles from MediaPipe landmarks.
"""

import numpy as np


def calculate_angle(a, b, c) -> float:
    """
    Calculate the angle (in degrees) at joint *b* formed by points a-b-c.

    Parameters
    ----------
    a, b, c : array-like [x, y]  (pixel coordinates)

    Returns
    -------
    float : angle in [0, 180] degrees
    """
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    c = np.array(c, dtype=float)

    radians = (
        np.arctan2(c[1] - b[1], c[0] - b[0])
        - np.arctan2(a[1] - b[1], a[0] - b[0])
    )
    angle = np.abs(np.degrees(radians))

    if angle > 180.0:
        angle = 360.0 - angle

    return round(angle, 1)


def get_all_angles(landmarks, w: int, h: int) -> dict:
    """
    Compute all clinically relevant joint angles from a MediaPipe landmark list.

    Parameters
    ----------
    landmarks : list of NormalizedLandmark (from MediaPipe)
    w, h      : frame width and height in pixels

    Returns
    -------
    dict : {joint_name: angle_degrees}
    """
    def pt(idx):
        """Convert normalized landmark to pixel coordinate."""
        return [landmarks[idx].x * w, landmarks[idx].y * h]

    return {
        # Elbow angles
        "left_elbow":     calculate_angle(pt(11), pt(13), pt(15)),
        "right_elbow":    calculate_angle(pt(12), pt(14), pt(16)),
        # Knee angles
        "left_knee":      calculate_angle(pt(23), pt(25), pt(27)),
        "right_knee":     calculate_angle(pt(24), pt(26), pt(28)),
        # Hip angles
        "left_hip":       calculate_angle(pt(11), pt(23), pt(25)),
        "right_hip":      calculate_angle(pt(12), pt(24), pt(26)),
        # Shoulder angles
        "left_shoulder":  calculate_angle(pt(13), pt(11), pt(23)),
        "right_shoulder": calculate_angle(pt(14), pt(12), pt(24)),
    }
