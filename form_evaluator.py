"""
form_evaluator.py — FormaFix
==============================
Sources:
  1. MGH (Massachusetts General Hospital) ACL Protocol 2024
  2. MOON Knee Group ACL Rehabilitation Program
  3. جامعة بنها 2022 - برنامج تأهيلي للرباط الصليبي
  4. Physio-Pedia ACL Rehabilitation

قاعدة مهمة: كل التمارين هنا تتعمل بدون معدات
  ✅ Quad Set         - شد العضلة الرباعية
  ✅ Ankle Pump       - تحريك الكاحل
  ✅ Heel Slide       - ثني الركبة مستلقي
  ✅ Straight Leg Raise - رفع الرجل مستقيمة
  ✅ Calf Raise       - رفع الكعب
  ✅ Hip Abduction    - فتح الورك
  ✅ Bridge           - رفع الحوض
  ✅ Mini Squat       - نزول جزئي (حتى 60°)
  ✅ Hamstring Curl   - ثني الركبة للخلف
  ✅ Terminal Knee Ext - مد الركبة من ثني بسيط
  ✅ Step Up          - صعود درجة (درجة صغيرة)
  ✅ Single Leg Stand - الوقوف على رجل واحدة
  ❌ Leg Press Machine - محتاج جهاز
  ❌ Seated Leg Extension - محتاج جهاز

مراحل MGH:
  Phase 1 (0-2 أسبوع)   : حماية + مد كامل + تنشيط الرباعية
  Phase 2 (3-5 أسابيع)  : مدى كامل + طبيعي المشي + تقوية
  Phase 3 (6-8 أسابيع)  : تقوية + حركة صحيحة
  Phase 4 (9-12 أسبوع)  : plyometrics أساسية
  Phase 5 (3-5 شهور)    : عودة للجري
  Phase 6 (6+ شهور)     : عودة للرياضة
"""


