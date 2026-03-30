EXERCISES = {
    # ACL Rehabilitation
    '1': {'name': 'straight_leg_raise',      'joint': 'hip',   'display': 'Straight Leg Raise (ACL)'},
    '2': {'name': 'terminal_knee_extension', 'joint': 'knee',  'display': 'Terminal Knee Extension (ACL)'},
    '3': {'name': 'mini_squat',              'joint': 'knee',  'display': 'Mini Squat (ACL)'},
    '4': {'name': 'hamstring_curl',          'joint': 'knee',  'display': 'Hamstring Curl (ACL)'},

    # Shoulder Rehabilitation
    '5': {'name': 'pendulum',                'joint': 'shoulder', 'display': 'Pendulum (Shoulder)'},
    '6': {'name': 'external_rotation',       'joint': 'elbow',    'display': 'External Rotation (Shoulder)'},
    '7': {'name': 'wall_slide',              'joint': 'shoulder', 'display': 'Wall Slide (Shoulder)'},
    '8': {'name': 'shoulder_abduction',      'joint': 'shoulder', 'display': 'Shoulder Abduction'},
}

def select_exercise():
    print("\n" + "="*40)
    print("     FormaFix — Select Exercise")
    print("="*40)
    print("\n── ACL Rehabilitation ──")
    for k in ['1','2','3','4']:
        print(f"  {k}. {EXERCISES[k]['display']}")
    print("\n── Shoulder Rehabilitation ──")
    for k in ['5','6','7','8']:
        print(f"  {k}. {EXERCISES[k]['display']}")
    print()

    while True:
        choice = input("Enter number (1-8): ").strip()
        if choice in EXERCISES:
            selected = EXERCISES[choice]
            print(f"\n✅ Selected: {selected['display']}\n")
            return selected
        print("❌ Invalid — enter a number from 1 to 8")