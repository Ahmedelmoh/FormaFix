"""
plan_service.py — FormaFix
===========================
Service for managing rehabilitation plans using the AI agent.
"""

import json
import re
from datetime import datetime
from database_service import DatabaseService
from ai_client import ask_ai

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

SYSTEM_PROMPT = f"""You are an expert physiotherapist AI assistant for FormaFix,
a rehabilitation app that uses computer vision to track exercise form.

Your role:
1. Assess the patient's injury through natural conversation.
2. Ask ONE question at a time — never multiple at once.
3. After 4–6 questions, generate a personalised rehab plan.

Information to gather:
  - Injury type and body part
  - Date of injury
  - Surgery (yes/no; if yes, when)
  - Current pain level (1–10)
  - Previous treatment
  - Rehabilitation goal

Available exercises: {json.dumps(AVAILABLE_EXERCISES)}

When you have enough information, output the marker PLAN_READY on its own line,
then the plan as a JSON code block:

PLAN_READY
```json
{{
  "patient": {{
    "name": "string",
    "age": null,
    "injury": "string",
    "injury_date": "string",
    "surgery": false,
    "surgery_date": null,
    "pain_level": 5,
    "mobility": "limited/moderate/good",
    "previous_treatment": "string",
    "goal": "string",
    "notes": "string"
  }},
  "plan": {{
    "total_weeks": 4,
    "phase": "early_recovery",
    "phase_description": "string",
    "weeks": [
      {{
        "week": 1,
        "focus": "string",
        "days": [
          {{
            "day": 1,
            "exercises": [
              {{
                "name": "exercise_name",
                "sets": 3,
                "reps": 10,
                "rest_seconds": 30,
                "notes": "description"
              }}
            ]
          }}
        ]
      }}
    ]
  }}
}}
```

Be professional, empathetic, and thorough. Ask clarifying questions if something is unclear.
"""


class PlanService:
    """Service for managing rehabilitation plans."""

    def __init__(self):
        self.db = DatabaseService()
        self.conversation_history = []

    def start_plan_creation(self, patient_name: str) -> str:
        """Start the plan creation conversation. Returns the first question."""
        self.conversation_history = []
        initial_message = f"Hi {patient_name}! I'm here to create a personalized rehabilitation plan for you. Let's start with a few questions about your injury.\n\nWhat body part were you injured? (e.g., knee, shoulder, hip)"
        self.conversation_history.append({"role": "assistant", "content": initial_message})
        return initial_message

    def continue_conversation(self, user_response: str) -> str:
        """Continue the conversation and ask the next question. Returns AI response."""
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_response})

        # Prepare messages for API (system prompt passed as dedicated param, not injected)
        messages = self.conversation_history.copy()

        # Get AI response
        response = ask_ai(messages, system_prompt=SYSTEM_PROMPT)

        # Check if plan is ready
        if "PLAN_READY" in response:
            # Extract JSON from response
            plan_json = self._extract_plan_json(response)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response, plan_json
        else:
            self.conversation_history.append({"role": "assistant", "content": response})
            return response, None

    @staticmethod
    def _extract_plan_json(response: str) -> dict :
        """Extract JSON from PLAN_READY response."""
        try:
            # Find JSON block
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except Exception as e:
            print(f"Error parsing plan JSON: {e}")
        return None

    def save_plan(self, customer_id: int, plan_data: dict) -> int:
        """Save plan to database. Returns plan_id."""
        plan_record = {
            "injury_type": plan_data.get("patient", {}).get("injury", "unknown"),
            "injury_date": plan_data.get("patient", {}).get("injury_date", ""),
            "surgery": plan_data.get("patient", {}).get("surgery", False),
            "surgery_date": plan_data.get("patient", {}).get("surgery_date"),
            "pain_level": plan_data.get("patient", {}).get("pain_level", 5),
            "mobility": plan_data.get("patient", {}).get("mobility", "moderate"),
            "previous_treatment": plan_data.get("patient", {}).get("previous_treatment", ""),
            "goal": plan_data.get("patient", {}).get("goal", ""),
            "plan_json": plan_data,
        }
        return self.db.create_plan(customer_id, plan_record)

    def get_plan_weeks(self, plan_json: dict) -> list:
        """Extract weeks from plan JSON."""
        try:
            return plan_json.get("plan", {}).get("weeks", [])
        except:
            return []

    def get_exercises_for_day(self, plan_json: dict, week: int, day: int) -> list:
        """Get exercises for a specific week and day."""
        try:
            def normalize_to_int(value):
                if isinstance(value, int):
                    return value
                if value is None:
                    return None
                text = str(value).strip()
                if not text:
                    return None
                digits = "".join(ch for ch in text if ch.isdigit())
                return int(digits) if digits else None

            root = plan_json.get("plan", plan_json)
            weeks = root.get("weeks", [])
            target_week = normalize_to_int(week)
            target_day = normalize_to_int(day)

            for w in weeks:
                if normalize_to_int(w.get("week")) == target_week:
                    days = w.get("days", [])
                    for i, d in enumerate(days, start=1):
                        current_day = normalize_to_int(d.get("day", i))
                        if current_day == target_day:
                            return d.get("exercises", [])
        except:
            pass
        return []