class FormEvaluator:

    REFERENCE_ANGLES = {

        # =====================================================================
        # PHASE 1 (0-2 أسبوع): أولوية = مد كامل + تنشيط الرباعية
        # MGH: "Restore full extension" - most critical goal
        # =====================================================================

        # Quad Set: الركبة مفرودة تماماً (0°)، شد العضلة الرباعية
        # MGH: NMES + quad sets - highest priority Phase 1
        'quad_set': {
            'start_angle': 15,   # بداية مع انثناء بسيط
            'end_angle':    0,   # هدف: مد كامل 0°
            'tolerance':    5,
            'joint':       'knee',
            'phase': 1,
            'no_equipment': True,
            'position': 'lying',
        },

        # Ankle Pump: تحريك الكاحل لتحسين الدورة الدموية
        # MGH Phase 1 - swelling management
        'ankle_pump': {
            'start_angle':  90,   # قدم عمودية
            'end_angle':   120,   # قدم مرفوعة للأعلى
            'tolerance':    15,
            'joint':       'ankle',
            'phase': 1,
            'no_equipment': True,
            'position': 'lying',
        },

        # Heel Slide Phase 1: disabled in standing mode
        # (kept for compatibility but not used in demo)
        'heel_slide_p1': {
            'start_angle': 170,
            'end_angle':   135,
            'tolerance':    10,
            'joint':       'knee',
            'phase': 1,
            'no_equipment': True,
            'position': 'lying',
        },

        # Straight Leg Raise: رفع الرجل مستقيمة
        # MGH: "Do not perform if knee extension lag"
        # نقيس: زاوية الورك (hip)
        'straight_leg_raise': {
            'start_angle': 155,   # رجل على الأرض
            'end_angle':    65,   # رجل مرفوعة ~65°
            'tolerance':    10,
            'joint':       'hip',
            'phase': 1,
            'no_equipment': True,
            'position': 'lying',
        },

        # Hip Abduction: فتح الورك جانباً
        # MGH Phase 1 strengthening
        'hip_abduction': {
            'start_angle':  10,   # رجل جنب الجسم
            'end_angle':    40,   # فتح جانبي ~40°
            'tolerance':    10,
            'joint':       'hip',
            'phase': 1,
            'no_equipment': True,
            'position': 'lying',
        },

        # Terminal Knee Extension: مد الركبة من 30° لـ 0°
        # MGH: "Multi-angle isometrics 90 and 60 deg"
        # بدون معدات: نعمله بوضع بروول تحت الركبة
        'terminal_knee_extension': {
            'start_angle':  30,   # ركبة منثنية بسيط
            'end_angle':     0,   # مد كامل
            'tolerance':     5,
            'joint':       'knee',
            'phase': 1,
            'no_equipment': True,
            'position': 'lying',
        },

        # Calf Raise: رفع الكعب (واقف)
        # MGH Phase 1: "Calf raises"
        'calf_raise': {
            'start_angle':  90,   # قدم مسطحة
            'end_angle':   120,   # رفع على الأصابع
            'tolerance':    10,
            'joint':       'ankle',
            'phase': 1,
            'no_equipment': True,
            'position': 'standing',
        },

        # =====================================================================
        # PHASE 2 (3-5 أسابيع): مدى كامل + طبيعية المشي + تقوية
        # MGH: "Restore full flexion (contralateral side)"
        # =====================================================================

        # Heel Slide Phase 2: ثني حتى 90°
        # MGH Phase 2 goal: full flexion = same as other leg
        'heel_slide_p2': {
            'start_angle': 170,
            'end_angle':    90,   # ثني 90°
            'tolerance':    15,
            'joint':       'knee',
            'phase': 2,
            'no_equipment': True,
            'position': 'lying',
        },

        # Mini Squat: واقف
        # Phase 1 demo: max 30° bend (knee ~150°) - very conservative
        # Phase 2: max 60° bend (knee ~120°) - MGH 2024
        # The agent decides which depth based on phase
        'mini_squat': {
            'start_angle': 155,   # واقف
            'end_angle':   120,   # نزول 60° = زاوية ركبة 120° (Phase 2)
            'tolerance':    20,   # tolerance واسعة تتسع لـ Phase 1 (150°) و Phase 2 (120°)
            'joint':       'knee',
            'phase': 2,
            'no_equipment': True,
            'position': 'standing',
        },

        # Hamstring Curl Phase 2: ثني بسيط
        # MGH: "Standing/Prone hamstring curls"
        'hamstring_curl_p2': {
            'start_angle': 160,   # رجل مفرودة
            'end_angle':   100,   # ثني ~70° (يعني زاوية ركبة 110°)
            'tolerance':    15,
            'joint':       'knee',
            'phase': 2,
            'no_equipment': True,
            'position': 'standing',
        },

        # Bridge: رفع الحوض
        # MGH Phase 2: "bridge & unilateral bridge"
        'bridge': {
            'start_angle':  90,   # ركبة منثنية 90°
            'end_angle':    90,   # نفس الزاوية، بس الحوض مرفوع
            'tolerance':    15,
            'joint':       'knee',
            'phase': 2,
            'no_equipment': True,
            'position': 'lying',
        },

        # Step Up: صعود درجة صغيرة (10-15 سم)
        # MGH Phase 2: "Step ups and step ups with march"
        'step_up': {
            'start_angle': 170,   # واقف
            'end_angle':   140,   # زاوية الركبة لما تطلع الدرجة
            'tolerance':    15,
            'joint':       'knee',
            'phase': 2,
            'no_equipment': True,
            'position': 'standing',
        },

        # Single Leg Stand: الوقوف على رجل واحدة (توازن)
        # MGH Phase 2: "Single leg standing balance (knee slightly flexed)"
        'single_leg_stand': {
            'start_angle': 155,   # ركبة شبه مفرودة
            'end_angle':   160,   # ركبة مفرودة مع انثناء بسيط
            'tolerance':    10,
            'joint':       'knee',
            'phase': 2,
            'no_equipment': True,
            'position': 'standing',
        },

        # =====================================================================
        # PHASE 3 (6-8 أسابيع): تقوية + حركة صحيحة
        # MGH: "Safely progress strengthening, Promote proper movement patterns"
        # =====================================================================

        # Squat Phase 3: نزول أعمق مع التركيز على الميكانيكا
        # MGH Phase 3: "Squat to chair" - focus on proper control
        'squat_p3': {
            'start_angle': 155,
            'end_angle':    80,   # نزول حتى 90° ثني
            'tolerance':    15,
            'joint':       'knee',
            'phase': 3,
            'no_equipment': True,
            'position': 'standing',
        },

        # Hamstring Curl Phase 3: ثني حتى 90°
        'hamstring_curl_p3': {
            'start_angle': 160,
            'end_angle':    90,   # ثني 90°
            'tolerance':    15,
            'joint':       'knee',
            'phase': 3,
            'no_equipment': True,
            'position': 'standing',
        },

        # Lateral Lunge: انفراج جانبي
        # MGH Phase 3: "Lateral lunges"
        'lateral_lunge': {
            'start_angle': 160,
            'end_angle':   120,   # ثني 60° في الرجل المتقدمة
            'tolerance':    15,
            'joint':       'knee',
            'phase': 3,
            'no_equipment': True,
            'position': 'standing',
        },

        # Romanian Deadlift: ميلان للأمام على رجل واحدة
        # MGH Phase 3: "Romanian deadlift and single leg deadlift"
        'romanian_deadlift': {
            'start_angle': 160,
            'end_angle':   145,   # انحناء للأمام مع الركبة شبه مفرودة
            'tolerance':    15,
            'joint':       'knee',
            'phase': 3,
            'no_equipment': True,
            'position': 'standing',
        },

        # =====================================================================
        # PHASE 4 (9-12 أسبوع): plyometrics أساسية
        # MGH: "Bilateral PWB plyometrics"
        # =====================================================================

        # Full Squat: نزول كامل
        'full_squat': {
            'start_angle': 170,
            'end_angle':    70,   # نزول كامل ~110° ثني
            'tolerance':    15,
            'joint':       'knee',
            'phase': 4,
            'no_equipment': True,
            'position': 'standing',
        },

        # Lunge: انفراج أمامي
        # MGH Phase 4: "Slide board lunges"
        'lunge': {
            'start_angle': 170,
            'end_angle':    90,   # ثني 90° في الرجل الأمامية
            'tolerance':    15,
            'joint':       'knee',
            'phase': 4,
            'no_equipment': True,
            'position': 'standing',
        },

        # =====================================================================
        # تمارين الكتف
        # =====================================================================

        'pendulum': {
            'start_angle':   5,
            'end_angle':    25,
            'tolerance':    10,
            'joint':       'shoulder',
            'phase': 1,
            'no_equipment': True,
            'position': 'standing',
        },
        'external_rotation': {
            'start_angle':  90,
            'end_angle':    70,
            'tolerance':    15,
            'joint':       'elbow',
            'phase': 2,
            'no_equipment': True,
            'position': 'standing',
        },
        'wall_slide': {
            'start_angle':  65,
            'end_angle':   155,
            'tolerance':    20,
            'joint':       'shoulder',
            'phase': 2,
            'no_equipment': True,
            'position': 'standing',
        },
        'shoulder_abduction': {
            'start_angle':  12,
            'end_angle':    85,
            'tolerance':    15,
            'joint':       'shoulder',
            'phase': 2,
            'no_equipment': True,
            'position': 'standing',
        },
    }

    # =========================================================================
    def evaluate(self, exercise, joint_name, current_angle):
        if exercise not in self.REFERENCE_ANGLES:
            return 100, "Exercise not found"

        ref = self.REFERENCE_ANGLES[exercise]
        end = ref['end_angle']
        tol = ref['tolerance']
        dev = abs(current_angle - end)

        if dev <= tol:
            score = 100
        elif dev <= tol * 2:
            score = 75
        elif dev <= tol * 3:
            score = 50
        else:
            score = max(0, 100 - int(dev * 2))

        score = round(score)

        if score >= 90:
            feedback = "Great form!"
        elif score >= 75:
            feedback = "Almost there!"
        elif score >= 50:
            feedback = "Fix your form!"
        else:
            feedback = "Incorrect position!"

        return score, feedback

    def get_exercise_info(self, exercise):
        ref = self.REFERENCE_ANGLES.get(exercise, {})
        return {
            'phase':        ref.get('phase', 0),
            'no_equipment': ref.get('no_equipment', True),
            'position':     ref.get('position', 'unknown'),
            'joint':        ref.get('joint', ''),
            'end_angle':    ref.get('end_angle', 0),
            'tolerance':    ref.get('tolerance', 15),
        }