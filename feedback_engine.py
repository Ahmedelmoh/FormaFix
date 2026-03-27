class FeedbackEngine:

    # =====================================================================
    # منطق الـ feedback:
    # كل تمرين عنده مراحل (phases) — كل مرحلة ليها شرط على الزاوية
    # ورسالة واضحة للمريض.
    #
    # الترتيب مهم: الشروط بتتفحص من فوق لتحت،
    # أول شرط يتحقق بيتبعت رسالته وبيوقف.
    # =====================================================================

    def get_feedback(self, exercise, joint_angles):
        """
        Parameters
        ----------
        exercise      : اسم التمرين  (مثلاً 'mini_squat')
        joint_angles  : dict فيه الزوايا الحالية
                        مثلاً {'left_knee': 145, 'left_hip': 170}

        Returns
        -------
        str : رسالة feedback واحدة واضحة
        """

        # ── تمارين موجودة مسبقاً ─────────────────────────────────────

        if exercise == 'bicep_curl':
            elbow = joint_angles.get('left_elbow', 0)
            if elbow > 160:
                return "Lower your elbow more!"
            elif elbow < 40:
                return "Don't over-curl!"
            elif 50 <= elbow <= 80:
                return "Perfect curl position!"
            return "Keep going!"

        elif exercise == 'squat':
            knee = joint_angles.get('left_knee', 0)
            if knee > 160:
                return "Go deeper!"
            elif knee < 70:
                return "Too deep, come up a bit!"
            elif 85 <= knee <= 110:
                return "Perfect squat depth!"
            return "Keep going!"

        elif exercise == 'shoulder_raise':
            shoulder = joint_angles.get('left_shoulder', 0)
            if shoulder < 80:
                return "Raise your arm higher!"
            elif shoulder > 100:
                return "Lower your arm slightly!"
            else:
                return "Perfect shoulder position!"

        # ── تمارين الرباط الصليبي (ACL) ─────────────────────────────

        elif exercise == 'straight_leg_raise':
            # نقيس زاوية الورك (hip)
            # البداية: رجل مفرودة على الأرض (~170°)
            # الهدف:   رجل مرفوعة (~65°)
            hip = joint_angles.get('left_hip', 0)

            if hip > 140:
                # لسه في البداية، الرجل على الأرض
                return "Lift your leg up slowly — keep it straight!"
            elif 100 < hip <= 140:
                # بدأ يرفع بس لسه مش وصل
                return "Keep raising — don't bend your knee!"
            elif 55 <= hip <= 80:
                # وصل للهدف
                return "Perfect! Hold for 3 seconds."
            elif hip < 55:
                # رفع أكتر من اللازم
                return "Too high — lower your leg slightly."
            return "Raise your leg steadily."

        elif exercise == 'terminal_knee_extension':
            # نقيس زاوية الركبة (knee)
            # البداية: ركبة مثنية (~45°)
            # الهدف:   ركبة ممدودة (~165°)
            knee = joint_angles.get('left_knee', 0)

            if knee < 30:
                return "Too much bend — start from about 45 degrees."
            elif 30 <= knee < 90:
                # لسه في مرحلة الثني
                return "Straighten your knee slowly."
            elif 90 <= knee < 140:
                # في المنتصف
                return "Keep extending — you're halfway there!"
            elif 140 <= knee < 155:
                # قرب من الهدف
                return "Almost fully extended — push a little more!"
            elif knee >= 155:
                # وصل
                return "Full extension — excellent!"
            return "Extend your knee."

        elif exercise == 'mini_squat':
            # نقيس زاوية الركبة (knee)
            # البداية: واقف (~160°)
            # الهدف:   نزول جزئي (~125°)
            knee = joint_angles.get('left_knee', 0)

            if knee > 155:
                # واقف — ينزل
                return "Bend your knees slightly — go down slowly."
            elif 130 <= knee <= 155:
                # نزل شوية بس مش وصل
                return "A little deeper — keep your back straight!"
            elif 110 <= knee < 130:
                # وصل للهدف
                return "Perfect mini squat depth!"
            elif knee < 110:
                # نزل أكتر من اللازم
                return "Too deep for a mini squat — come up a bit."
            return "Maintain controlled movement."

        elif exercise == 'hamstring_curl':
            # نقيس زاوية الركبة (knee)
            # البداية: رجل مفرودة (~170°)
            # الهدف:   ركبة متنية (~95°)
            knee = joint_angles.get('left_knee', 0)

            if knee > 155:
                # رجل مفرودة — يثنيها
                return "Curl your leg up — bend your knee backward."
            elif 120 <= knee <= 155:
                # بدأ يثني بس لسه مش وصل
                return "Keep curling — bring your heel toward you!"
            elif 80 <= knee < 120:
                # وصل للهدف
                return "Great curl! Hold briefly."
            elif knee < 80:
                # ثنى أكتر من اللازم
                return "Too far — don't over-flex."
            return "Curl your leg smoothly."

        # ── تمارين الكتف (Shoulder) ──────────────────────────────────

        elif exercise == 'pendulum':
            # نقيس زاوية الكتف (shoulder)
            # حركة صغيرة جداً — تأرجح بسيط
            shoulder = joint_angles.get('left_shoulder', 0)

            if shoulder < 5:
                return "Let your arm hang and swing gently."
            elif 5 <= shoulder <= 30:
                return "Good pendulum motion — keep it relaxed!"
            elif shoulder > 30:
                return "Too much movement — smaller circles."
            return "Relax your shoulder and swing."

        elif exercise == 'external_rotation':
            # نقيس زاوية الكوع (elbow) — لازم يفضل ~90°
            # ونقيس زاوية الكتف (shoulder) للتدوير
            elbow    = joint_angles.get('left_elbow', 0)
            shoulder = joint_angles.get('left_shoulder', 0)

            # أول حاجة — الكوع لازم يكون ثابت عند 90°
            if elbow < 75 or elbow > 105:
                return "Keep your elbow at 90 degrees — don't move it!"

            # لو الكوع تمام — نشوف التدوير
            if shoulder < 50:
                return "Rotate your forearm outward more."
            elif 55 <= shoulder <= 85:
                return "Perfect rotation range!"
            elif shoulder > 85:
                return "Too much rotation — stay within comfort."
            return "Rotate slowly and controlled."

        elif exercise == 'wall_slide':
            # نقيس زاوية الكتف (shoulder)
            # البداية: ~65°   النهاية: ~155°
            shoulder = joint_angles.get('left_shoulder', 0)

            if shoulder < 50:
                return "Start with your arms at shoulder height against the wall."
            elif 50 <= shoulder < 90:
                return "Slide your arms up the wall slowly."
            elif 90 <= shoulder < 130:
                return "Halfway — keep pressing lightly on the wall!"
            elif 130 <= shoulder <= 165:
                return "Excellent range! You reached full slide."
            elif shoulder > 165:
                return "Don't force it — stay within your pain-free range."
            return "Slide upward smoothly."

        elif exercise == 'shoulder_abduction':
            # نقيس زاوية الكتف (shoulder) — رفع جانبي
            # البداية: ~12°   النهاية: ~85°
            shoulder = joint_angles.get('left_shoulder', 0)

            if shoulder < 20:
                return "Raise your arm out to the side slowly."
            elif 20 <= shoulder < 60:
                return "Keep raising — arm should reach shoulder level."
            elif 60 <= shoulder <= 95:
                return "Perfect! Arm is parallel to the ground."
            elif shoulder > 95:
                return "Too high for this exercise — lower slightly."
            return "Raise your arm to the side."

        # ── fallback ──────────────────────────────────────────────────
        return "Keep going!"