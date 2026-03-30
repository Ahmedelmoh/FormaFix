"""
exercise_video_generator.py — FormaFix
=======================================
بيولّد شرح مرئي للتمرين باستخدام Gemini API (مجاني).

الفكرة:
  1. Gemini بيولّد وصف دقيق للتمرين + الفريمات (start/end)
  2. بنعرض animation جوه OpenCV مع الخطوات

مستقبلاً (اختياري - مش مجاني):
  - Replicate API (Wan 2.2) لـ image-to-video حقيقي
  - هتحتاج: pip install replicate + REPLICATE_API_TOKEN في .env
"""

import json
import os
import cv2
import numpy as np
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── ألوان الـ UI ────────────────────────────────────────────────
COLOR_BG      = (20, 20, 20)
COLOR_TITLE   = (0, 255, 180)
COLOR_STEP    = (255, 255, 255)
COLOR_ACCENT  = (0, 165, 255)
COLOR_GOOD    = (0, 220, 0)
COLOR_WARN    = (0, 200, 255)
COLOR_SKELETON= (255, 255, 0)


# ══════════════════════════════════════════════════════════════════
# 1. Gemini — يولّد وصف التمرين + الفريمات
# ══════════════════════════════════════════════════════════════════

def generate_exercise_description(exercise_name: str, exercise_notes: str = "") -> dict:
    """
    بيبعت للـ Gemini عشان يولّد:
      - وصف التمرين (steps)
      - وصف start frame
      - وصف end frame
      - نصيحة للمريض
    """
    if not GEMINI_API_KEY:
        print("[WARNING] GEMINI_API_KEY مش موجود — هستخدم وصف افتراضي")
        return _default_description(exercise_name)

    prompt = f"""You are a physiotherapy expert.
Generate a clear exercise description for: {exercise_name}
Additional notes: {exercise_notes or 'None'}

Return ONLY valid JSON (no markdown, no backticks):
{{
  "title": "Exercise display name",
  "description": "One sentence what this exercise does",
  "start_frame": "Describe starting position in detail (body posture)",
  "end_frame": "Describe ending position in detail (body posture)",
  "steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "tip": "One key safety tip",
  "reps_suggestion": "e.g. 3 sets x 10 reps",
  "target_joint": "e.g. knee / shoulder / hip"
}}"""

    try:
        payload = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.3}
        }).encode("utf-8")

        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{GEMINI_MODEL}:generateContent"
               f"?key={GEMINI_API_KEY}")

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data     = json.loads(resp.read().decode("utf-8"))
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

            # نظّف الـ JSON لو Gemini حط backticks
            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            raw_text = raw_text.strip()

            return json.loads(raw_text)

    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"[ERROR] Gemini API error: {e}")
        return _default_description(exercise_name)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[ERROR] JSON parse error: {e}")
        return _default_description(exercise_name)


def _default_description(exercise_name: str) -> dict:
    """وصف افتراضي لو Gemini مش شغّال"""
    defaults = {
        "pendulum": {
            "title": "Pendulum Exercise",
            "description": "Gentle shoulder mobilization using gravity.",
            "start_frame": "Lean forward 90°, injured arm hanging freely downward.",
            "end_frame": "Arm swinging in small circles, 20-25° arc.",
            "steps": [
                "Step 1: Lean forward, support yourself with good arm on table.",
                "Step 2: Let injured arm hang completely relaxed.",
                "Step 3: Gently swing arm in small clockwise circles.",
                "Step 4: Reverse — counter-clockwise circles.",
                "Step 5: Return to start slowly."
            ],
            "tip": "Let gravity do the work — do NOT use shoulder muscles.",
            "reps_suggestion": "3 sets x 10 reps",
            "target_joint": "shoulder"
        },
        "mini_squat": {
            "title": "Mini Squat",
            "description": "Partial squat for knee strengthening post-ACL.",
            "start_frame": "Standing upright, feet shoulder-width, knee at 160°.",
            "end_frame": "Slight knee bend, knee at 125°, back straight.",
            "steps": [
                "Step 1: Stand with feet shoulder-width apart.",
                "Step 2: Hold support if needed for balance.",
                "Step 3: Slowly bend knees to ~30° (not full squat).",
                "Step 4: Hold 2 seconds at bottom.",
                "Step 5: Slowly return to standing."
            ],
            "tip": "Keep knees aligned over toes — do NOT let them cave inward.",
            "reps_suggestion": "3 sets x 15 reps",
            "target_joint": "knee"
        }
    }
    return defaults.get(exercise_name, {
        "title": exercise_name.replace("_", " ").title(),
        "description": "Rehabilitation exercise.",
        "start_frame": "Start position: body in neutral stance.",
        "end_frame": "End position: complete the movement range.",
        "steps": [
            "Step 1: Prepare in starting position.",
            "Step 2: Perform movement slowly and controlled.",
            "Step 3: Return to start."
        ],
        "tip": "Stop if you feel sharp pain.",
        "reps_suggestion": "3 sets x 10 reps",
        "target_joint": "unknown"
    })


