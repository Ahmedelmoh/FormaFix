class FormEvaluator:

    # =====================================================================
    # الزوايا المرجعية لكل تمرين
    # كل تمرين فيه:
    #   - start_angle : زاوية وضع البداية
    #   - end_angle   : زاوية وضع النهاية (الهدف)
    #   - tolerance   : هامش القبول (±درجة) — لو الانحراف فيه يعتبر "ممتاز"
    #   - joint       : المفصل المقاس
    # =====================================================================

    REFERENCE_ANGLES = {

        # ── تمارين موجودة مسبقاً ─────────────────────────────────────────
        'bicep_curl': {
            'elbow_down': 160,   # ذراع مفرودة
            'elbow_up':    50,   # ذراع متنية
        },
        'squat': {
            'knee_down': 90,     # نزول كامل
            'knee_up':  170,     # واقف
        },
        'shoulder_raise': {
            'shoulder_up':   90,
            'shoulder_down': 10,
        },

        # ── تمارين الرباط الصليبي (ACL) ──────────────────────────────────

        # تمرين 1: رفع الرجل وهي مستقيمة
        # المريض مستلقي، يرفع الرجل لفوق بدون ثني الركبة
        # نقيس: زاوية الورك (hip) بين الجذع والفخذ
        'straight_leg_raise': {
            'start_angle': 170,   # رجل مفرودة على الأرض
            'end_angle':    65,   # رجل مرفوعة ~65 درجة
            'tolerance':    15,   # ±15 درجة مقبولة
            'joint':       'hip',
        },

        # تمرين 2: مد الركبة النهائي
        # المريض واقف، يمد الركبة من نص انثناء لمد كامل
        # نقيس: زاوية الركبة (knee)
        'terminal_knee_extension': {
            'start_angle':  45,   # ركبة مثنية ~45°
            'end_angle':   165,   # ركبة ممدودة تقريباً
            'tolerance':    10,
            'joint':       'knee',
        },

        # تمرين 3: نزول جزئي (Mini Squat)
        # نزول بسيط مش كامل — مناسب بعد عملية ACL
        # نقيس: زاوية الركبة (knee)
        'mini_squat': {
            'start_angle': 160,   # واقف
            'end_angle':   125,   # نزول جزئي ~125°
            'tolerance':    15,
            'joint':       'knee',
        },

        # تمرين 4: ثني الركبة للخلف (Hamstring Curl)
        # واقف، يثني الركبة من الخلف لأعلى ما يقدر
        # نقيس: زاوية الركبة (knee)
        'hamstring_curl': {
            'start_angle': 170,   # رجل مفرودة
            'end_angle':    95,   # ركبة متنية ~95°
            'tolerance':    15,
            'joint':       'knee',
        },

        # ── تمارين الكتف (Shoulder) ───────────────────────────────────────

        # تمرين 5: تأرجح الذراع (Pendulum)
        # المريض ينحني، الذراع معلق ويتأرجح بشكل دائري
        # نقيس: زاوية الكتف (shoulder) — حركة صغيرة مقصودة
        'pendulum': {
            'start_angle':   5,   # ذراع معلق تقريباً عمودي
            'end_angle':    25,   # تأرجح ~25°
            'tolerance':    10,
            'joint':       'shoulder',
        },

        # تمرين 6: تدوير الكتف للخارج (External Rotation)
        # الكوع ثابت عند 90°، يدور الذراع السفلية للخارج
        # نقيس: زاوية الكوع (elbow) — نتأكد إنه ثابت عند 90°
        'external_rotation': {
            'start_angle':  90,   # كوع عند 90° — وضع ثابت
            'end_angle':    70,   # تدوير للخارج ~70°
            'tolerance':    15,
            'joint':       'elbow',
        },

        # تمرين 7: انزلاق الذراع على الحيط (Wall Slide)
        # الذراع على الحيط، يرفعها لفوق ببطء
        # نقيس: زاوية الكتف (shoulder)
        'wall_slide': {
            'start_angle':  65,   # بداية — ذراع في المنتصف
            'end_angle':   155,   # نهاية — ذراع فوق
            'tolerance':    20,
            'joint':       'shoulder',
        },

        # تمرين 8: رفع الذراع جانبي (Shoulder Raise / Abduction)
        # يرفع الذراع جانباً لمستوى الكتف
        # نقيس: زاوية الكتف (shoulder)
        'shoulder_abduction': {
            'start_angle':  12,   # جنب الجسم
            'end_angle':    85,   # موازي للأرض
            'tolerance':    15,
            'joint':       'shoulder',
        },
    }

    # =====================================================================
    def evaluate(self, exercise, joint_name, current_angle):
        """
        بيقيس الفورم وبيرجع (score, feedback)

        Parameters
        ----------
        exercise      : اسم التمرين (مثلاً 'mini_squat')
        joint_name    : اسم المفصل (مش مستخدم حالياً، للتوثيق)
        current_angle : الزاوية الحالية من الكاميرا

        Returns
        -------
        score    : int  — من 0 (غلط جداً) لـ 100 (مثالي)
        feedback : str  — رسالة للمريض
        """
        if exercise not in self.REFERENCE_ANGLES:
            return 100, "Exercise not found"

        ref = self.REFERENCE_ANGLES[exercise]

        # التمارين القديمة (bicep_curl, squat, shoulder_raise)
        # بتشتغل بنظام min/max
        if 'start_angle' not in ref:
            angles = list(ref.values())
            min_angle = min(angles)
            max_angle = max(angles)

            if current_angle < min_angle:
                deviation = min_angle - current_angle
            elif current_angle > max_angle:
                deviation = current_angle - max_angle
            else:
                deviation = 0

            score = max(0, 100 - (deviation * 2))

        # التمارين الجديدة: بتشتغل بنظام start/end/tolerance
        else:
            start   = ref['start_angle']
            end     = ref['end_angle']
            tol     = ref['tolerance']

            # الانحراف عن الـ end_angle (الهدف)
            deviation = abs(current_angle - end)

            if deviation <= tol:
                # جوه الهامش — ممتاز
                score = 100
            elif deviation <= tol * 2:
                # قريب بس مش وصل
                score = 75
            elif deviation <= tol * 3:
                # محتاج تحسين
                score = 50
            else:
                # بعيد جداً
                score = max(0, 100 - int(deviation * 2))

        score = round(score)

        # ── Feedback بناءً على الـ score ──────────────────────────────
        if score >= 90:
            feedback = "Great form!"
        elif score >= 75:
            feedback = "Almost there!"
        elif score >= 50:
            feedback = "Fix your form!"
        else:
            feedback = "Stop — incorrect position!"

        return score, feedback