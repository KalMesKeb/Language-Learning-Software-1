import pyttsx3
import threading

class TTSEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.rate = self.engine.getProperty("rate")
        self.voices = self.engine.getProperty("voices")
        self.voice_map = {v.id: v for v in self.voices}
        
        self.default_voice = self.voices[0].id if self.voices else None

    def list_voices(self):
        return [(v.id, v.name, v.languages) for v in self.voices]

    def set_rate(self, rate: int):
        self.engine.setProperty("rate", rate)
        self.rate = rate

    def set_voice(self, voice_id: str):
        self.engine.setProperty("voice", voice_id)

    def say_async(self, text: str, voice_id: str = None):
        def worker(t, vid):
            if vid:
                try:
                    self.engine.setProperty("voice", vid)
                except Exception:
                    pass
            self.engine.say(t)
            self.engine.runAndWait()
        thread = threading.Thread(target=worker, args=(text, voice_id))
        thread.daemon = True
        thread.start()
