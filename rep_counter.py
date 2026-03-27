class RepCounter:
    def __init__(self):
        self.counter = 0
        self.stage = None  # "up" or "down"
    
    def count(self, angle, up_threshold=160, down_threshold=90):
        """
        angle = زاوية الـ joint
        up_threshold = الزاوية لما الذراع مفرودة
        down_threshold = الزاوية لما الذراع متنية
        """
        # Stage: DOWN
        if angle < down_threshold:
            self.stage = "down"
        
        # Stage: UP (complete one rep)
        if angle > up_threshold and self.stage == "down":
            self.stage = "up"
            self.counter += 1
        
        return self.counter, self.stage
    
    def reset(self):
        self.counter = 0
        self.stage = None
        