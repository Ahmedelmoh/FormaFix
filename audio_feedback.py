"""
audio_feedback.py — FormaFix
==============================
Non-blocking text-to-speech feedback using pyttsx3.
Avoids repeating the same phrase and runs in a daemon thread
so it never blocks the camera loop.
"""

import threading
import pyttsx3


class AudioFeedback:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 1.0)
        self._lock = threading.Lock()
        self._is_speaking = False
        self._last_text = ""

    def speak(self, text: str) -> None:
        """
        Speak *text* asynchronously.
        Silently skips if the same phrase was just spoken or TTS is still busy.
        """
        with self._lock:
            if text == self._last_text or self._is_speaking:
                return
            self._last_text = text
            self._is_speaking = True

        def _run():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            finally:
                with self._lock:
                    self._is_speaking = False

        threading.Thread(target=_run, daemon=True).start()
