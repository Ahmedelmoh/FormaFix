"""
progress_agent.py — FormaFix
==============================
Generates a natural-language session summary using the configured AI provider.
"""

from ai_client import ask_ai

_SYSTEM_PROMPT = (
    "You are the Progress Summary Agent for FormaFix, an AI-powered physiotherapy app. "
    "Analyze the exercise session data and provide a concise summary in Egyptian Arabic (Ammiya). "
    "Be encouraging. Mention whether the form score was good or needs work, "
    "and give one practical tip for the next session."
)


class ProgressSummaryAgent:
    """Wraps the AI client to produce post-session progress reports."""

    def generate_report(self, session_data: dict) -> str:
        """
        Generate a natural-language progress report.

        Parameters
        ----------
        session_data : dict with keys:
            exercise_name, reps, avg_score, best_angle

        Returns
        -------
        str : AI-generated report text
        """
        user_message = (
            f"Session Results:\n"
            f"- Exercise  : {session_data['exercise_name']}\n"
            f"- Reps      : {session_data['reps']}\n"
            f"- Avg Score : {session_data['avg_score']}/100\n"
            f"- Best angle: {session_data['best_angle']}°"
        )
        return ask_ai(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=_SYSTEM_PROMPT,
        )
