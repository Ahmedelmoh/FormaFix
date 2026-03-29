"""
rehab_agent.py — FormaFix
==========================
Rehabilitation Planning Agent.

Interviews the patient via a conversational CLI, then generates a
personalised weekly exercise plan (saved to plan.json).

Supports Gemini / Anthropic / Ollama via ai_client.py.
"""

import json
import os
import re
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
                "notes": "instruction"
              }}
            ]
          }},
          {{"day": 2, "exercises": []}}
        ]
      }}
    ]
  }}
}}
```

Rules:
- Only use exercises from the available list.
- Pain > 7: gentle exercises only (straight_leg_raise, pendulum).
- Include rest days (empty exercises list).
- Progress gradually week by week.
- Reply in the same language as the patient (Arabic or English).
"""


def _extract_plan(response: str) -> dict | None:
    """Parse the JSON plan block from the AI response, or return None."""
    if "PLAN_READY" not in response:
        return None
    match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse error: {e}")
        return None


def _clean_response(response: str) -> str:
    """Strip the PLAN_READY marker and JSON block, returning only prose."""
    text = response.replace("PLAN_READY", "").strip()
    return re.sub(r"```json.*?```", "", text, flags=re.DOTALL).strip()


def _save_plan(plan: dict, filename: str = "plan.json") -> str:
    """Persist the plan dict to disk and return the filename."""
    plan["generated_at"] = datetime.now().isoformat()
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    return filename


def run_rehab_agent() -> dict | None:
    """
    Run the interactive rehab planning session.

    Returns the generated plan dict, or None if the user exits early.
    """
    print("\n" + "=" * 50)
    print("   FormaFix — Rehabilitation Planning Agent")
    print(f"   AI provider: {PROVIDER.upper()}")
    print("=" * 50)
    print("Describe your injury to get started. (type 'quit' to exit)\n")

    conversation: list[dict] = []

    # ── Opening message ──────────────────────────────────────────────────────
    opening_user = {"role": "user", "content": "Hello, I want to start my rehabilitation program."}
    opening_reply = ask_ai(messages=[opening_user], system_prompt=SYSTEM_PROMPT)
    print(f"FormaFix Agent:\n{opening_reply}\n")
    conversation += [opening_user, {"role": "assistant", "content": opening_reply}]

    # ── Conversation loop ────────────────────────────────────────────────────
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n[FormaFix] Session exited.")
            return None

        conversation.append({"role": "user", "content": user_input})
        response = ask_ai(conversation, system_prompt=SYSTEM_PROMPT)

        plan = _extract_plan(response)
        if plan:
            # Print any prose that preceded the JSON
            prose = _clean_response(response)
            if prose:
                print(f"\nFormaFix Agent:\n{prose}")

            _save_plan(plan)
            print("\n" + "=" * 50)
            print("[OK] Plan saved to plan.json")
            print(f"  Injury : {plan['patient']['injury']}")
            print(f"  Phase  : {plan['plan']['phase']}")
            print(f"  Weeks  : {plan['plan']['total_weeks']}")
            print("=" * 50)
            print("Next step: python session_runner.py\n")
            return plan

        # Normal conversation turn — append reply and continue
        print(f"\nFormaFix Agent:\n{response}\n")
        conversation.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    run_rehab_agent()
