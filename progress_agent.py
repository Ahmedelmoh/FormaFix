# progress_agent.py
from ai_client import ask_ai

class ProgressSummaryAgent:
    def __init__(self):
        self.system_prompt = (
            "You are the Progress Summary Agent for FormaFix. "
            "Analyze the exercise session data and provide a summary in Egyptian Arabic (Ammiya). "
            "Be encouraging and mention if the form score was good or needs work."
        )

    def generate_report(self, session_data):
        user_message = (
            f"Session Results:\n"
            f"- Exercise: {session_data['exercise_name']}\n"
            f"- Reps: {session_data['reps']}\n"
            f"- Avg Score: {session_data['avg_score']}/100\n"
            f"- Angles reached: {session_data['best_angle']} degrees."
        )
        return ask_ai([{"role": "user", "content": user_message}], self.system_prompt)