"""
progress_agent.py — FormaFix
==============================
Reads session_data.json and displays a clear progress report in the terminal.

Usage:
    python progress_agent.py
"""

import json
import os
from datetime import datetime


def load_sessions(filepath: str = "session_data.json") -> list[dict]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            "session_data.json not found. Complete at least one session first."
        )
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def _bar(score: int, width: int = 20) -> str:
    """Render a simple ASCII progress bar for a score 0–100."""
    filled = round(score / 100 * width)
    colour = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
    return f"[{'█' * filled}{'░' * (width - filled)}] {score}/100 {colour}"


def show_progress(filepath: str = "session_data.json") -> None:
    sessions = load_sessions(filepath)

    if not sessions:
        print("No sessions recorded yet.")
        return

    # ── Patient summary ───────────────────────────────────────────────────────
    latest   = sessions[-1]
    patient  = latest.get("patient") or "Unknown"
    injury   = latest.get("injury", "Unknown")
    total    = len(sessions)

    print("\n" + "=" * 55)
    print("  FormaFix — Progress Report")
    print("=" * 55)
    print(f"  Patient : {patient}")
    print(f"  Injury  : {injury}")
    print(f"  Total sessions completed: {total}")
    print("=" * 55)

    # ── Per-session history ───────────────────────────────────────────────────
    print("\n📅 Session History:\n")
    for i, s in enumerate(sessions, 1):
        ts    = s.get("timestamp", "")
        date  = ts[:10] if ts else "unknown"
        week  = s.get("week", "?")
        day   = s.get("day", "?")
        score = s.get("overall_score", 0)
        ex_names = [e["name"] for e in s.get("exercises", [])]

        print(f"  Session {i:>2} | {date} | Week {week} Day {day}")
        print(f"           Exercises : {', '.join(ex_names) or 'none'}")
        print(f"           Score     : {_bar(score)}")
        print()

    # ── Trend analysis ────────────────────────────────────────────────────────
    scores = [s["overall_score"] for s in sessions if s["overall_score"] > 0]
    if len(scores) >= 2:
        trend = scores[-1] - scores[0]
        arrow = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
        print("-" * 55)
        print(f"  Overall trend : {arrow}  {'+' if trend >= 0 else ''}{trend} points")
        print(f"  Best session  : {max(scores)}/100")
        print(f"  Average score : {round(sum(scores)/len(scores))}/100")

    # ── Exercise breakdown ────────────────────────────────────────────────────
    ex_stats: dict[str, list[int]] = {}
    for s in sessions:
        for ex in s.get("exercises", []):
            name = ex["name"]
            sc   = ex.get("avg_score", 0)
            if sc > 0:
                ex_stats.setdefault(name, []).append(sc)

    if ex_stats:
        print("\n📊 Per-Exercise Averages:\n")
        for name, sc_list in ex_stats.items():
            avg = round(sum(sc_list) / len(sc_list))
            print(f"  {name:<30} {_bar(avg, width=15)}")

    print("\n" + "=" * 55 + "\n")


if __name__ == "__main__":
    show_progress()