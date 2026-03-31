"""
feedback_engine.py — FormaFix
==============================
Feedback مبني على MGH Protocol 2024 + MOON + جامعة بنها 2022
كل التمارين بدون معدات.

قواعد MGH المهمة:
  ✓ Phase 1: Quad activation = FIRST priority
  ✓ Phase 1: Full extension (0°) = must achieve before Phase 2
  ✓ Phase 1: No SLR if extension lag exists
  ✓ Phase 2: Mini squat max 60° (MGH 2024)
  ✓ Phase 3: Focus on proper movement mechanics
  ✓ Pain/swelling = stop and rest
"""


class FeedbackEngine:

    # رسائل تحذير عند تجاوز الحد
    PHASE_WARNINGS = {
        1: "⚠️ Phase 1 limit — protect your graft!",
        2: "⚠️ Phase 2 limit — do not exceed this range!",
        3: "⚠️ Check with your physio before going deeper",
    }

    def get_feedback(self, exercise, joint_angles):
        """
        Parameters
        ----------
        exercise     : اسم التمرين
        joint_angles : dict مثل {'left_knee': 145, 'left_hip': 160}

        Returns
        -------
        str : رسالة feedback واضحة
        """

        # ── PHASE 1 EXERCISES ─────────────────────────────────────────────────

        if exercise == 'quad_set':
            # MGH: highest priority Phase 1 - must achieve before SLR
            knee = joint_angles.get('left_knee', 0)
            if knee > 20:
                return f"Flatten your knee completely — push it down to 0°, now at {knee:.0f}°"
            elif 10 < knee <= 20:
                return "Almost flat — push knee down just a bit more"
            elif knee <= 10:
                return "Knee is flat! Now tighten your thigh muscle hard — hold 10 sec"
            return "Push your knee down to the floor"

        elif exercise == 'ankle_pump':
            # MGH Phase 1: swelling management
            ankle = joint_angles.get('left_ankle', 90)
            if ankle < 100:
                return "Pump your foot up and down — flex and point, 20 reps"
            elif 100 <= ankle <= 130:
                return "Good ankle pump — keep it going, improves circulation"
            return "Flex and point your foot repeatedly"

        elif exercise == 'heel_slide_p1':
            # MGH + MOON: Phase 1 max 45° bend (knee angle ~135°)
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Slide your heel slowly toward you — bend your knee gently"
            elif 150 <= knee <= 165:
                return f"Keep sliding — at {bend:.0f}° bend, Phase 1 target is 45°"
            elif 130 <= knee < 150:
                return f"Phase 1 perfect depth — 45° reached! Pause then return slowly"
            elif knee < 130:
                return f"⚠️ Stop at 45° in Phase 1 — graft protection! Come back up"
            return "Slide heel toward you gently"

        elif exercise == 'straight_leg_raise':
            # MGH: "Do not perform if extension lag exists"
            hip = joint_angles.get('left_hip', 0)
            if hip > 155:
                return "Tighten quad first, then lift leg to 45-65° — keep knee straight"
            elif 100 < hip <= 155:
                return f"Keep lifting — {hip:.0f}° now, target is 65°"
            elif 55 <= hip <= 80:
                return "Perfect height — 65°! Hold 3 seconds, lower slowly"
            elif hip < 55:
                return f"Slightly too high — lower to 65° range"
            return "Lift leg slowly with knee locked straight"

        elif exercise == 'hip_abduction':
            # MGH Phase 1: hip abduction for glute activation
            hip = joint_angles.get('left_hip', 0)
            if hip < 15:
                return "Raise your leg out to the side — keep toes pointing forward"
            elif 15 <= hip <= 45:
                return f"Good hip abduction — {hip:.0f}°, keep pelvis stable"
            elif hip > 45:
                return f"Good range — hold briefly then lower with control"
            return "Lift leg sideways steadily"

        elif exercise == 'terminal_knee_extension':
            # MGH: "multi-angle isometrics" - done lying with rolled towel under knee
            knee = joint_angles.get('left_knee', 0)
            if knee > 40:
                return "Start with knee slightly bent (~30°), then straighten fully"
            elif 10 < knee <= 40:
                return f"Straighten your knee — {knee:.0f}° remaining to reach 0°"
            elif knee <= 10:
                return "Full extension — excellent! Squeeze quad hard, hold 5 sec"
            return "Push knee to full 0° extension"

        elif exercise == 'calf_raise':
            # MGH Phase 1: calf raises for circulation + strength
            ankle = joint_angles.get('left_ankle', 90)
            if ankle < 95:
                return "Rise up slowly onto your toes — both feet together"
            elif 95 <= ankle <= 120:
                return f"Good calf raise — {ankle:.0f}°, hold at top for 2 sec"
            elif ankle > 120:
                return "Great height! Lower slowly — 3 seconds down"
            return "Rise on toes, control the descent"

        # ── PHASE 2 EXERCISES ─────────────────────────────────────────────────

        elif exercise == 'heel_slide_p2':
            # MGH Phase 2 goal: full flexion = same as good leg
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Slide heel toward you — Phase 2 target is 90° flexion"
            elif 120 <= knee <= 165:
                return f"Keep sliding — {bend:.0f}° now, target 90°"
            elif 85 <= knee < 120:
                return f"Almost there — {90 - bend:.0f}° more to reach 90°"
            elif knee < 90:
                return "Phase 2 goal reached — 90° flexion! Compare with your other leg"
            return "Slide heel toward you"

        elif exercise == 'mini_squat':
            # MGH Phase 2: "mini squats from 0-60 deg"
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Bend knees slowly — Phase 2 target is 60° bend (not deeper)"
            elif 140 <= knee <= 165:
                return f"Keep bending — {bend:.0f}° now, target 60°"
            elif 115 <= knee < 140:
                return "Phase 2 mini squat depth — 60° reached! Back straight, equal weight"
            elif knee < 115:
                return "⚠️ Too deep for Phase 2 — stop at 60°! Come back up"
            return "Squat to 60° only in Phase 2"

        elif exercise == 'hamstring_curl_p2':
            # MGH Phase 2: "Standing/Prone hamstring curls"
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Stand on good leg, curl surgical leg backward slowly"
            elif 140 <= knee <= 165:
                return f"Keep curling — {bend:.0f}° now, aiming for 70°"
            elif 100 <= knee < 140:
                return f"Good Phase 2 curl — hold briefly then lower with control"
            elif knee < 100:
                return "Good range for Phase 2 — control the return"
            return "Curl your leg smoothly, control both ways"

        elif exercise == 'bridge':
            # MGH Phase 2: "bridge & unilateral bridge"
            knee = joint_angles.get('left_knee', 0)
            if knee > 110:
                return "Feet flat, knees bent ~90°, then push hips up to ceiling"
            elif 80 <= knee <= 110:
                return "Good bridge position — squeeze glutes at the top, hold 3 sec"
            elif knee < 80:
                return "Knees too bent — place feet closer to your back"
            return "Bridge: push hips up, squeeze glutes"

        elif exercise == 'step_up':
            # MGH Phase 2: "Step ups and step ups with march"
            # Use a stair step ~10-15cm
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Step up with surgical leg — control the movement, no pushing off"
            elif 140 <= knee <= 165:
                return f"Good step up — {bend:.0f}° bend, keep knee over 2nd toe"
            elif knee < 140:
                return "Step fully up — straighten knee at the top, then step down slowly"
            return "Step up with control — knee tracks over toes"

        elif exercise == 'single_leg_stand':
            # MGH Phase 2: "Single leg standing balance"
            knee = joint_angles.get('left_knee', 0)
            if knee < 155:
                return "Slight knee bend is fine — focus on not swaying sideways"
            elif 155 <= knee <= 170:
                return "Good single leg stand — keep hips level, hold 30 sec"
            elif knee > 170:
                return "Don't lock knee — keep very slight bend for stability"
            return "Balance on surgical leg — eyes forward"

        # ── PHASE 3 EXERCISES ─────────────────────────────────────────────────

        elif exercise == 'squat_p3':
            # MGH Phase 3: "Squat to chair" - emphasis on proper mechanics
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Phase 3 Squat — sit back into squat, knees track over toes"
            elif 140 <= knee <= 165:
                return f"Keep going — {bend:.0f}° now, target 90°"
            elif 85 <= knee < 140:
                return "Good depth! Keep chest up, weight equal on both legs"
            elif knee < 85:
                return "Deep squat — excellent! Control the return up slowly"
            return "Squat with proper mechanics — chest up, knees forward"

        elif exercise == 'hamstring_curl_p3':
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Phase 3 curl — bring heel up toward your back slowly"
            elif 120 <= knee <= 165:
                return f"Keep curling — {bend:.0f}° now, target 90°"
            elif knee < 90:
                return "Full 90° curl! Hold briefly — now lower in 3 seconds"
            return "Hamstring curl to 90°, control both directions"

        elif exercise == 'lateral_lunge':
            # MGH Phase 3: "Lateral lunges"
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Step wide to the side — bend into the lunge sideways"
            elif 130 <= knee <= 165:
                return f"Good lateral lunge — {bend:.0f}° bend, keep chest up"
            elif 110 <= knee < 130:
                return "Great depth! Push back to start — equal leg strength"
            return "Lunge sideways — keep both feet forward"

        elif exercise == 'romanian_deadlift':
            # MGH Phase 3: "Romanian deadlift"
            knee = joint_angles.get('left_knee', 0)
            if knee < 145:
                return "Keep knee soft but mostly straight — hinge at hip not knee"
            elif 145 <= knee <= 165:
                return "Good RDL position — hinge forward, feel hamstring stretch"
            elif knee > 165:
                return "Hinge forward at the hip — let arms hang, feel the stretch"
            return "Hip hinge — back straight, feel hamstrings"

        # ── PHASE 4 EXERCISES ─────────────────────────────────────────────────

        elif exercise == 'full_squat':
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 165:
                return "Phase 4 Full Squat — go as deep as comfortable with good form"
            elif 120 <= knee <= 165:
                return f"Keep going — {bend:.0f}° now, target 90-110°"
            elif 70 <= knee < 120:
                return f"Great depth — {bend:.0f}°! Heels on floor, chest up"
            elif knee < 70:
                return "Deep full squat — excellent range! Hold briefly"
            return "Full squat — full range of motion"

        elif exercise == 'lunge':
            # MGH Phase 4: "slide board lunges"
            knee = joint_angles.get('left_knee', 0)
            bend = 180 - knee
            if knee > 160:
                return "Step forward into lunge — back knee toward floor"
            elif 120 <= knee <= 160:
                return f"Good lunge — {bend:.0f}° bend, keep front knee over ankle"
            elif knee < 100:
                return "Deep lunge — excellent! Push back to start powerfully"
            return "Lunge forward — control the movement"

        # ── SHOULDER EXERCISES ────────────────────────────────────────────────

        elif exercise == 'pendulum':
            shoulder = joint_angles.get('left_shoulder', 0)
            if shoulder < 5:
                return "Lean forward, let arm hang loose — let gravity swing it"
            elif 5 <= shoulder <= 30:
                return "Good pendulum — relax completely, no muscle effort needed"
            elif shoulder > 30:
                return "Too much effort — let gravity do the work, smaller swing"
            return "Relax arm completely — gravity does the work"

        elif exercise == 'external_rotation':
            elbow    = joint_angles.get('left_elbow', 0)
            shoulder = joint_angles.get('left_shoulder', 0)
            if elbow < 75 or elbow > 105:
                return f"Fix elbow first — keep it at exactly 90°, now at {elbow:.0f}°"
            if shoulder < 50:
                return f"Rotate forearm outward — {shoulder:.0f}° now, target 60-80°"
            elif 55 <= shoulder <= 85:
                return "Perfect external rotation — hold this position!"
            elif shoulder > 85:
                return "Good but ease back slightly — stay pain-free"
            return "Rotate slowly — elbow stays fixed at 90°"

        elif exercise == 'wall_slide':
            shoulder = joint_angles.get('left_shoulder', 0)
            if shoulder < 50:
                return "Arms at shoulder height on wall — ready to slide up"
            elif 50 <= shoulder < 90:
                return f"Sliding up — {shoulder:.0f}°, keep arms touching wall lightly"
            elif 90 <= shoulder < 130:
                return f"Halfway — {shoulder:.0f}°, press lightly on wall going up"
            elif 130 <= shoulder <= 165:
                return "Excellent wall slide! Maximum range reached"
            return "Slide arms upward — wall contact throughout"

        elif exercise == 'shoulder_abduction':
            shoulder = joint_angles.get('left_shoulder', 0)
            if shoulder < 20:
                return "Raise arm out to the side slowly — palm down"
            elif 20 <= shoulder < 60:
                return f"Keep raising — {shoulder:.0f}° now, target 85-90°"
            elif 60 <= shoulder <= 95:
                return "Perfect! Arm parallel to ground — hold 2 sec"
            elif shoulder > 95:
                return "Just to shoulder level — lower slightly"
            return "Raise arm sideways to shoulder height"

        # ── Fallback ──────────────────────────────────────────────────────────
        return "Keep going with good form!"