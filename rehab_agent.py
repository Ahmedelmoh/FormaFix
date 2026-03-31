"""
rehab_agent.py — FormaFix
==========================
Rehab Planning Agent — بيشخص الإصابة بدقة ويولّد خطة علاجية.

Sources:
  - MGH ACL Rehabilitation Protocol 2024
  - MOON Knee Group ACL Rehabilitation Program
  - جامعة بنها 2022

قواعد التشخيص:
  ✓ يسأل عن نوع الإصابة + توقيتها
  ✓ يسأل عن وجود عملية وتاريخها
  ✓ يحدد المرحلة الصحيحة بناءً على الوقت
  ✓ يسأل عن مستوى الألم (1-10)
  ✓ يسأل عن المدى الحركي الحالي
  ✓ يسأل عن التورم
  ✓ يراعي قاعدة: كل التمارين بدون معدات
"""

import json
import os
import re
from datetime import datetime
from ai_client import ask_ai, PROVIDER


# ── التمارين المتاحة (بدون معدات فقط) ───────────────────────────────────────
# ── كل التمارين هنا في وضع واقف فقط (Demo Mode) ─────────────────────────────
AVAILABLE_EXERCISES = {

    # Phase 1 (0-2 weeks): حماية + تنشيط خفيف
    "phase_1": [
        "single_leg_stand",   # توازن — واقف ✅
        "mini_squat",         # نزول جزئي 30° فقط — واقف ✅
        "hamstring_curl_p2",  # ثني خفيف للركبة — واقف ✅
    ],

    # Phase 2 (3-5 weeks): تقوية + توازن
    "phase_2": [
        "mini_squat",         # نزول حتى 60° — واقف ✅
        "hamstring_curl_p2",  # ثني الركبة حتى 70° — واقف ✅
        "step_up",            # صعود درجة — واقف ✅
        "single_leg_stand",   # توازن — واقف ✅
    ],

    # Phase 3 (6-8 weeks): تقوية متقدمة
    "phase_3": [
        "squat_p3",           # squat حتى 90° — واقف
        "hamstring_curl_p3",  # ثني الركبة حتى 90° — واقف
        "lateral_lunge",      # انفراج جانبي — واقف
        "romanian_deadlift",  # ميلان للأمام — واقف
        "step_up",            # صعود درجة — واقف
    ],

    # Phase 4 (9-12 weeks): مدى كامل
    "phase_4": [
        "full_squat",         # نزول كامل — واقف
        "lunge",              # انفراج أمامي — واقف
        "lateral_lunge",      # انفراج جانبي — واقف
        "romanian_deadlift",  # ميلان للأمام — واقف
        "single_leg_stand",   # توازن متقدم — واقف
    ],

    # كتف
    "shoulder": [
        "pendulum",           # تأرجح — واقف
        "external_rotation",  # تدوير — واقف
        "wall_slide",         # انزلاق — واقف
        "shoulder_abduction", # رفع — واقف
    ],
}

ALL_EXERCISES = (
    AVAILABLE_EXERCISES["phase_1"] +
    AVAILABLE_EXERCISES["phase_2"] +
    AVAILABLE_EXERCISES["phase_3"] +
    AVAILABLE_EXERCISES["phase_4"] +
    AVAILABLE_EXERCISES["shoulder"]
)

