"""
progress_analyzer.py — FormaFix
=================================
Analyzes session_data.json and updates plan.json using AI.

Flow:
  1. Load session_data.json + plan.json
  2. Compute per-exercise stats: avg score, trend, completion rate
  3. Build a structured summary and send to the AI with the current plan
  4. AI returns a fully updated plan JSON
  5. Backup old plan.json → save new one

Usage:
  python progress_analyzer.py          # standalone
  from progress_analyzer import run_plan_update   # called from session_runner
"""

import json
import os
import re
import shutil
from datetime import datetime
from collections import defaultdict

from ai_client import ask_ai, PROVIDER


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

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

# Score tiers
TIER_EXCELLENT   = 85   # Progress: add reps/sets or advance exercise
TIER_GOOD        = 70   # Maintain: stay the course
TIER_STRUGGLING  = 50   # Regress: reduce load
# Below 50 → needs_regression: significant regression required

# Trend detection (needs at least 3 sessions per exercise)
TREND_DELTA_MIN  = 10   # points difference first→last to count as improving/declining
TREND_PLATEAU    = 5    # max spread to call it a plateau


# ─────────────────────────────────────────────────────────────────────────────
# AI System Prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are an expert physiotherapist AI for FormaFix, a rehabilitation app.

You receive:
  - A patient's current rehab plan (JSON)
  - A structured analysis of their actual session performance

Your task: return a REVISED rehab plan as valid JSON.

═══ PERFORMANCE TIERS ═══
  excellent   (score ≥ 85) → Patient is excelling.
              Progress: increase reps by 2-3, or add a set, or introduce the next harder exercise.
  good        (score 70-84) → On track.
              Maintain current exercises. Small rep/set increase only if trend is "improving".
  struggling  (score 50-69) → Having difficulty.
              Reduce reps by 2-3, reduce sets, add more rest, or regress to an easier exercise.
  needs_regression (score < 50) → Significant difficulty.
              Regress exercise, halve the load, increase rest time, add a coaching note.

═══ TREND MODIFIERS ═══
  improving  → Accelerate progression even for "good" scores
  plateau    → Change exercise variation or rep scheme to break the plateau
  declining  → Investigate overload — reduce all load, check rest days are present
  insufficient_data → Use score tier only, don't assume trend

═══ RULES ═══
  - Only use exercises from this list: {json.dumps(AVAILABLE_EXERCISES)}
  - Never remove rest days (empty exercises list)
  - Only adjust FUTURE weeks — do not modify weeks that have already been completed
  - Keep total_weeks unchanged
  - Preserve the entire "patient" object exactly as given
  - Add a "plan_notes" string at the plan level: plain language summary of what changed and why
  - Reply in the same language the original plan is written in

