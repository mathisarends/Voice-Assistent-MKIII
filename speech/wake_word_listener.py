import os
from dotenv import load_dotenv
import pvporcupine
import pyaudio
import numpy as np
import threading
import time
import logging
from audio.audio_manager import play

load_dotenv()

class WakeWordListener:
    def __init__(self, wakeword="picovoice", sensitivity=0.8):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity muss zwischen 0.0 und 1.0 liegen")
            
        self.logger.info("🔧 Initialisiere Wake-Word Listener mit Wort: %s (Sensitivity: %.1f)", 
                        wakeword, sensitivity)
        
        access_key = os.getenv("PICO_ACCESS_KEY")
        if not access_key:
            raise ValueError("PICO_ACCESS_KEY nicht in .env Datei gefunden")
        
        self.wakeword = wakeword
        self.sensitivity = sensitivity
        self.handle = None
        self.pa_input = None
        self.stream = None
        self.is_listening = False
        self.should_stop = False
        self._detection_event = threading.Event()
        
        try:
            self.handle = pvporcupine.create(
                access_key=access_key,
                keywords=[wakeword],
                sensitivities=[sensitivity]
            )
            
            self.pa_input = pyaudio.PyAudio()
            self.stream = self.pa_input.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.handle.sample_rate,
                input=True,
                frames_per_buffer=self.handle.frame_length,
                stream_callback=self._audio_callback
            )
            self.logger.debug("Wake-Word-Listener erfolgreich initialisiert")
        except Exception as e:
            self.cleanup()
            self.logger.error("Fehler bei Initialisierung: %s", e)
            raise

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        try:
            if status:
                self.logger.warning("Audio-Callback-Status: %s", status)
                
            if not self.is_listening or self.should_stop:
                return (in_data, pyaudio.paContinue)
                
            pcm = np.frombuffer(in_data, dtype=np.int16)
            keyword_index = self.handle.process(pcm)
            
            if keyword_index >= 0:
                play("wakesound")
                self.logger.info("🚀 Wake-Word erkannt!")
                self._detection_event.set()
        except Exception as e:
            self.logger.error("Fehler im Audio-Callback: %s", e)
            
        return (in_data, pyaudio.paContinue)

    def listen_for_wakeword(self):
        self.logger.info("🎤 Warte auf Wake-Word...")
        self._detection_event.clear()
        self.is_listening = True
        
        if not self.stream.is_active():
            self.stream.start_stream()
        
        # Warten auf Erkennung
        while not self.should_stop:
            if self._detection_event.wait(timeout=0.1):
                self._detection_event.clear()
                self.logger.info("✅ Wake-Word erkannt und Event signalisiert")
                return True
                
        return False

    def cleanup(self):
        self.logger.info("🧹 Räume Wake-Word-Listener auf...")
        self.should_stop = True
        self.is_listening = False
        
        time.sleep(0.1)
        
        # Stream sicher schließen
        if not hasattr(self, 'stream') or not self.stream:
            return
            
        try:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
        except Exception as e:
            self.logger.error("Fehler beim Schließen des Streams: %s", e)
            
        # PyAudio sicher beenden
        if hasattr(self, 'pa_input') and self.pa_input:
            try:
                self.pa_input.terminate()
            except Exception as e:
                self.logger.error("Fehler beim Beenden von PyAudio: %s", e)
                
        # Porcupine-Handle sicher löschen
        if hasattr(self, 'handle') and self.handle:
            try:
                self.handle.delete()
            except Exception as e:
                self.logger.error("Fehler beim Löschen des Porcupine-Handles: %s", e)
        
        self.logger.info("✅ Wake-Word-Listener erfolgreich beendet")
    
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        with WakeWordListener(wakeword="computer", sensitivity=0.7) as listener:
            print("Sage 'Computer' um die Erkennung zu testen...")
            print("Drücke Strg+C zum Beenden")
            
            if listener.listen_for_wakeword():
                print("👂 Wake-Word erkannt! Führe Aktion aus...")
                
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet.")
    except Exception as e:
        print(f"Fehler: {e}")