# ── قواعد تحديد المرحلة (MGH Protocol) ──────────────────────────────────────
PHASE_CRITERIA = """
PHASE DETERMINATION (MGH Protocol 2024):

Phase 1 (0-2 weeks post-op):
  - Cannot achieve 0° extension yet
  - Quad activation is weak/absent
  - Significant swelling
  - Pain > 5/10
  - Exercises: quad_set, ankle_pump, heel_slide_p1, straight_leg_raise, hip_abduction, terminal_knee_extension, calf_raise

Phase 2 (3-5 weeks post-op):
  - Can achieve 0° full extension
  - Walking normally without pain
  - Flexion reaching 90°+
  - Swelling 1+ or less
  - Exercises: heel_slide_p2, mini_squat (0-60° only!), hamstring_curl_p2, bridge, step_up, single_leg_stand

Phase 3 (6-8 weeks post-op):
  - Full ROM equal to other leg
  - Normal gait
  - No swelling after exercise
  - Exercises: squat_p3 (to 90°), hamstring_curl_p3, lateral_lunge, romanian_deadlift

Phase 4 (9-12 weeks post-op):
  - Quad strength >80% of other leg
  - Good single leg balance
  - No pain/swelling
  - Exercises: full_squat, lunge

STANDING-ONLY MODE: All exercises must be performed STANDING (no lying/sitting).
Available standing exercises per phase (use ALL that are appropriate, not just one):

Phase 1 standing options: single_leg_stand, mini_squat (30° max), hamstring_curl_p2
Phase 2 standing options: mini_squat, hamstring_curl_p2, step_up, single_leg_stand
Phase 3 standing options: squat_p3, hamstring_curl_p3, lateral_lunge, romanian_deadlift, step_up
Phase 4 standing options: full_squat, lunge, lateral_lunge, romanian_deadlift, single_leg_stand

PLAN DURATION RULES (very important):
- Minor sprains (no surgery, pain ≤ 5): 4 weeks minimum
- Post-op ACL Phase 1-2: 4 weeks
- Post-op ACL Phase 2-3: 6 weeks
- Return to sport goal: 8-12 weeks total
- NEVER generate a plan shorter than 4 weeks
- Each week should have 3 DIFFERENT exercises per training day (not the same exercise every day)
- Vary exercises between days AND between weeks
  Week 1 Day 1 example: mini_squat + single_leg_stand + hamstring_curl_p2
  Week 1 Day 3 example: single_leg_stand + hamstring_curl_p2 + mini_squat
  Week 2: introduce step_up if Phase 2 criteria met, add more reps/sets
  Week 3+: progress to harder exercises (squat_p3, lateral_lunge, etc.)
- NEVER repeat exactly the same exercise list week after week with just different reps
- NEVER include calf_raise in any plan

CRITICAL RULES from MGH + MOON + جامعة بنها 2022:
  - NEVER prescribe > 45° flexion in Phase 1
  - NEVER prescribe > 60° squat in Phase 2
  - Mini squat in Phase 2 = 0-60° MAX (MGH 2024)
  - No hamstring resisted curl until Phase 2 (3 weeks min)
  - Quad set must be mastered before SLR
  - If pain > 7: Phase 1 exercises only (quad_set, ankle_pump, SLR)
  - Swelling increase = reduce exercises, add ice
  - ALL exercises must be possible WITHOUT equipment
"""


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are an expert physiotherapist AI for FormaFix, a computer vision rehabilitation app.
Your role: diagnose the patient's injury through smart conversation, then create a personalized rehab plan.

AVAILABLE EXERCISES (NO equipment needed - home-based only):
{json.dumps(AVAILABLE_EXERCISES, indent=2)}

{PHASE_CRITERIA}

DIAGNOSIS QUESTIONS (ask ONE at a time, naturally):
1. Type and location of injury (ACL? which knee? shoulder?)
2. When did injury occur / when was surgery?
3. Current pain level (1-10 scale)
4. Can you fully straighten your knee? (tests for extension lag)
5. Any swelling currently?
6. Current flexion range: can you bend to 45°? 90°? more?
7. Previous treatment or physiotherapy?
8. Goal: return to sport? daily activities?

PHASE ASSIGNMENT:
- Calculate weeks since surgery from the patient's answer
- Assign phase based on MGH criteria above
- Always err on the conservative side

When you have enough info (5-6 questions), output PLAN_READY then the JSON.