═══ OUTPUT FORMAT ═══
Output ONLY a valid JSON object — no markdown, no explanation, no preamble.
Exact schema:
{{
  "patient": {{ ...unchanged from input... }},
  "plan": {{
    "total_weeks": <int>,
    "phase": "<string>",
    "phase_description": "<string>",
    "plan_notes": "<plain language: what changed and why>",
    "weeks": [
      {{
        "week": <int>,
        "focus": "<string>",
        "days": [
          {{
            "day": <int>,
            "exercises": [
              {{
                "name": "<exercise_name>",
                "sets": <int>,
                "reps": <int>,
                "rest_seconds": <int>,
                "notes": "<instruction for patient>"
              }}
            ]
          }}
        ]
      }}
    ]
  }}
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_data(plan_file="plan.json", sessions_file="session_data.json") -> tuple:
    if not os.path.exists(plan_file):
        raise FileNotFoundError(
            "plan.json not found. Run rehab_agent.py first."
        )
    if not os.path.exists(sessions_file):
        raise FileNotFoundError(
            "session_data.json not found. Complete at least one session first."
        )

    with open(plan_file, encoding="utf-8") as f:
        plan = json.load(f)
    with open(sessions_file, encoding="utf-8") as f:
        sessions = json.load(f)

    return plan, sessions


# ─────────────────────────────────────────────────────────────────────────────
# Performance Analysis
# ─────────────────────────────────────────────────────────────────────────────

def _assign_tier(avg_score: float) -> str:
    if avg_score >= TIER_EXCELLENT:
        return "excellent"
    elif avg_score >= TIER_GOOD:
        return "good"
    elif avg_score >= TIER_STRUGGLING:
        return "struggling"
    return "needs_regression"


def _assign_trend(scores: list) -> str:
    """
    Requires ≥ 3 data points.
    Compares first score to last score and overall spread.
    """
    if len(scores) < 3:
        return "insufficient_data"

    delta  = scores[-1] - scores[0]
    spread = max(scores) - min(scores)

    if delta >= TREND_DELTA_MIN:
        return "improving"
    elif delta <= -TREND_DELTA_MIN:
        return "declining"
    elif spread <= TREND_PLATEAU:
        return "plateau"
    return "stable"


def analyze_sessions(sessions: list) -> dict:
    """
    Groups sessions by exercise name and computes:
      - avg_score
      - latest_score
      - trend (improving / plateau / declining / stable / insufficient_data)
      - sessions_count
      - avg_completion_rate  (completed_sets / target_sets)
      - performance_tier
      - score_history (chronological list)

    Returns dict keyed by exercise name.
    """
    by_exercise = defaultdict(list)

    for session in sessions:
        for ex in session.get("exercises", []):
            if ex.get("avg_score", 0) > 0:
                by_exercise[ex["name"]].append({
                    "score":          ex["avg_score"],
                    "completed_sets": ex.get("completed_sets", 0),
                    "target_sets":    ex.get("target_sets", 1),
                    "timestamp":      session["timestamp"],
                })

    stats = {}
    for name, entries in by_exercise.items():
        entries_sorted = sorted(entries, key=lambda x: x["timestamp"])
        scores = [e["score"] for e in entries_sorted]

        avg_score   = round(sum(scores) / len(scores), 1)
        trend       = _assign_trend(scores)
        tier        = _assign_tier(avg_score)

        completion_rates = [
            e["completed_sets"] / max(e["target_sets"], 1)
            for e in entries_sorted
        ]
        avg_completion = round(sum(completion_rates) / len(completion_rates), 2)

        stats[name] = {
            "avg_score":          avg_score,
            "latest_score":       scores[-1],
            "trend":              trend,
            "sessions_count":     len(entries_sorted),
            "avg_completion_rate": avg_completion,
            "performance_tier":   tier,
            "score_history":      scores,
        }

    return stats


def get_completed_weeks(sessions: list) -> set:
    """Returns the set of week numbers the patient has already completed."""
    return {s["week"] for s in sessions}


# ─────────────────────────────────────────────────────────────────────────────
# Summary Builder (what gets sent to the AI)
# ─────────────────────────────────────────────────────────────────────────────

def build_analysis_summary(plan: dict, stats: dict, sessions: list) -> str:
    """
    Builds a structured plain-text summary + the current plan JSON.
    This is the user message sent to the AI.
    """
    overall_scores = [s["overall_score"] for s in sessions if s.get("overall_score", 0) > 0]
    overall_avg    = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0

    completed_weeks = sorted(get_completed_weeks(sessions))
    last_session    = sessions[-1] if sessions else {}

    lines = [
        "=== PATIENT PERFORMANCE ANALYSIS ===",
        "",
        f"Patient      : {plan['patient'].get('name', 'Unknown')}",
        f"Injury       : {plan['patient'].get('injury', 'Unknown')}",
        f"Current phase: {plan['plan']['phase']}",
        f"Total weeks  : {plan['plan']['total_weeks']}",
        f"Sessions done: {len(sessions)}",
        f"Overall avg  : {overall_avg}/100",
        f"Weeks completed (do NOT modify): {completed_weeks}",
        f"Last session  : week {last_session.get('week', '?')}, day {last_session.get('day', '?')}",
        "",
        "=== PER-EXERCISE STATS ===",
    ]

    for name, s in stats.items():
        lines.append(
            f"\n  Exercise       : {name}"
            f"\n  Avg score      : {s['avg_score']}/100"
            f"\n  Latest score   : {s['latest_score']}/100"
            f"\n  Score history  : {s['score_history']}"
            f"\n  Trend          : {s['trend']}"
            f"\n  Tier           : {s['performance_tier']}"
            f"\n  Sessions       : {s['sessions_count']}"
            f"\n  Completion rate: {int(s['avg_completion_rate'] * 100)}%"
        )

    lines += [
        "",
        "=== CURRENT PLAN (JSON) ===",
        json.dumps(plan, indent=2, ensure_ascii=False),
        "",
        "Please return the updated plan JSON now.",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# AI Plan Update
# ─────────────────────────────────────────────────────────────────────────────

def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if the model added them."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def update_plan_with_ai(plan: dict, sessions: list) -> dict:
    stats   = analyze_sessions(sessions)
    summary = build_analysis_summary(plan, stats, sessions)

    print(f"\n[FormaFix] Sending analysis to {PROVIDER.upper()}...")
    response = ask_ai(
        messages=[{"role": "user", "content": summary}],
        system_prompt=SYSTEM_PROMPT
    )

    clean = _strip_json_fences(response)

    try:
        updated = json.loads(clean)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"[FormaFix] AI returned invalid JSON.\n"
            f"Parse error: {e}\n"
            f"First 600 chars:\n{response[:600]}"
        )

    # Stamp metadata onto the updated plan
    updated["updated_at"] = datetime.now().isoformat()
    updated["update_history"] = plan.get("update_history", []) + [{
        "timestamp":          datetime.now().isoformat(),
        "sessions_at_update": len(sessions),
        "overall_avg":        round(
            sum(s["overall_score"] for s in sessions if s.get("overall_score", 0) > 0)
            / max(len(sessions), 1), 1
        ),
        "exercise_stats": stats,
    }]

    return updated


# ─────────────────────────────────────────────────────────────────────────────
# File Helpers
# ─────────────────────────────────────────────────────────────────────────────

def backup_plan(plan_file: str = "plan.json") -> str | None:
    """Copies plan.json to plan_backup_YYYYMMDD_HHMMSS.json."""
    if not os.path.exists(plan_file):
        return None
    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = plan_file.replace(".json", f"_backup_{ts}.json")
    shutil.copy2(plan_file, backup)
    return backup


# ─────────────────────────────────────────────────────────────────────────────
# Pretty Print Helpers
# ─────────────────────────────────────────────────────────────────────────────

TIER_EMOJI = {
    "excellent":        "🟢",
    "good":             "🔵",
    "struggling":       "🟡",
    "needs_regression": "🔴",
}

TREND_EMOJI = {
    "improving":          "📈",
    "stable":             "➡️",
    "plateau":            "⏸️",
    "declining":          "📉",
    "insufficient_data":  "❓",
}


def print_analysis_report(stats: dict, sessions: list) -> None:
    """Prints a human-readable summary to the console before updating."""
    overall_scores = [s["overall_score"] for s in sessions if s.get("overall_score", 0) > 0]
    overall_avg    = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0

    print(f"\n{'='*52}")
    print(f"  Performance Report  ({len(sessions)} sessions)")
    print(f"  Overall avg: {overall_avg}/100")
    print(f"{'='*52}")

    if not stats:
        print("  No exercise data found yet.")
        return

    for name, s in stats.items():
        tier_sym  = TIER_EMOJI.get(s["performance_tier"], "")
        trend_sym = TREND_EMOJI.get(s["trend"], "")
        print(
            f"\n  {tier_sym} {name}"
            f"\n     Score : {s['avg_score']}/100  (latest: {s['latest_score']})"
            f"\n     Trend : {trend_sym} {s['trend']}"
            f"\n     Tier  : {s['performance_tier']}"
            f"\n     Done  : {s['sessions_count']} session(s), "
            f"{int(s['avg_completion_rate']*100)}% completion"
            f"\n     History: {s['score_history']}"
        )

    print(f"\n{'='*52}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def run_plan_update(
    plan_file:     str  = "plan.json",
    sessions_file: str  = "session_data.json",
    silent:        bool = False,
) -> dict | None:
    """
    Full pipeline: load → analyze → AI update → backup → save → return.

    Parameters
    ----------
    plan_file     : path to plan.json
    sessions_file : path to session_data.json
    silent        : if True, suppress the console report (for automated calls)

    Returns
    -------
    The updated plan dict, or None if skipped.
    """
    if not silent:
        print("\n" + "="*52)
        print("   FormaFix — Plan Update Engine")
        print(f"   AI Provider: {PROVIDER.upper()}")
        print("="*52)

    # ── Load ──────────────────────────────────────────────────────────────────
    plan, sessions = load_data(plan_file, sessions_file)

    if len(sessions) == 0:
        print("[FormaFix] No sessions found. Complete a session first.")
        return None

    # ── Analyze ───────────────────────────────────────────────────────────────
    stats = analyze_sessions(sessions)

    if not silent:
        print_analysis_report(stats, sessions)

    # ── AI update ─────────────────────────────────────────────────────────────
    updated_plan = update_plan_with_ai(plan, sessions)

    # ── Backup + Save ─────────────────────────────────────────────────────────
    backup = backup_plan(plan_file)
    if backup and not silent:
        print(f"\n[OK] Old plan backed up → {backup}")

    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(updated_plan, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Plan updated and saved → {plan_file}")

    # ── Show what changed ─────────────────────────────────────────────────────
    notes = updated_plan.get("plan", {}).get("plan_notes", "")
    if notes:
        print(f"\n  What changed:\n  {notes}\n")

    return updated_plan


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_plan_update()