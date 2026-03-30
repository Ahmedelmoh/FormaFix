import pyttsx3
import threading

class AudioFeedback:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)   # سرعة الكلام
        self.engine.setProperty('volume', 1.0)
        self.is_speaking = False
        self.last_feedback = ""

    def speak(self, text):
        # متكررش نفس الكلام
        if text == self.last_feedback or self.is_speaking:
            return

        self.last_feedback = text
        self.is_speaking = True

        def run():
            self.engine.say(text)
            self.engine.runAndWait()
            self.is_speaking = False

        # شغّل في thread منفصل عشان متوقفش الكاميرا
        threading.Thread(target=run, daemon=True).start()