# main.py — FormaFix Entry Point
from rehab_agent import run_rehab_agent
from session_runne import run_session
from progress_summary import run_progress_summary
from adaptive_plan import run_adaptive_plan
import os

def main():
    print("\n" + "="*50)
    print("     FormaFix — AI Physical Therapy")
    print("="*50)
    print("\n  1. New Patient    (generate rehab plan)")
    print("  2. Start Session  (follow today's plan)")
    print("  3. View Summary   (last session report)")
    print("  4. Adaptive Plan  (update plan by AI)")
    print("  5. Exit")
    print()

    while True:
        choice = input("  Choose (1-5): ").strip()

        if choice == '1':
            run_rehab_agent()

        elif choice == '2':
            if not os.path.exists("plan.json"):
                print("\n  [!] No plan found. Run option 1 first.\n")
            else:
                run_session()

        elif choice == '3':
            if not os.path.exists("session_data.json"):
                print("\n  [!] No sessions yet. Run option 2 first.\n")
            else:
                run_progress_summary()

        elif choice == '4':
            if not os.path.exists("plan.json"):
                print("\n  [!] No plan found. Run option 1 first.\n")
            else:
                run_adaptive_plan()

        elif choice == '5':
            print("\n  Goodbye! Keep up the recovery! 💪\n")
            break

        else:
            print("  Invalid choice.\n")

if __name__ == "__main__":
    main()