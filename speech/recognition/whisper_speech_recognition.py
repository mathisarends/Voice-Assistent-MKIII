import os
import queue
import time
import wave

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class WhisperSpeechRecognition:
    def __init__(self, samplerate=16000):
        """Initialisiert die OpenAI Whisper API-Anbindung"""
        self.openai = OpenAI()
        self.set_open_ai_key()
        self.samplerate = samplerate
        self.audio_queue = queue.Queue()
        self.is_recording = False

    def audio_callback(self, indata, frames, time, status):
        """Fügt Audiodaten zum Queue hinzu"""
        if self.is_recording:
            self.audio_queue.put(indata.copy())

    def record_audio(
        self,
        filename="./temp/recorded_audio.mp3",
        silence_threshold=0.1,
        silence_duration=1.5,
    ):
        """Nimmt Sprache auf und speichert sie als WAV-Datei."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        self.is_recording = True
        buffer = []
        start_time = time.time()
        print("🎙 Aufnahme gestartet...")

        with sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype=np.int16,
            blocksize=int(self.samplerate * 0.1),  # 100ms Blocks
            callback=self.audio_callback,
        ):
            while True:
                if not self.audio_queue.empty():
                    current_audio = self.audio_queue.get()
                    buffer.append(current_audio)

                    # Nur die letzten 0.5 Sekunden analysieren
                    window_size = int(self.samplerate * 0.5)  # halbe Sekunde
                    recent_samples = (
                        np.concatenate(buffer[-5:])
                        if len(buffer) > 5
                        else np.concatenate(buffer)
                    )
                    if len(recent_samples) > window_size:
                        recent_samples = recent_samples[-window_size:]

                    volume = np.max(np.abs(recent_samples)) / 32767.0

                    if volume < silence_threshold:
                        if time.time() - start_time > silence_duration:
                            print("⏸ Stille erkannt, Aufnahme stoppt.")
                            break
                    else:
                        start_time = time.time()

        self.is_recording = False

        if len(buffer) < 20:
            return None

        audio_data = np.concatenate(buffer, axis=0)

        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_data.tobytes())

        return filename

    def set_open_ai_key(self):
        """Gibt den OpenAI API Key aus der Umgebungsvariable zurück."""
        load_dotenv()

        self.open_ai_key = os.getenv("OPENAI_API_KEY")
        if not self.open_ai_key:
            raise ValueError("❌ Kein OpenAI API Key gefunden!")
