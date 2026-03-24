import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from angle_calculator import calculate_angle

# Initialize MediaPipe Pose
BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Download model first
import urllib.request
import os

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

def run_pose_estimation():
    cap = cv2.VideoCapture(0)
    
    with PoseLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to MediaPipe Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detect pose
            results = landmarker.detect(mp_image)
            
            # Draw landmarks + connections
            if results.pose_landmarks:
                landmarks = results.pose_landmarks[0]
                h, w, _ = frame.shape
                
                # Draw connections (skeleton)
                connections = [
                    (11, 12),
                    (11, 13), (13, 15),
                    (12, 14), (14, 16),
                    (11, 23), (12, 24),
                    (23, 24),
                    (23, 25), (25, 27),
                    (24, 26), (26, 28),
                ]
                
                for start, end in connections:
                    x1 = int(landmarks[start].x * w)
                    y1 = int(landmarks[start].y * h)
                    x2 = int(landmarks[end].x * w)
                    y2 = int(landmarks[end].y * h)
                    cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                
                # Draw points
                for landmark in landmarks:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

                # ✅ ضيف الكود الجديد هنا
                def get_point(idx):
                    return [landmarks[idx].x * w, landmarks[idx].y * h]
                
                left_elbow = calculate_angle(get_point(11), get_point(13), get_point(15))
                right_elbow = calculate_angle(get_point(12), get_point(14), get_point(16))
                left_knee = calculate_angle(get_point(23), get_point(25), get_point(27))
                
                cv2.putText(frame, f'L Elbow: {left_elbow}',
                        (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, f'R Elbow: {right_elbow}',
                        (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, f'L Knee: {left_knee}',
                        (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # cv2.putText(frame, 'FormaFix - Pose Estimation',
            #            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
            #            1, (0, 255, 0), 2)
            
            cv2.imshow('FormaFix', frame)
            
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_pose_estimation()