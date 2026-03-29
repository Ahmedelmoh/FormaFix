"""
plan_generator.py — FormaFix
==============================
Fallback plan generator — بيشتغل بدون AI أو internet.

بيولّد خطة تمارين أساسية بناءً على:
  - نوع الإصابة  (acl / shoulder)
  - مستوى الألم  (1–10)

الاستخدام:
  from plan_generator import generate_basic_plan
  plan = generate_basic_plan("acl", pain_level=5, patient_name="Ahmed")
"""

from datetime import datetime

# ── Exercise pools per injury type ───────────────────────────────────────────

_ACL_GENTLE = [
    {"name": "straight_leg_raise", "sets": 3, "reps": 10,
     "rest_seconds": 30, "notes": "Keep knee fully straight throughout"},
]

_ACL_MODERATE = [
    {"name": "straight_leg_raise",      "sets": 3, "reps": 12,
     "rest_seconds": 30, "notes": "Keep knee fully straight"},
    {"name": "terminal_knee_extension", "sets": 3, "reps": 10,
     "rest_seconds": 30, "notes": "Push through full range slowly"},
]

_ACL_PROGRESSIVE = [
    {"name": "terminal_knee_extension", "sets": 3, "reps": 12,
     "rest_seconds": 30, "notes": "Full extension at the top"},
    {"name": "mini_squat",              "sets": 3, "reps": 10,
     "rest_seconds": 45, "notes": "Keep knees aligned over toes"},
    {"name": "hamstring_curl",          "sets": 3, "reps": 10,
     "rest_seconds": 30, "notes": "Slow and controlled movement"},
]

_SHOULDER_GENTLE = [
    {"name": "pendulum", "sets": 3, "reps": 10,
     "rest_seconds": 30, "notes": "Relax shoulder completely, let gravity work"},
]

_SHOULDER_MODERATE = [
    {"name": "pendulum",          "sets": 3, "reps": 12,
     "rest_seconds": 30, "notes": "Relax shoulder completely"},
    {"name": "external_rotation", "sets": 3, "reps": 10,
     "rest_seconds": 30, "notes": "Keep elbow fixed at 90 degrees"},
]

_SHOULDER_PROGRESSIVE = [
    {"name": "external_rotation",  "sets": 3, "reps": 12,
     "rest_seconds": 30, "notes": "Elbow at 90 degrees, rotate slowly"},
    {"name": "wall_slide",         "sets": 3, "reps": 10,
     "rest_seconds": 45, "notes": "Slide arms up the wall smoothly"},
    {"name": "shoulder_abduction", "sets": 3, "reps": 10,
     "rest_seconds": 30, "notes": "Raise arm to shoulder height only"},
]


def _pick_exercises(injury_type: str, pain_level: int) -> list[dict]:
    """Return the appropriate exercise list based on injury and pain."""
    gentle   = pain_level >= 7
    moderate = 4 <= pain_level <= 6

    if injury_type == "acl":
        if gentle:   return _ACL_GENTLE
        if moderate: return _ACL_MODERATE
        return _ACL_PROGRESSIVE

    if injury_type == "shoulder":
        if gentle:   return _SHOULDER_GENTLE
        if moderate: return _SHOULDER_MODERATE
        return _SHOULDER_PROGRESSIVE

    return []   # unknown injury


def _build_week(week_num: int, focus: str, exercises: list[dict]) -> dict:
    """
    Build one week with 3 active days and 4 rest days.
    Active days: 1, 3, 5  |  Rest days: 2, 4, 6, 7
    """
    days = []
    for day_num in range(1, 8):
        days.append({
            "day":       day_num,
            "exercises": exercises if day_num in (1, 3, 5) else [],
        })
    return {"week": week_num, "focus": focus, "days": days}


def generate_basic_plan(
    injury_type: str,
    pain_level: int,
    patient_name: str = "Patient",
    total_weeks: int = 4,
) -> dict:
    """
    Generate a basic rehabilitation plan without using an AI API.

    Parameters
    ----------
    injury_type  : "acl" or "shoulder"
    pain_level   : current pain 1–10
    patient_name : patient's name (stored in the plan)
    total_weeks  : how many weeks to generate (default 4)

    Returns
    -------
    dict : plan in the same format as rehab_agent.py produces,
           ready to be saved as plan.json
    """
    injury_type = injury_type.lower().strip()

    if injury_type not in ("acl", "shoulder"):
        raise ValueError(f"Unknown injury type '{injury_type}'. Choose: acl / shoulder")
    if not (1 <= pain_level <= 10):
        raise ValueError("pain_level must be between 1 and 10")

    exercises = _pick_exercises(injury_type, pain_level)

    if pain_level >= 7:
        phase             = "early_recovery"
        phase_description = "Gentle range-of-motion exercises to reduce pain and swelling"
        mobility          = "limited"
    elif pain_level >= 4:
        phase             = "mid_recovery"
        phase_description = "Progressive strengthening while managing discomfort"
        mobility          = "moderate"
    else:
        phase             = "late_recovery"
        phase_description = "Full strengthening and return-to-function exercises"
        mobility          = "good"

    week_focuses = [
        "Reduce pain and restore range of motion",
        "Build initial strength",
        "Progressive loading",
        "Functional strengthening",
    ]

    weeks = []
    for week_num in range(1, total_weeks + 1):
        focus = week_focuses[min(week_num - 1, len(week_focuses) - 1)]

        # Progressive overload: +2 reps every week
        scaled = [
            {**ex, "reps": ex["reps"] + (week_num - 1) * 2}
            for ex in exercises
        ]
        weeks.append(_build_week(week_num, focus, scaled))

    return {
        "patient": {
            "name":               patient_name,
            "age":                None,
            "injury":             injury_type.upper(),
            "injury_date":        "unknown",
            "surgery":            False,
            "surgery_date":       None,
            "pain_level":         pain_level,
            "mobility":           mobility,
            "previous_treatment": "none",
            "goal":               "Full recovery",
            "notes":              "Plan generated offline (no AI)",
        },
        "plan": {
            "total_weeks":       total_weeks,
            "phase":             phase,
            "phase_description": phase_description,
            "weeks":             weeks,
        },
        "generated_at": datetime.now().isoformat(),
        "source":       "plan_generator (offline fallback)",
    }


# ── Interactive CLI ───────────────────────────────────────────────────────────

def generate_and_save(output_file: str = "plan.json") -> dict:
    """Collect inputs from the user via CLI and save plan.json."""
    import json

    print("\n" + "=" * 45)
    print("  FormaFix — Offline Plan Generator")
    print("=" * 45)

    name = input("Patient name: ").strip() or "Patient"

    injury_type = ""
    while injury_type not in ("acl", "shoulder"):
        injury_type = input("Injury type (acl / shoulder): ").strip().lower()
        if injury_type not in ("acl", "shoulder"):
            print("  ❌ Enter 'acl' or 'shoulder'")

    pain_level = 0
    while not (1 <= pain_level <= 10):
        try:
            pain_level = int(input("Pain level (1–10): ").strip())
        except ValueError:
            pass
        if not (1 <= pain_level <= 10):
            print("  ❌ Enter a number between 1 and 10")

    plan = generate_basic_plan(injury_type, pain_level, patient_name=name)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Plan saved to {output_file}")
    print(f"   Injury : {injury_type.upper()}")
    print(f"   Phase  : {plan['plan']['phase']}")
    print(f"   Weeks  : {plan['plan']['total_weeks']}")
    print("\nNext step: python session_runner.py\n")
    return plan


if __name__ == "__main__":
    generate_and_save()