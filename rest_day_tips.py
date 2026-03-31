"""
rest_day_tips.py — FormaFix
=============================
نصايح يوم الراحة — مختلفة كل مرة — بناءً على الإصابة.
بيحاول الـ AI الأول، لو مش متاح بيستخدم نصايح offline.
"""

import random
from ai_client import ask_ai

OFFLINE_TIPS = {
    "acl": [
        "Apply ice to your knee for 15-20 minutes to reduce swelling.",
        "Keep your leg elevated above heart level when resting.",
        "Practice gentle ankle pumps to improve circulation.",
        "Focus on sleep — healing happens during deep rest. Aim for 8 hours.",
        "Stay hydrated to help your body repair tissues.",
        "Try gentle quad sets: tighten your thigh, hold 5 sec, repeat 10 times.",
        "Avoid prolonged sitting — walk slowly every 30 minutes.",
        "Eat protein-rich food (eggs, chicken, fish) to support tissue repair.",
        "Practice deep breathing to reduce stress hormones that slow healing.",
        "Check for increased swelling or warmth — if present, contact your physio.",
    ],
    "shoulder": [
        "Apply ice to your shoulder for 15-20 minutes.",
        "Do gentle pendulum exercises: let your arm hang and make small circles.",
        "Avoid lifting anything heavy — even light bags can strain a healing shoulder.",
        "Sleep on your unaffected side with a pillow supporting your arm.",
        "Gentle neck stretches relieve tension around an injured shoulder.",
        "Try shoulder blade squeezes: squeeze gently, hold 5 sec, repeat 10 times.",
        "Eat anti-inflammatory foods: berries, fatty fish, walnuts, leafy greens.",
        "Avoid reaching overhead or behind your back today.",
        "Stay hydrated — dehydration makes tendons stiffer.",
        "Visualize your shoulder healing — positive imagery aids recovery.",
    ],
    "general": [
        "Rest days are when your body actually repairs and gets stronger.",
        "A short slow walk (10-15 min) keeps blood flowing without stressing your injury.",
        "Focus on nutrition: protein for repair, vegetables for inflammation.",
        "Practice mindfulness to reduce cortisol that can slow healing.",
        "Stay hydrated — aim for 8 glasses of water today.",
        "Check that your sleeping position isn't stressing your injury.",
        "Write down your symptoms today — it helps track your progress.",
    ]
}


def get_injury_category(injury: str) -> str:
    i = injury.lower()
    if any(w in i for w in ["acl", "knee", "meniscus", "ligament", "patellar"]):
        return "acl"
    if any(w in i for w in ["shoulder", "rotator", "cuff", "labrum"]):
        return "shoulder"
    return "general"


def get_rest_day_tips(injury: str, day: int, week: int, use_ai: bool = True) -> list:
    """بيرجع 3 نصايح مختلفة ليوم الراحة."""
    if use_ai:
        try:
            tips = _get_ai_tips(injury, day, week)
            if tips:
                return tips
        except Exception:
            pass

    category = get_injury_category(injury)
    pool = OFFLINE_TIPS.get(category, OFFLINE_TIPS["general"])
    return random.sample(pool, min(3, len(pool)))


def _get_ai_tips(injury: str, day: int, week: int) -> list:
    response = ask_ai(
        messages=[{"role": "user", "content": (
            f"Patient has: {injury}. Today is Week {week}, Day {day} — REST DAY.\n"
            f"Give exactly 3 specific rest day tips.\n"
            f"Format:\n1. [tip]\n2. [tip]\n3. [tip]"
        )}],
        system_prompt=(
            "You are a physiotherapy assistant. Give practical rest day advice "
            "tailored to the injury. Each tip under 2 sentences. Be encouraging."
        )
    )
    tips = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if line and line[0].isdigit() and "." in line:
            tip = line.split(".", 1)[1].strip()
            if tip:
                tips.append(tip)
    return tips if len(tips) >= 3 else []


def show_rest_day_screen(injury: str, day: int, week: int):
    """بيعرض شاشة يوم الراحة في الـ terminal."""
    print("\n" + "="*50)
    print(f"  REST DAY  —  Week {week}, Day {day}")
    print("="*50)
    print("  Great job! Today is for recovery.\n")

    tips = get_rest_day_tips(injury, day, week)
    for i, tip in enumerate(tips, 1):
        print(f"  {i}. {tip}\n")

    print("="*50)
    print("  See you tomorrow for your next session!")
    print("="*50 + "\n")