# ══════════════════════════════════════════════════════════════════
# 2. رسم Stick Figure بسيط (Skeleton Animation)
# ══════════════════════════════════════════════════════════════════

def draw_stick_figure(frame, cx, cy, scale=1.0, phase="start",
                      exercise="pendulum", progress=0.0):
    """
    بيرسم stick figure بسيط يعكس حركة التمرين.
    phase: "start" أو "end"
    progress: 0.0 → 1.0 (للانتقال السلس)
    """
    s = scale

    def pt(dx, dy):
        return (int(cx + dx * s), int(cy + dy * s))

    # ── بيانات الـ poses حسب التمرين ─────────────────────────────
    poses = _get_pose_keypoints(exercise, progress)

    head_y   = poses["head_y"]
    torso_y  = poses["torso_y"]
    l_arm_x  = poses["l_arm_x"]
    l_arm_y  = poses["l_arm_y"]
    r_arm_x  = poses["r_arm_x"]
    r_arm_y  = poses["r_arm_y"]
    l_knee_y = poses["l_knee_y"]
    l_foot_y = poses["l_foot_y"]
    torso_lean = poses.get("torso_lean", 0)

    # Head
    cv2.circle(frame, pt(torso_lean, head_y), int(18 * s), COLOR_SKELETON, 2)

    # Torso
    cv2.line(frame, pt(torso_lean, head_y + 18), pt(torso_lean, torso_y), COLOR_SKELETON, 2)

    # Left arm (الذراع المصابة — مميزة بلون مختلف)
    shoulder = pt(torso_lean - 20, head_y + 25)
    l_elbow  = pt(torso_lean + l_arm_x // 2, head_y + 25 + l_arm_y // 2)
    l_hand   = pt(torso_lean + l_arm_x, head_y + 25 + l_arm_y)
    cv2.line(frame, shoulder, l_elbow, COLOR_ACCENT, 3)
    cv2.line(frame, l_elbow, l_hand, COLOR_ACCENT, 3)
    cv2.circle(frame, l_elbow, 5, COLOR_ACCENT, -1)

    # Right arm
    r_shoulder = pt(torso_lean + 20, head_y + 25)
    r_elbow    = pt(torso_lean + 20 + r_arm_x // 2, head_y + 25 + r_arm_y // 2)
    r_hand     = pt(torso_lean + 20 + r_arm_x, head_y + 25 + r_arm_y)
    cv2.line(frame, r_shoulder, r_elbow, COLOR_SKELETON, 2)
    cv2.line(frame, r_elbow, r_hand, COLOR_SKELETON, 2)

    # Hips
    hip_l = pt(torso_lean - 15, torso_y)
    hip_r = pt(torso_lean + 15, torso_y)
    cv2.line(frame, hip_l, hip_r, COLOR_SKELETON, 2)

    # Left leg
    l_knee = pt(torso_lean - 15, l_knee_y)
    l_foot = pt(torso_lean - 15, l_foot_y)
    cv2.line(frame, hip_l, l_knee, COLOR_SKELETON, 2)
    cv2.line(frame, l_knee, l_foot, COLOR_SKELETON, 2)
    cv2.circle(frame, l_knee, 5, COLOR_GOOD, -1)

    # Right leg (ثابت دايماً)
    r_knee = pt(torso_lean + 15, l_knee_y - 10)
    r_foot = pt(torso_lean + 15, l_foot_y)
    cv2.line(frame, hip_r, r_knee, COLOR_SKELETON, 2)
    cv2.line(frame, r_knee, r_foot, COLOR_SKELETON, 2)


def _get_pose_keypoints(exercise: str, progress: float) -> dict:
    """
    بيحسب إحداثيات الـ stick figure حسب التمرين والـ progress (0→1)
    """
    def lerp(a, b, t):
        return a + (b - a) * t

    p = progress  # 0.0 = start, 1.0 = end

    if exercise == "pendulum":
        return {
            "head_y":      lerp(-120, -80, p),   # ينحني للأمام
            "torso_y":     lerp(-60, -20, p),
            "torso_lean":  lerp(0, 30, p),
            "l_arm_x":     lerp(0, -30, p),       # ذراع تتأرجح
            "l_arm_y":     lerp(80, 70, p),        # معلقة
            "r_arm_x":     lerp(-30, -25, p),
            "r_arm_y":     lerp(20, 15, p),
            "l_knee_y":    lerp(40, 35, p),
            "l_foot_y":    lerp(100, 95, p),
        }
    elif exercise in ("mini_squat", "squat"):
        return {
            "head_y":      lerp(-120, -105, p),
            "torso_y":     lerp(-60, -45, p),
            "torso_lean":  0,
            "l_arm_x":     lerp(0, -10, p),
            "l_arm_y":     lerp(20, 25, p),
            "r_arm_x":     lerp(10, 15, p),
            "r_arm_y":     lerp(20, 25, p),
            "l_knee_y":    lerp(40, 65, p),        # ركبة تنزل
            "l_foot_y":    lerp(100, 100, p),      # قدم ثابتة
        }
    elif exercise in ("straight_leg_raise",):
        return {
            "head_y":      lerp(-120, -118, p),
            "torso_y":     lerp(-60, -58, p),
            "torso_lean":  0,
            "l_arm_x":     lerp(0, 0, p),
            "l_arm_y":     lerp(20, 20, p),
            "r_arm_x":     lerp(10, 10, p),
            "r_arm_y":     lerp(20, 20, p),
            "l_knee_y":    lerp(40, 0, p),         # رجل ترفع
            "l_foot_y":    lerp(100, 60, p),
        }
    elif exercise in ("wall_slide", "shoulder_abduction"):
        return {
            "head_y":      -120,
            "torso_y":     -60,
            "torso_lean":  0,
            "l_arm_x":     lerp(-5, -45, p),       # ذراع ترفع
            "l_arm_y":     lerp(20, -50, p),
            "r_arm_x":     lerp(10, 10, p),
            "r_arm_y":     lerp(20, 20, p),
            "l_knee_y":    40,
            "l_foot_y":    100,
        }
    elif exercise == "hamstring_curl":
        return {
            "head_y":      -120,
            "torso_y":     -60,
            "torso_lean":  0,
            "l_arm_x":     0,
            "l_arm_y":     20,
            "r_arm_x":     10,
            "r_arm_y":     20,
            "l_knee_y":    lerp(40, 40, p),
            "l_foot_y":    lerp(100, 55, p),        # رجل تتثنى للخلف
        }
    elif exercise == "external_rotation":
        return {
            "head_y":      -120,
            "torso_y":     -60,
            "torso_lean":  0,
            "l_arm_x":     lerp(-20, -40, p),
            "l_arm_y":     lerp(10, -5, p),
            "r_arm_x":     10,
            "r_arm_y":     20,
            "l_knee_y":    40,
            "l_foot_y":    100,
        }
    else:
        # default
        return {
            "head_y": -120, "torso_y": -60, "torso_lean": 0,
            "l_arm_x": lerp(0, -20, p), "l_arm_y": lerp(20, 0, p),
            "r_arm_x": 10, "r_arm_y": 20,
            "l_knee_y": 40, "l_foot_y": 100,
        }


# ══════════════════════════════════════════════════════════════════
# 3. عرض الشرح المرئي في OpenCV
# ══════════════════════════════════════════════════════════════════

def show_exercise_visual(exercise_name: str, exercise_notes: str = "",
                         sets: int = 3, reps: int = 10):
    """
    الدالة الرئيسية — بتعرض شرح التمرين مرئياً.
    اضغط SPACE للبدء، Q للخروج.
    """
    print(f"\n[FormaFix] Generating exercise guide for: {exercise_name}")
    desc = generate_exercise_description(exercise_name, exercise_notes)

    W, H = 900, 550
    frame_count = 0
    anim_speed  = 0.02   # سرعة الـ animation
    progress    = 0.0
    direction   = 1       # 1 = forward, -1 = backward

    step_idx = 0
    steps    = desc.get("steps", [])
    tip      = desc.get("tip", "")
    title    = desc.get("title", exercise_name)

    print(f"[FormaFix] Loaded: {title}")
    print(f"[FormaFix] Press SPACE to close guide and start exercise | Q to quit")

    while True:
        canvas = np.zeros((H, W, 3), dtype=np.uint8)
        canvas[:] = COLOR_BG

        # ── شريط العنوان ─────────────────────────────────────────
        cv2.rectangle(canvas, (0, 0), (W, 55), (30, 30, 30), -1)
        cv2.putText(canvas, f"FormaFix — {title}",
                    (15, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.85, COLOR_TITLE, 2)
        cv2.putText(canvas, f"{sets} sets x {reps} reps",
                    (W - 200, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_ACCENT, 2)

        # ── Animation Panel (يسار) ────────────────────────────────
        panel_w = 380
        cv2.rectangle(canvas, (10, 65), (panel_w, H - 10), (35, 35, 35), -1)

        # Labels: START / END
        p_label = "START" if progress < 0.5 else "END"
        p_color = COLOR_GOOD if progress < 0.5 else COLOR_WARN
        cv2.putText(canvas, p_label,
                    (panel_w // 2 - 35, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, p_color, 2)

        # رسم الـ stick figure
        draw_stick_figure(canvas,
                          cx=panel_w // 2, cy=H // 2 + 30,
                          scale=1.4, progress=progress,
                          exercise=exercise_name)

        # Progress bar
        bar_x, bar_y = 30, H - 35
        bar_w = panel_w - 50
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + 12),
                      (60, 60, 60), -1)
        cv2.rectangle(canvas, (bar_x, bar_y),
                      (bar_x + int(bar_w * progress), bar_y + 12),
                      COLOR_ACCENT, -1)

        # وصف الوضعية
        frame_desc = desc.get("start_frame") if progress < 0.5 else desc.get("end_frame")
        if frame_desc:
            _wrap_text(canvas, frame_desc, x=15, y=H - 70,
                       max_w=panel_w - 20, color=(180, 180, 180), scale=0.45)

        # ── Steps Panel (يمين) ───────────────────────────────────
        rx = panel_w + 20
        cv2.putText(canvas, "How to perform:",
                    (rx, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_TITLE, 1)

        for i, step in enumerate(steps[:5]):
            y_pos  = 120 + i * 55
            is_cur = (i == step_idx)
            color  = COLOR_GOOD if is_cur else (150, 150, 150)
            # highlight
            if is_cur:
                cv2.rectangle(canvas, (rx - 5, y_pos - 18),
                              (W - 10, y_pos + 32), (40, 55, 40), -1)
            _wrap_text(canvas, step, x=rx, y=y_pos,
                       max_w=W - rx - 15, color=color, scale=0.5)

        # Tip box
        tip_y = H - 65
        cv2.rectangle(canvas, (rx - 5, tip_y - 18), (W - 10, H - 12),
                      (50, 40, 20), -1)
        cv2.putText(canvas, "TIP:", (rx, tip_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1)
        _wrap_text(canvas, tip, x=rx + 45, y=tip_y,
                   max_w=W - rx - 55, color=(200, 200, 200), scale=0.48)

        # Controls hint
        cv2.putText(canvas, "SPACE = Start Exercise | Q = Quit | Arrow Keys = Steps",
                    (15, H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 100, 100), 1)

        # ── Animation update ──────────────────────────────────────
        progress += anim_speed * direction
        if progress >= 1.0:
            progress   = 1.0
            direction  = -1
        elif progress <= 0.0:
            progress  = 0.0
            direction = 1

        # تحديث الـ step تلقائياً مع الـ animation
        step_idx = min(int(progress * len(steps)), len(steps) - 1) if steps else 0

        cv2.imshow("FormaFix — Exercise Guide", canvas)

        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            cv2.destroyAllWindows()
            return False   # خروج كامل
        elif key == ord(" "):
            cv2.destroyAllWindows()
            return True    # ابدأ التمرين
        elif key == 83:    # سهم يمين — step التالي
            step_idx = min(step_idx + 1, len(steps) - 1)
        elif key == 81:    # سهم يسار — step السابق
            step_idx = max(step_idx - 1, 0)

        frame_count += 1


def _wrap_text(canvas, text, x, y, max_w, color, scale=0.5, thickness=1):
    """بيكسر النص لو طويل على أكتر من سطر"""
    words    = text.split()
    line     = ""
    line_h   = int(scale * 40)
    cur_y    = y

    for word in words:
        test = line + word + " "
        (tw, _), _ = cv2.getTextSize(test, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        if tw > max_w and line:
            cv2.putText(canvas, line.strip(), (x, cur_y),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)
            cur_y += line_h
            line   = word + " "
        else:
            line = test

    if line.strip():
        cv2.putText(canvas, line.strip(), (x, cur_y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


# ══════════════════════════════════════════════════════════════════
# 4. (اختياري/مستقبلي) Replicate — Wan 2.2 image-to-video
# ══════════════════════════════════════════════════════════════════

def generate_video_replicate(exercise_name: str, image_path: str = None) -> str | None:
    """
    ⚠️ دي مش مجانية — بتحتاج:
      1. pip install replicate
      2. REPLICATE_API_TOKEN في .env
      3. ~$0.05 لكل فيديو

    بترجع: path للفيديو المحمّل، أو None لو مش متاح
    """
    try:
        import replicate  # type: ignore
    except ImportError:
        print("[INFO] Replicate غير مثبّت — skip video generation")
        return None

    token = os.getenv("REPLICATE_API_TOKEN", "")
    if not token:
        print("[INFO] REPLICATE_API_TOKEN مش موجود — skip")
        return None

    desc = generate_exercise_description(exercise_name)
    motion_prompt = (
        f"A physiotherapy patient performing {desc['title']}. "
        f"Starting: {desc['start_frame']}. "
        f"Moving to: {desc['end_frame']}. "
        f"Slow, controlled, clinical setting, side view."
    )

    print(f"[Replicate] Generating video for: {exercise_name}")
    print(f"[Replicate] Prompt: {motion_prompt[:100]}...")

    # لو في صورة، نستخدم image-to-video
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            output = replicate.run(
                "wan-video/wan2.2-i2v-480p",
                input={
                    "image":  f,
                    "prompt": motion_prompt,
                    "num_frames": 81,
                    "fps": 16,
                }
            )
    else:
        # text-to-video لو مفيش صورة
        output = replicate.run(
            "wan-video/wan2.2-t2v-480p",
            input={
                "prompt": motion_prompt,
                "num_frames": 81,
                "fps": 16,
            }
        )

    # حمّل الفيديو
    video_url  = str(output)
    video_path = f"{exercise_name}_demo.mp4"
    urllib.request.urlretrieve(video_url, video_path)
    print(f"[Replicate] Video saved: {video_path}")
    return video_path


# ══════════════════════════════════════════════════════════════════
# اختبار مباشر
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from exercise_selector import select_exercise

    ex = select_exercise()
    show_exercise_visual(
        exercise_name  = ex["name"],
        exercise_notes = "",
        sets           = 3,
        reps           = 10
    )
