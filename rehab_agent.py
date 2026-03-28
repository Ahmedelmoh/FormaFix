"""
rehab_agent.py — FormaFix
==========================
Rehab Planning Agent — بيسأل المريض أسئلة ذكية عن إصابته
وبيولّد خطة تمارين مخصصة.

يستخدم ai_client.py — يدعم Gemini / Anthropic / Ollama
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
1. Assess the patient's injury through natural conversation
2. Ask ONE question at a time
3. After 4-6 questions, generate a personalized rehab plan

Gather: injury type, date, surgery (yes/no + when), pain level 1-10,
previous treatment, and rehab goal.

Available exercises: {json.dumps(AVAILABLE_EXERCISES)}

When ready, output PLAN_READY then the JSON:

PLAN_READY
```json
{{
  "patient": {{
    "name": "string", "age": null,
    "injury": "string", "injury_date": "string",
    "surgery": true, "surgery_date": null,
    "pain_level": 5, "mobility": "limited/moderate/good",
    "previous_treatment": "string", "goal": "string", "notes": "string"
  }},
  "plan": {{
    "total_weeks": 4,
    "phase": "early_recovery",
    "phase_description": "string",
    "weeks": [
      {{
        "week": 1, "focus": "string",
        "days": [
          {{
            "day": 1,
            "exercises": [
              {{"name": "exercise_name", "sets": 3, "reps": 10,
                "rest_seconds": 30, "notes": "instruction"}}
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
- Only use exercises from the available list
- Pain > 7: gentle exercises only (straight_leg_raise, pendulum)
- Include rest days (empty exercises)
- Progress gradually week by week
- Reply in the same language as the patient (Arabic or English)
"""


def extract_plan(response: str) -> dict | None:
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


def clean_response(response: str) -> str:
    text = response.replace("PLAN_READY", "").strip()
    return re.sub(r"```json.*?```", "", text, flags=re.DOTALL).strip()


def save_plan(plan: dict, filename: str = "plan.json") -> str:
    plan["generated_at"] = datetime.now().isoformat()
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    return filename


def run_rehab_agent() -> dict | None:
    print("\n" + "="*50)
    print("   FormaFix — Rehabilitation Planning Agent")
    print(f"   AI: {PROVIDER.upper()}")
    print("="*50)
    print("Describe your injury to get started. (type 'quit' to exit)\n")

    conversation = []

    # فتح المحادثة
    opening = ask_ai(
        messages=[{"role": "user",
                   "content": "Hello, I want to start my rehabilitation program."}],
        system_prompt=SYSTEM_PROMPT
    )
    print(f"FormaFix Agent:\n{opening}\n")
    conversation += [
        {"role": "user", "content": "Hello, I want to start my rehabilitation program."},
        {"role": "assistant", "content": opening},
    ]

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n[FormaFix] Exited.")
            return None

        conversation.append({"role": "user", "content": user_input})
        response = ask_ai(conversation, system_prompt=SYSTEM_PROMPT)
        plan = extract_plan(response)

        if plan:
            msg = clean_response(response)
            if msg:
                print(f"\nFormaFix Agent:\n{msg}")
            save_plan(plan)
            print("\n" + "="*50)
            print(f"[OK] Plan saved to plan.json")
            print(f"  Injury  : {plan['patient']['injury']}")
            print(f"  Phase   : {plan['plan']['phase']}")
            print(f"  Weeks   : {plan['plan']['total_weeks']}")
            print("="*50)
            print("Next: python session_runner.py\n")
            return plan
        else:
            print(f"\nFormaFix Agent:\n{response}\n")
            conversation.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    run_rehab_agent()