class FeedbackEngine:

    def get_feedback(self, exercise, joint_angles):
        """
        feedback دقيق - بيقول الزاوية الصح + المسافة عنها + مرحلة التمرين
        """

        if exercise == 'bicep_curl':
            elbow = joint_angles.get('left_elbow', 0)
            target = 50
            diff = round(abs(elbow - target), 1)
            if elbow > 160:
                return f"Lower your elbow - target is {target} deg, you are {diff} deg away"
            elif elbow < 40:
                return "Don't over-curl - release slightly!"
            elif 50 <= elbow <= 80:
                return "Perfect curl position - hold it!"
            return f"Keep curling - {diff} degrees to target"

        elif exercise == 'squat':
            knee = joint_angles.get('left_knee', 0)
            target = 90
            diff = round(abs(knee - target), 1)
            if knee > 160:
                return f"Go deeper - target {target} deg, you are {diff} deg away"
            elif knee < 70:
                return "Too deep - come up slightly!"
            elif 85 <= knee <= 110:
                return "Perfect squat depth - great form!"
            return f"Almost there - {diff} degrees to target"

        elif exercise == 'straight_leg_raise':
            hip = joint_angles.get('left_hip', 0)
            target = 65
            diff = round(abs(hip - target), 1)
            if hip > 140:
                return f"Phase 1 - Lift your leg up, target is {target} deg"
            elif 100 < hip <= 140:
                return f"Phase 2 - Keep raising, {diff} degrees to target"
            elif 55 <= hip <= 80:
                return "Phase 3 - Perfect! Hold for 3 seconds"
            elif hip < 55:
                return f"Too high - lower {diff} degrees"
            return "Raise your leg steadily"

        elif exercise == 'terminal_knee_extension':
            knee = joint_angles.get('left_knee', 0)
            target = 165
            diff = round(abs(knee - target), 1)
            if knee < 30:
                return f"Phase 1 - Start from 45 degrees, you are at {knee} deg"
            elif 30 <= knee < 90:
                return f"Phase 2 - Straighten your knee, {diff} deg to go"
            elif 90 <= knee < 140:
                return f"Phase 3 - Halfway there! {diff} deg remaining"
            elif 140 <= knee < 155:
                return f"Almost there - push {diff} more degrees!"
            elif knee >= 155:
                return "Full extension - excellent form!"
            return f"Extend your knee - target {target} deg"

        elif exercise == 'mini_squat':
            knee = joint_angles.get('left_knee', 0)
            target = 125
            diff = round(abs(knee - target), 1)
            if knee > 155:
                return f"Phase 1 - Bend your knees, target is {target} deg"
            elif 130 <= knee <= 155:
                return f"Phase 2 - Go a bit deeper, {diff} deg to target"
            elif 110 <= knee < 130:
                return "Phase 3 - Perfect mini squat depth!"
            elif knee < 110:
                return f"Too deep - come up {diff} degrees"
            return "Maintain controlled movement"

        elif exercise == 'hamstring_curl':
            knee = joint_angles.get('left_knee', 0)
            target = 95
            diff = round(abs(knee - target), 1)
            if knee > 155:
                return f"Phase 1 - Curl your leg up, target {target} deg"
            elif 120 <= knee <= 155:
                return f"Phase 2 - Keep curling, {diff} deg to target"
            elif 80 <= knee < 120:
                return "Phase 3 - Great curl! Hold briefly"
            elif knee < 80:
                return f"Too far - release {diff} degrees"
            return "Curl your leg smoothly"

        elif exercise == 'pendulum':
            shoulder = joint_angles.get('left_shoulder', 0)
            target = 25
            diff = round(abs(shoulder - target), 1)
            if shoulder < 5:
                return "Phase 1 - Let your arm hang and swing gently"
            elif 5 <= shoulder <= 30:
                return f"Phase 2 - Good pendulum! {diff} deg to target"
            elif shoulder > 30:
                return f"Too much - reduce by {diff} degrees"
            return "Relax and swing"

        elif exercise == 'external_rotation':
            elbow = joint_angles.get('left_elbow', 0)
            shoulder = joint_angles.get('left_shoulder', 0)
            target_elbow = 90
            diff_elbow = round(abs(elbow - target_elbow), 1)
            if elbow < 75 or elbow > 105:
                return f"Fix elbow first - must be 90 deg, you are {diff_elbow} deg off"
            target = 70
            diff = round(abs(shoulder - target), 1)
            if shoulder < 50:
                return f"Phase 2 - Rotate outward more, {diff} deg to target"
            elif 55 <= shoulder <= 85:
                return "Perfect rotation range - hold it!"
            elif shoulder > 85:
                return f"Too much - reduce by {diff} degrees"
            return "Rotate slowly and controlled"

        elif exercise == 'wall_slide':
            shoulder = joint_angles.get('left_shoulder', 0)
            target = 155
            diff = round(abs(shoulder - target), 1)
            if shoulder < 50:
                return f"Phase 1 - Start with arms at shoulder height"
            elif 50 <= shoulder < 90:
                return f"Phase 2 - Slide up, {diff} deg to target"
            elif 90 <= shoulder < 130:
                return f"Phase 3 - Halfway! {diff} deg remaining"
            elif 130 <= shoulder <= 165:
                return "Phase 4 - Excellent! Full slide reached"
            elif shoulder > 165:
                return "Stay within pain-free range"
            return "Slide upward smoothly"

        elif exercise == 'shoulder_abduction':
            shoulder = joint_angles.get('left_shoulder', 0)
            target = 85
            diff = round(abs(shoulder - target), 1)
            if shoulder < 20:
                return f"Phase 1 - Raise arm to the side, target {target} deg"
            elif 20 <= shoulder < 60:
                return f"Phase 2 - Keep raising, {diff} deg to target"
            elif 60 <= shoulder <= 95:
                return "Phase 3 - Perfect! Arm parallel to ground"
            elif shoulder > 95:
                return f"Too high - lower by {diff} degrees"
            return "Raise your arm to the side"

        elif exercise == 'shoulder_raise':
            shoulder = joint_angles.get('left_shoulder', 0)
            target = 90
            diff = round(abs(shoulder - target), 1)
            if shoulder < 80:
                return f"Raise higher - {diff} deg to target {target}"
            elif shoulder > 100:
                return f"Lower slightly - {diff} deg above target"
            else:
                return "Perfect shoulder position!"

        return "Keep going!"