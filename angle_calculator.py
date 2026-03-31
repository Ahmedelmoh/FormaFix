# import numpy as np

# def calculate_angle(a, b, c):
#     """حساب الزاوية بين 3 نقاط (x, y)"""
#     a = np.array(a)
#     b = np.array(b)
#     c = np.array(c)

#     # معادلة حساب الزاوية باستخدام arctan2
#     # $$ \theta = \arctan2(c_y-b_y, c_x-b_x) - \arctan2(a_y-b_y, a_x-b_x) $$
#     radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
#               np.arctan2(a[1] - b[1], a[0] - b[0])

#     angle = np.abs(radians * 180.0 / np.pi)
#     if angle > 180.0:
#         angle = 360 - angle

#     return round(angle, 1)

# def get_all_angles(landmarks, w, h):
#     """
#     بيحسب الزوايا والـ Visibility لكل مفصل.
#     بيرجع Dictionary بيحتوي على: {'joint_name': {'angle': float, 'vis': float}}
#     """
#     # دالة داخلية لجلب الإحداثيات والـ visibility معاً
#     def get_data(idx):
#         lm = landmarks[idx]
#         return (lm.x * w, lm.y * h), lm.visibility

#     # تعريف المفاصل المكونة لكل زاوية
#     joint_map = {
#         'left_elbow':    (11, 13, 15),
#         'right_elbow':   (12, 14, 16),
#         'left_knee':     (23, 25, 27),
#         'right_knee':    (24, 26, 28),
#         'left_hip':      (11, 23, 25),
#         'right_hip':     (12, 24, 26),
#         'left_shoulder': (13, 11, 23),
#         'right_shoulder':(14, 12, 24),
#         'left_ankle':    (25, 27, 31),
#         'right_ankle':   (26, 28, 32),
#     }

#     results = {}
#     for joint_name, (idx_a, idx_b, idx_c) in joint_map.items():
#         pt_a, vis_a = get_data(idx_a)
#         pt_b, vis_b = get_data(idx_b)
#         pt_c, vis_c = get_data(idx_c)

#         # الزاوية تعتمد على 3 نقاط، فالثقة في الزاوية هي "أقل" ثقة في أي نقطة منهم
#         # لو نقطة واحدة مختفية، الزاوية كلها مشكوك فيها
#         joint_visibility = min(vis_a, vis_b, vis_c)
        
#         angle_val = calculate_angle(pt_a, pt_b, pt_c)
        
#         results[joint_name] = {
#             'angle': angle_val,
#             'vis': round(float(joint_visibility), 2)
#         }

#     return results
# -----------------------------------





import numpy as np

def calculate_angle(a, b, c):
    """حساب الزاوية بين 3 نقاط (x, y)"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    # معادلة حساب الزاوية باستخدام arctan2
    # $$ \theta = \arctan2(c_y-b_y, c_x-b_x) - \arctan2(a_y-b_y, a_x-b_x) $$
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
              np.arctan2(a[1] - b[1], a[0] - b[0])

    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle

    return round(angle, 1)

def get_all_angles(landmarks, w, h):
    """
    بيحسب الزوايا والـ Visibility لكل مفصل.
    بيرجع Dictionary بيحتوي على: {'joint_name': {'angle': float, 'vis': float}}
    """
    # دالة داخلية لجلب الإحداثيات والـ visibility معاً
    def get_data(idx):
        lm = landmarks[idx]
        return (lm.x * w, lm.y * h), lm.visibility

    # تعريف المفاصل المكونة لكل زاوية
    joint_map = {
        'left_elbow':    (11, 13, 15),
        'right_elbow':   (12, 14, 16),
        'left_knee':     (23, 25, 27),
        'right_knee':    (24, 26, 28),
        'left_hip':      (11, 23, 25),
        'right_hip':     (12, 24, 26),
        'left_shoulder': (13, 11, 23),
        'right_shoulder':(14, 12, 24),
        'left_ankle':    (25, 27, 31),
        'right_ankle':   (26, 28, 32),
    }

    results = {}
    for joint_name, (idx_a, idx_b, idx_c) in joint_map.items():
        pt_a, vis_a = get_data(idx_a)
        pt_b, vis_b = get_data(idx_b)
        pt_c, vis_c = get_data(idx_c)

        # الزاوية تعتمد على 3 نقاط، فالثقة في الزاوية هي "أقل" ثقة في أي نقطة منهم
        # لو نقطة واحدة مختفية، الزاوية كلها مشكوك فيها
        joint_visibility = min(vis_a, vis_b, vis_c)
        
        angle_val = calculate_angle(pt_a, pt_b, pt_c)
        
        results[joint_name] = {
            'angle': angle_val,
            'vis': round(float(joint_visibility), 2)
        }

    return results