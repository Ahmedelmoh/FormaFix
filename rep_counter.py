import time

class RepCounter:
    def __init__(self, confirm_frames=24):
        self.counter = 0
        self.stage = None   # "up" or "down"
        self.confirm_frames = confirm_frames
        
        # كاونترات للتأكيد لمنع الـ Noise
        self._up_frames = 0
        self._down_frames = 0
        
        # الخطوة الرابعة: منع العد السريع (Dead-zone)
        self.last_rep_time = 0

    def count(self, angle, up_threshold=160, down_threshold=90):
        # 1. مراقبة حالة النزول (Down)
        if angle < down_threshold:
            self._down_frames += 1
            self._up_frames = 0
        else:
            self._down_frames = 0

        # 2. مراقبة حالة الصعود (Up)
        if angle > up_threshold:
            self._up_frames += 1
            self._down_frames = 0
        else:
            self._up_frames = 0

        # 3. تأكيد الوصول لنقطة النزول
        if self._down_frames >= self.confirm_frames:
            self.stage = "down"

        # 4. تأكيد العودة لنقطة البداية (عدّ Rep جديدة) مع شرط الزمن
        if self._up_frames >= self.confirm_frames and self.stage == "down":
            current_time = time.time()
            # التأكد من مرور ثانية واحدة على الأقل بين العدة والثانية
            if (current_time - self.last_rep_time) > 1.2: 
                self.counter += 1
                self.stage = "up"
                self.last_rep_time = current_time
                # تصويرياً: المريض رجع للوضع الأصلي بنجاح
            else:
                # لو حاول يخدع البرنامج ويتحرك بسرعة جداً، مش هنعدها
                pass 

        return self.counter, self.stage

    def reset(self):
        self.counter = 0
        self.stage = None
        self._up_frames = 0
        self._down_frames = 0
        self.last_rep_time = 0