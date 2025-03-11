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

    def record_audio(self, base_silence_threshold=0.05, silence_duration=1.0, zcr_threshold=0.1):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        final_mp3 = os.path.join(script_dir, "temp", "recorded_audio.mp3")
        os.makedirs(os.path.dirname(final_mp3), exist_ok=True)
        
        self.is_recording = True
        buffer = []
        silence_start_time = None
        
        # Für adaptive Schwellenwerte
        background_energy = []
        window_size = int(self.samplerate * 0.2)  # 200ms Fenster
        print("🎙 Aufnahme gestartet...")
        
        with sd.InputStream(samplerate=self.samplerate, channels=1,
                            dtype=np.int16,
                            blocksize=int(self.samplerate * 0.05),  
                            callback=self.audio_callback):
            calibration_time = time.time() + 0.5
            while time.time() < calibration_time:
                if not self.audio_queue.empty():
                    current_audio = self.audio_queue.get()
                    background_energy.append(np.mean(np.abs(current_audio)))
                    time.sleep(0.01)
            
            if background_energy:
                adaptive_threshold = max(base_silence_threshold, 
                                        np.mean(background_energy) * 1.5 / 32767.0)
            else:
                adaptive_threshold = base_silence_threshold
                
            print(f"Adaptiver Schwellenwert: {adaptive_threshold:.4f}")
            
            while True:
                if not self.audio_queue.empty():
                    current_audio = self.audio_queue.get()
                    buffer.append(current_audio)
                    
                    recent_samples = np.concatenate(buffer[-4:]) if len(buffer) >= 4 else np.concatenate(buffer)
                    if len(recent_samples) > window_size:
                        recent_samples = recent_samples[-window_size:]
                    
                    energy = np.mean(np.abs(recent_samples)) / 32767.0
                    
                    zero_crossings = np.sum(np.diff(np.signbit(recent_samples).astype(int)))
                    zcr = zero_crossings / len(recent_samples)
                    
                    is_silence = energy < adaptive_threshold and zcr < zcr_threshold
                    
                    if is_silence:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time > silence_duration:
                            print("⏸ Stille erkannt, Aufnahme stoppt.")
                            break
                    else:
                        silence_start_time = None
        
        self.is_recording = False
        
        if len(buffer) < 10:  # Mindestlänge (500ms)
            return None
        
        audio_data = np.concatenate(buffer, axis=0)
        audio_data = self.optimize_audio(audio_data)
        
        # Direkt zu MP3 konvertieren ohne temporäre WAV-Datei
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
            audio.export(final_mp3, format="mp3", bitrate="32k")

        print(f"📊 Dateigröße MP3: {os.path.getsize(final_mp3) / 1024:.2f} KB")
        return final_mp3