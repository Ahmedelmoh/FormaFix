"""
adaptive_plan.py — FormaFix
=============================
كل أسبوع الـ AI بيشوف أداء المريض ويعدّل الخطة أوتوماتيك.

Logic:
  - avg score >= 80  → progress  (زود sets/reps أو انتقل للمرحلة الجاية)
  - avg score 60-79  → maintain  (فضل على نفس الخطة)
  - avg score < 60   → regress   (خفف التمارين)

بيقرأ  : plan.json + session_data.json
بيكتب  : plan.json (نسخة محدّثة) + plan_backup_YYYYMMDD.json
"""

import json
import os
import shutil
from datetime import datetime
from ai_client import ask_ai, PROVIDER


AVAILABLE_EXERCISES = [
    "straight_leg_raise",
    "terminal_knee_extension",
    "mini_squat",
    "hamstring_curl",
    "pendulum",
    "external_rotation",
    "wall_slide",
    "shoulder_abduction",
]


def load_json(filename: str) -> dict | list:
    with open(filename, encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_week_stats(sessions: list, week: int) -> dict:
    """بيحسب إحصائيات أسبوع معين من الـ sessions."""
    week_sessions = [s for s in sessions if s.get("week") == week]

    if not week_sessions:
        return {"sessions": 0, "avg_score": 0, "exercises": {}}

    scores        = [s["overall_score"] for s in week_sessions]
    avg_score     = round(sum(scores) / len(scores)) if scores else 0

    # إحصائيات كل تمرين
    exercise_stats = {}
    for session in week_sessions:
        for ex in session.get("exercises", []):
            name = ex["name"]
            if name not in exercise_stats:
                exercise_stats[name] = {"scores": [], "completed_sets": [], "target_sets": []}
            exercise_stats[name]["scores"].append(ex.get("avg_score", 0))
            exercise_stats[name]["completed_sets"].append(ex.get("completed_sets", 0))
            exercise_stats[name]["target_sets"].append(ex.get("target_sets", 0))

    # ابسط الإحصائيات
    for name, data in exercise_stats.items():
        s = data["scores"]
        c = data["completed_sets"]
        t = data["target_sets"]
        exercise_stats[name] = {
            "avg_score":       round(sum(s) / len(s)) if s else 0,
            "completion_rate": round(sum(c) / sum(t) * 100) if sum(t) > 0 else 0,
        }

    return {
        "week":        week,
        "sessions":    len(week_sessions),
        "avg_score":   avg_score,
        "exercises":   exercise_stats,
    }


def decide_adaptation(avg_score: int) -> str:
    """بيقرر نوع التعديل بناءً على الأداء."""
    if avg_score >= 80:
        return "progress"
    elif avg_score >= 60:
        return "maintain"
    else:
        return "regress"


def get_ai_adaptation(plan: dict, week_stats: dict, all_sessions: list) -> dict:
    """
    بيبعت الخطة الحالية والأداء لـ AI ويطلب منه يعمل خطة معدّلة.
    بيرجع plan dict جديد.
    """

    adaptation = decide_adaptation(week_stats["avg_score"])

    # ابني ملخص الأداء
    ex_lines = []
    for name, stats in week_stats["exercises"].items():
        ex_lines.append(
            f"  - {name}: score {stats['avg_score']}/100, "
            f"completion {stats['completion_rate']}%"
        )

    # آخر 5 sessions للسياق
    recent = all_sessions[-5:]
    history_lines = [
        f"  Week {s['week']} Day {s['day']}: {s['overall_score']}/100"
        for s in recent
    ]

    prompt = f"""
You are a physiotherapy AI updating a patient's rehabilitation plan.

CURRENT PLAN:
{json.dumps(plan['plan'], indent=2)}

PATIENT INFO:
- Injury: {plan['patient']['injury']}
- Current phase: {plan['plan']['phase']}
- Total weeks planned: {plan['plan']['total_weeks']}

WEEK {week_stats['week']} PERFORMANCE:
- Sessions completed: {week_stats['sessions']}
- Average score: {week_stats['avg_score']}/100
- Adaptation decision: {adaptation.upper()}
- Exercise breakdown:
{chr(10).join(ex_lines)}

RECENT HISTORY:
{chr(10).join(history_lines)}

ADAPTATION RULES:
- PROGRESS  (score >= 80): increase reps by 2-3, or sets by 1, or add harder exercise
- MAINTAIN  (score 60-79): keep same exercises, same sets/reps
- REGRESS   (score < 60) : reduce reps by 2-3, or sets by 1, or replace hard exercises with easier ones

IMPORTANT:
- Only use these exercises: {json.dumps(AVAILABLE_EXERCISES)}
- Keep the same plan structure (weeks/days format)
- Update the next week(s) only, keep completed weeks unchanged
- Adjust phase if appropriate (early_recovery → mid_recovery → late_recovery)
- Return ONLY the updated plan JSON, no extra text

Return the complete updated plan in this exact format:
```json
{{
  "total_weeks": number,
  "phase": "string",
  "phase_description": "string",
  "weeks": [...]
}}
```
"""

    response = ask_ai(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=(
            "You are a physiotherapy AI. Return only valid JSON. "
            "No explanations, no markdown outside the json block."
        )
    )

    # استخرج الـ JSON
    import re
    match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if match:
        updated_plan_section = json.loads(match.group(1))
    else:
        # لو مفيش ``` حاول تحلل الرد مباشرة
        updated_plan_section = json.loads(response.strip())

    return updated_plan_section


def apply_offline_adaptation(plan: dict, week_stats: dict) -> dict:
    """
    تعديل بسيط بدون AI — لو الـ API مش متاح.
    بيعدل الـ reps/sets بناءً على الأداء.
    """
    adaptation = decide_adaptation(week_stats["avg_score"])
    current_week = week_stats["week"]

    updated_plan = json.loads(json.dumps(plan))  # deep copy

    for week in updated_plan["plan"]["weeks"]:
        # عدّل الأسابيع الجاية بس
        if week["week"] <= current_week:
            continue

        for day in week["days"]:
            for ex in day.get("exercises", []):
                if adaptation == "progress":
                    ex["reps"]  = min(ex["reps"] + 2, 20)
                    ex["notes"] = "Increased — good progress last week!"
                elif adaptation == "regress":
                    ex["reps"]  = max(ex["reps"] - 2, 5)
                    ex["notes"] = "Reduced — focus on form this week."

    return updated_plan


def run_adaptive_plan(plan_file="plan.json", session_file="session_data.json"):
    """الدالة الرئيسية."""

    print("\n" + "="*50)
    print("   FormaFix — Adaptive Plan")
    print(f"   AI: {PROVIDER.upper()}")
    print("="*50)

    # قرأ الملفات
    if not os.path.exists(plan_file):
        print("[ERROR] plan.json not found. Run rehab_agent.py first.")
        return
    if not os.path.exists(session_file):
        print("[ERROR] session_data.json not found. Complete at least one session.")
        return

    plan     = load_json(plan_file)
    sessions = load_json(session_file)

    if not sessions:
        print("[ERROR] No sessions found.")
        return

    # اعرض الأسابيع المتاحة
    completed_weeks = sorted(set(s["week"] for s in sessions))
    print(f"\n  Completed weeks: {completed_weeks}")

    week_num = int(input("\n  Analyze which week? ").strip())

    # احسب إحصائيات الأسبوع
    stats = get_week_stats(sessions, week_num)

    if stats["sessions"] == 0:
        print(f"[ERROR] No sessions found for week {week_num}.")
        return

    adaptation = decide_adaptation(stats["avg_score"])

    print(f"\n  Week {week_num} stats:")
    print(f"  Sessions completed : {stats['sessions']}")
    print(f"  Average score      : {stats['avg_score']}/100")
    print(f"  Adaptation decision: {adaptation.upper()}")

    if adaptation == "progress":
        print("  → Great performance! Plan will be progressed.")
    elif adaptation == "maintain":
        print("  → Solid performance. Plan stays the same.")
    else:
        print("  → Needs more work. Plan will be reduced slightly.")

    # Backup الخطة الحالية
    date_str    = datetime.now().strftime("%Y%m%d_%H%M")
    backup_file = f"plan_backup_{date_str}.json"
    shutil.copy(plan_file, backup_file)
    print(f"\n  Backup saved: {backup_file}")

    # جيب الخطة الجديدة
    print("  Generating updated plan...")
    try:
        updated_plan_section = get_ai_adaptation(plan, stats, sessions)

        # دمج مع بيانات المريض
        updated_plan = json.loads(json.dumps(plan))
        updated_plan["plan"]         = updated_plan_section
        updated_plan["last_updated"] = datetime.now().isoformat()
        updated_plan["adaptation_history"] = plan.get("adaptation_history", []) + [{
            "week":       week_num,
            "avg_score":  stats["avg_score"],
            "decision":   adaptation,
            "updated_at": datetime.now().isoformat(),
        }]

        source = "AI"

    except Exception as e:
        print(f"  [AI unavailable: {e}]")
        print("  Using offline adaptation...")
        updated_plan = apply_offline_adaptation(plan, stats)
        updated_plan["last_updated"] = datetime.now().isoformat()
        source = "offline"

    # احفظ الخطة الجديدة
    save_json(updated_plan, plan_file)

    print(f"\n  [OK] Plan updated ({source})")
    print(f"  New phase    : {updated_plan['plan']['phase']}")
    print(f"  Total weeks  : {updated_plan['plan']['total_weeks']}")

    # اعرض التغييرات في الأسبوع الجاي
    next_week_num = week_num + 1
    next_week = next(
        (w for w in updated_plan["plan"]["weeks"] if w["week"] == next_week_num),
        None
    )

    if next_week:
        print(f"\n  Next week (Week {next_week_num}): {next_week.get('focus', '')}")
        for day in next_week["days"][:3]:   # أول 3 أيام بس
            names = [e["name"] for e in day.get("exercises", [])] or ["Rest"]
            print(f"    Day {day['day']}: {', '.join(names)}")

    print("\n" + "="*50)
    print("  Run session_runner.py for your next session.")
    print("="*50 + "\n")


if __name__ == "__main__":
    run_adaptive_plan()