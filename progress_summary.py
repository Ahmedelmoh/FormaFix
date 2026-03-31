"""
progress_summary.py — FormaFix
================================
بعد كل session، الـ AI بيحلل الأداء ويدي تقرير coaching كامل.

بيقرأ: session_data.json
بيكتب: summary.txt (تقرير قابل للقراءة)
"""

import json
import os
from datetime import datetime
from ai_client import ask_ai, PROVIDER

OFFLINE_SUMMARY_TEMPLATE = """
╔══════════════════════════════════════════════════════╗
║           FormaFix — Session Summary                 ║
╚══════════════════════════════════════════════════════╝

Patient  : {patient}
Injury   : {injury}
Date     : {date}
Phase    : {phase}
Week {week}, Day {day}

─────────────────────────────────────────────────────
  EXERCISES COMPLETED
─────────────────────────────────────────────────────
{exercises_text}
─────────────────────────────────────────────────────
  OVERALL SCORE: {overall_score}/100  {score_emoji}
─────────────────────────────────────────────────────

AI Coaching not available (quota exceeded).
Keep following your plan and stay consistent!

Next session: follow Week {week} schedule.
"""


def load_sessions(filename="session_data.json") -> list:
    if not os.path.exists(filename):
        raise FileNotFoundError(
            "session_data.json not found.\n"
            "Run session_runner.py first to complete a session."
        )
    with open(filename, encoding="utf-8") as f:
        return json.load(f)


def format_exercises(exercises: list) -> str:
    lines = []
    for ex in exercises:
        score  = ex.get("avg_score", 0)
        sets_d = ex.get("completed_sets", 0)
        sets_t = ex.get("target_sets", 0)
        reps_t = ex.get("target_reps", 0)
        emoji  = "✅" if score >= 75 else "⚠️" if score >= 50 else "❌"
        lines.append(
            f"  {emoji}  {ex['name']:<30} "
            f"Sets: {sets_d}/{sets_t}  "
            f"Reps: {reps_t}  "
            f"Score: {score}/100"
        )
    return "\n".join(lines)


def get_score_emoji(score: int) -> str:
    if score >= 85: return "🌟 Excellent!"
    if score >= 70: return "✅ Good"
    if score >= 50: return "⚠️  Needs improvement"
    return "❌ Poor — review your form"


def get_ai_report(session: dict, all_sessions: list) -> str:
    """بيبعت بيانات الـ session لـ AI ويجيب تقرير coaching."""

    # ابني ملخص كل التمارين
    ex_summary = []
    for ex in session["exercises"]:
        ex_summary.append(
            f"- {ex['name']}: "
            f"{ex['completed_sets']}/{ex['target_sets']} sets, "
            f"{ex['target_reps']} reps each, "
            f"avg score {ex['avg_score']}/100"
        )

    # ابني تاريخ الـ sessions السابقة (آخر 3)
    history = []
    prev_sessions = [s for s in all_sessions if s != session][-3:]
    for s in prev_sessions:
        history.append(
            f"  {s['timestamp'][:10]}: "
            f"Week {s['week']} Day {s['day']} — "
            f"score {s['overall_score']}/100"
        )

    history_text = "\n".join(history) if history else "  (This is the first session)"

    prompt = f"""
You are a physiotherapy coach reviewing a patient's rehabilitation session.

PATIENT INFO:
- Name: {session['patient']}
- Injury: {session['injury']}
- Phase: {session['phase']}
- Week: {session['week']}, Day: {session['day']}

TODAY'S SESSION:
{chr(10).join(ex_summary)}
Overall score: {session['overall_score']}/100

PREVIOUS SESSIONS:
{history_text}

Please provide a coaching report with these sections:
1. SESSION ASSESSMENT — brief evaluation of today's performance
2. WHAT WENT WELL — positive observations
3. AREAS TO IMPROVE — specific form or movement corrections
4. TIPS FOR NEXT SESSION — 2-3 actionable tips
5. PLAN RECOMMENDATION — should they continue current plan, repeat this day, or progress?

Keep it encouraging, specific, and under 300 words.
"""

    response = ask_ai(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=(
            "You are an expert physiotherapy coach. "
            "Give practical, encouraging, and specific feedback. "
            "Always be positive but honest about areas needing improvement."
        )
    )
    return response


def build_report(session: dict, ai_report: str) -> str:
    """بيبني التقرير النهائي كـ string."""

    exercises_text = format_exercises(session["exercises"])
    score_emoji    = get_score_emoji(session["overall_score"])
    date_str       = session["timestamp"][:10]

    report = f"""
╔══════════════════════════════════════════════════════╗
║           FormaFix — Session Summary                 ║
╚══════════════════════════════════════════════════════╝

Patient  : {session['patient']}
Injury   : {session['injury']}
Date     : {date_str}
Phase    : {session['phase']}
Week {session['week']}, Day {session['day']}

─────────────────────────────────────────────────────
  EXERCISES COMPLETED
─────────────────────────────────────────────────────
{exercises_text}

─────────────────────────────────────────────────────
  OVERALL SCORE: {session['overall_score']}/100  {score_emoji}
─────────────────────────────────────────────────────

  AI COACHING REPORT
─────────────────────────────────────────────────────
{ai_report}

─────────────────────────────────────────────────────
  Generated by FormaFix AI ({PROVIDER.upper()})
  {datetime.now().strftime('%Y-%m-%d %H:%M')}
═══════════════════════════════════════════════════════
"""
    return report


def save_report(report: str, session: dict) -> str:
    """بيحفظ التقرير في ملف summary.txt."""
    date_str = session["timestamp"][:10].replace("-", "")
    filename = f"summary_W{session['week']}D{session['day']}_{date_str}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    return filename


def run_progress_summary(session_file="session_data.json"):
    """الدالة الرئيسية — بتحلل آخر session وبتولّد التقرير."""

    print("\n" + "="*50)
    print("   FormaFix — Progress Summary")
    print(f"   AI: {PROVIDER.upper()}")
    print("="*50)

    # قرأ الـ sessions
    sessions = load_sessions(session_file)
    if not sessions:
        print("[ERROR] No sessions found.")
        return

    # آخر session
    session = sessions[-1]

    print(f"\n  Analyzing session: Week {session['week']}, Day {session['day']}")
    print(f"  Overall score: {session['overall_score']}/100")
    print("\n  Generating AI coaching report...")

    # جيب الـ AI report
    try:
        ai_report = get_ai_report(session, sessions)
    except Exception as e:
        print(f"  [AI unavailable: {e}]")
        print("  Using offline summary...")
        exercises_text = format_exercises(session["exercises"])
        ai_report = (
            "AI coaching not available right now.\n"
            "Keep following your plan consistently — consistency is key to recovery!"
        )

    # ابني التقرير
    report = build_report(session, ai_report)

    # اعرضه في الـ terminal
    print(report)

    # احفظه في ملف
    filename = save_report(report, session)
    print(f"  [OK] Report saved to: {filename}")

    # ── عرض ملخص سريع للـ sessions كلها ─────────────────────────────
    if len(sessions) > 1:
        print("\n" + "="*50)
        print("  YOUR PROGRESS HISTORY")
        print("="*50)
        for s in sessions[-5:]:   # آخر 5 sessions
            bar_len = s['overall_score'] // 5
            bar     = "█" * bar_len + "░" * (20 - bar_len)
            print(
                f"  W{s['week']}D{s['day']}  "
                f"|{bar}|  "
                f"{s['overall_score']:3}/100"
            )
        print("="*50)


if __name__ == "__main__":
    run_progress_summary()