PLAN JSON FORMAT:
PLAN_READY
```json
{{
  "patient": {{
    "name": "string",
    "injury": "string (e.g. ACL tear right knee, 4 weeks post-op)",
    "surgery": true/false,
    "weeks_post_op": number,
    "pain_level": 1-10,
    "extension_full": true/false,
    "swelling": "none/mild/moderate/severe",
    "current_flexion": number (degrees, e.g. 90),
    "goal": "string",
    "notes": "string"
  }},
  "assessment": {{
    "current_phase": 1,
    "phase_name": "Phase 1: Immediate Post-Op Protection",
    "phase_rationale": "why this phase was chosen",
    "key_deficits": ["list of main problems to address"],
    "precautions": ["list of things to avoid"]
  }},
  "plan": {{
    "total_weeks": number,
    "weeks": [
      {{
        "week": 1,
        "phase": 1,
        "focus": "string",
        "days": [
          {{
            "day": 1,
            "exercises": [
              {{
                "name": "exercise_name_from_available_list",
                "sets": number,
                "reps": number,
                "rest_seconds": 30,
                "notes": "specific instruction for this patient"
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

RULES:
- Only use exercises from AVAILABLE_EXERCISES list
- Respect phase limits strictly (no exceeding angles!)
- Start conservative, progress gradually
- Include rest days (2-3 per week)
- ALWAYS reply in the user's selected language
- Be empathetic and encouraging
"""
# - Reply in patient's language (Arabi  English)

# ── Helpers ───────────────────────────────────────────────────────────────────
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


def print_assessment(plan: dict):
    """بيطبع ملخص التشخيص بشكل واضح."""
    a = plan.get("assessment", {})
    p = plan.get("patient", {})

    print("\n" + "="*55)
    print("  DIAGNOSIS SUMMARY")
    print("="*55)
    print(f"  Injury        : {p.get('injury', 'N/A')}")
    print(f"  Weeks post-op : {p.get('weeks_post_op', 'N/A')}")
    print(f"  Pain level    : {p.get('pain_level', 'N/A')}/10")
    print(f"  Full extension: {'Yes' if p.get('extension_full') else 'No'}")
    print(f"  Swelling      : {p.get('swelling', 'N/A')}")
    print(f"  Current flex  : {p.get('current_flexion', 'N/A')}°")
    print(f"\n  Phase Assigned: {a.get('current_phase', '?')} — {a.get('phase_name', '')}")
    print(f"  Rationale     : {a.get('phase_rationale', '')}")

    if a.get('key_deficits'):
        print(f"\n  Key deficits:")
        for d in a['key_deficits']:
            print(f"    • {d}")

    if a.get('precautions'):
        print(f"\n  ⚠️  Precautions:")
        for pr in a['precautions']:
            print(f"    ! {pr}")
    print("="*55)


# ── Main Agent ────────────────────────────────────────────────────────────────
def run_rehab_agent() -> dict | None:
    print("\n" + "="*55)
    print("  FormaFix — Rehabilitation Planning Agent")
    print(f"  AI: {PROVIDER.upper()}")
    print("  Protocol: MGH 2024 + MOON + جامعة بنها 2022")
    print("="*55)
    # print("Tell me about your injury. (type 'quit' to exit)\n")

    conversation = []
    language = None

    # # فتح المحادثة
    # opening = ask_ai(
    #     messages=[{"role": "user",
    #                "content": "Hello, I need rehabilitation help for my knee injury."}],
    #     system_prompt=SYSTEM_PROMPT
    # )
    # print(f"FormaFix Agent:\n{opening}\n")
    # conversation += [
    #     {"role": "user",
    #      "content": "Hello, I need rehabilitation help for my knee injury."},
    #     {"role": "assistant", "content": opening},
    # ]
    # اختيار اللغة
    print("FormaFix Agent:")
    print("Hi! Please choose your preferred language: Arabic or English?\n")


    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n[FormaFix] Session ended.")
            return None
          
        # ── تحديد اللغة أول مرة ─────────────────────────────
        if language is None:
            if "arabic" in user_input.lower():
                language = "Arabic"
            elif "english" in user_input.lower():
                language = "English"
            else:
                print("Please type 'Arabic' or 'English'.\n")
                continue

            print(f"[OK] Language set to {language}\n")
            
            conversation.append({
                "role": "user",
                "content": f"The user prefers {language}. Start the assessment."
            })
            continue

        conversation.append({"role": "user", "content": user_input})
        response = ask_ai(conversation, system_prompt=SYSTEM_PROMPT)
        plan = extract_plan(response)

        if plan:
            msg = clean_response(response)
            if msg:
                print(f"\nFormaFix Agent:\n{msg}")

            save_plan(plan)
            print_assessment(plan)

            print(f"\n[OK] Plan saved to plan.json")
            print(f"  Total weeks : {plan['plan']['total_weeks']}")
            print("Next: python session_runner.py\n")
            return plan
        else:
            print(f"\nFormaFix Agent:\n{response}\n")
            conversation.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    run_rehab_agent()