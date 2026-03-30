import numpy as np

def calculate_angle(a, b, c):
    """
    حساب الزاوية بين 3 نقاط
    a = النقطة الأولى
    b = النقطة الوسطى (المفصل)
    c = النقطة الأخيرة
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
              np.arctan2(a[1] - b[1], a[0] - b[0])
    
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
    
    return round(angle, 1)


def get_all_angles(landmarks, w, h):
    """
    بيحسب كل الزوايا المهمة مرة واحدة
    بيرجع dict فيه كل الزوايا
    """
    def pt(idx):
        return [landmarks[idx].x * w, landmarks[idx].y * h]

    angles = {
        # Elbow angles
        'left_elbow':    calculate_angle(pt(11), pt(13), pt(15)),
        'right_elbow':   calculate_angle(pt(12), pt(14), pt(16)),

        # Knee angles
        'left_knee':     calculate_angle(pt(23), pt(25), pt(27)),
        'right_knee':    calculate_angle(pt(24), pt(26), pt(28)),

        # Hip angles
        'left_hip':      calculate_angle(pt(11), pt(23), pt(25)),
        'right_hip':     calculate_angle(pt(12), pt(24), pt(26)),

        # Shoulder angles
        'left_shoulder': calculate_angle(pt(13), pt(11), pt(23)),
        'right_shoulder':calculate_angle(pt(14), pt(12), pt(24)),
    }

    return angles