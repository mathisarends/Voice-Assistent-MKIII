import os
import queue
import time
import wave
from pathlib import Path
from typing import List, Optional

import aiofiles
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

from util.decorator import measure_performance
from util.loggin_mixin import LoggingMixin

load_dotenv()

class SpeechRecorder(LoggingMixin):
    def __init__(self, samplerate=44100):
        """Initialisiert die OpenAI Whisper API-Anbindung mit verbesserter Audioqualität"""
        self.openai = OpenAI()
        self.set_open_ai_key()
        self.samplerate = samplerate
        self.audio_queue = queue.Queue()
        self.is_recording = False
        
        self.base_path = Path(__file__).parent.parent / "audio" / "sounds" / "temp"

    def audio_callback(self, indata, frames, time, status):
        """Fügt Audiodaten zum Queue hinzu und überwacht Status"""
        if status:
            self.logger.warning(f"⚠️ Audio-Status: {status}")
        
        if not self.is_recording:
            return
            
        peak = np.max(np.abs(indata))
        if peak >= 32700:
            self.logger.warning("🔊 Warnung: Audio übersteuert!")
            
        self.audio_queue.put(indata.copy())

    def record_audio(
        self,
        filename=None,
        silence_threshold=0.1,
        silence_duration=1.5,
        gain=2.0,
    ):
        if filename is None:
            filename = str(self.base_path / "recorded_audio.wav")
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        self.is_recording = True
        buffer = []
        start_time = time.time()
        self.logger.info("🎙 Aufnahme gestartet...")

        try:
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=1,
                dtype=np.int16,
                blocksize=int(self.samplerate * 0.1),
                callback=self.audio_callback,
            ):
                while True:
                    if self.audio_queue.empty():
                        time.sleep(0.01)
                        continue
                        
                    current_audio = self.audio_queue.get()
                    buffer.append(current_audio)

                    window_size = int(self.samplerate * 0.5)
                    recent_samples = (
                        np.concatenate(buffer[-5:])
                        if len(buffer) > 5
                        else np.concatenate(buffer)
                    )
                    if len(recent_samples) > window_size:
                        recent_samples = recent_samples[-window_size:]

                    volume = np.max(np.abs(recent_samples)) / 32767.0

                    if volume >= silence_threshold:
                        start_time = time.time()
                        continue
                        
                    if time.time() - start_time <= silence_duration:
                        continue
                        
                    self.logger.info("⏸ Stille erkannt, Aufnahme stoppt.")
                    break
        finally:
            self.is_recording = False

        if len(buffer) < 20:
            self.logger.info("❌ Aufnahme zu kurz oder kein Audio erkannt.")
            return None

        audio_data = np.concatenate(buffer, axis=0)
        
        audio_data = audio_data * gain
        audio_data = np.clip(audio_data, -32767, 32767).astype(np.int16)

        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.samplerate)
                wf.writeframes(audio_data.tobytes())
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Speichern der Audiodatei: {e}")
            return None
        
        self.logger.info(f"✅ Aufnahme gespeichert unter: {filename}")
        return filename

    def set_open_ai_key(self):
        """Gibt den OpenAI API Key aus der Umgebungsvariable zurück."""
        load_dotenv()

        self.open_ai_key = os.getenv("OPENAI_API_KEY")
        if not self.open_ai_key:
            raise ValueError("❌ Kein OpenAI API Key gefunden!")
    
    
        
class AudioTranscriber(LoggingMixin):
    def __init__(self):
        super().__init__()
        self.openai = AsyncOpenAI()

    @measure_performance
    async def transcribe_audio(
        self, filename, language="de", vocabulary: List[str] = ["Wetter", "Licht", "Spotify", "Notion"]
    ) -> Optional[str]:
        """
        Sendet die Audiodatei an OpenAI Whisper API und gibt den erkannten Text zurück
        """
        self.logger.info("📝 Sende Audiodatei an OpenAI...")

        try:
            file_basename = os.path.basename(filename)

            prompt = ""
            if language == "de":
                prompt = "Dies ist eine Aufnahme auf Deutsch. "
                
            vocab_str = ", ".join(vocabulary)
            prompt += f"Folgende Wörter können vorkommen: {vocab_str}"

            async with aiofiles.open(filename, "rb") as audio_file:
                audio_data = await audio_file.read()
                
            transcription = await self.openai.audio.transcriptions.create(
                model="whisper-1",
                file=(file_basename, audio_data),
                response_format="text",
                prompt=prompt if prompt else None,
            )

            return transcription

        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Transkription: {str(e)}")
            return None