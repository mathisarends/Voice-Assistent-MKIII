import queue
import os
import time
import sounddevice as sd
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import io
from pydub import AudioSegment

load_dotenv()

class SpeechRecorder:
    def __init__(self, samplerate=16000):
        self.openai = OpenAI()
        self.samplerate = samplerate
        self.audio_queue = queue.Queue()
        self.is_recording = False

    def audio_callback(self, indata, frames, time, status):
        if self.is_recording:
            self.audio_queue.put(indata.copy())
            
    def optimize_audio(self, audio_data, reduce_quality=False):
        max_volume = np.max(np.abs(audio_data))
        if max_volume > 0:
            audio_data = (audio_data / max_volume * 0.9 * 32767).astype(np.int16)
        
        if reduce_quality:
            audio_data = audio_data[::2]
            audio_data = (audio_data / 256).astype(np.int8)
        
        return audio_data

    def record_audio(self, silence_threshold=0.1, silence_duration=1.5):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        temp_wav = os.path.join(script_dir, "temp", "temp_audio.wav")
        final_mp3 = os.path.join(script_dir, "temp", "recorded_audio.mp3")
        os.makedirs(os.path.dirname(temp_wav), exist_ok=True)
        
        self.is_recording = True
        buffer = []
        start_time = time.time()
        print("🎙 Aufnahme gestartet...")

        with sd.InputStream(samplerate=self.samplerate, channels=1,
                            dtype=np.int16,
                            blocksize=int(self.samplerate * 0.1),
                            callback=self.audio_callback):
            while True:
                if not self.audio_queue.empty():
                    current_audio = self.audio_queue.get()
                    buffer.append(current_audio)
                    
                    window_size = int(self.samplerate * 0.5)
                    recent_samples = np.concatenate(buffer[-5:]) if len(buffer) > 5 else np.concatenate(buffer)
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
        audio_data = self.optimize_audio(audio_data)
        
        # Zuerst als WAV speichern (temporär)
        with io.BytesIO() as wav_io:
            import wave
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.samplerate)
                wf.writeframes(audio_data.tobytes())
            
            wav_io.seek(0)
            
            # Konvertiere zu MP3 mit pydub
            audio = AudioSegment.from_wav(wav_io)
            audio.export(final_mp3, format="mp3", bitrate="32k")  # Niedrige Bitrate für kleinere Dateien
        
        print(f"📊 Dateigröße MP3: {os.path.getsize(final_mp3) / 1024:.2f} KB")
        return final_mp3