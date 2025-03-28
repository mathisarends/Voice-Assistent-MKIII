import os
from typing import List
from dotenv import load_dotenv
import pvporcupine
import pyaudio
import numpy as np
import threading
import time
import logging
from speech.wake_word_observer import get_wake_word_observers, WakeWordObserver

load_dotenv()


class WakeWordListener:
    def __init__(self, wakeword="picovoice", sensitivity=0.8):
        self.logger = logging.getLogger(self.__class__.__name__)

        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity muss zwischen 0.0 und 1.0 liegen")

        self.logger.info(
            "🔧 Initialisiere Wake-Word Listener mit Wort: %s (Sensitivity: %.1f)",
            wakeword,
            sensitivity,
        )

        access_key = os.getenv("PICO_ACCESS_KEY")
        if not access_key:
            raise ValueError("PICO_ACCESS_KEY nicht in .env Datei gefunden")

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("🔧 Initialisiere Wake-Word Listener mit Wort: %s", wakeword)

        self.wakeword = wakeword
        self.handle = pvporcupine.create(
            access_key=access_key, keywords=[wakeword], sensitivities=[0.8]
        )

        # Separate PyAudio-Instanz für Input
        self.pa_input = pyaudio.PyAudio()
        self.stream = self.pa_input.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=self.handle.frame_length,
            stream_callback=self._audio_callback,
        )

        # Flags für Status
        self.is_listening = False
        self.should_stop = False
        self._detection_event = threading.Event()

        self._observers: List[WakeWordObserver] = get_wake_word_observers()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback für Audio-Processing"""
        if self.is_listening and not self.should_stop:
            pcm = np.frombuffer(in_data, dtype=np.int16)
            keyword_index = self.handle.process(pcm)

            if keyword_index >= 0:
                self.logger.info("🚀 Wake-Word erkannt!")
                self._detection_event.set()
                self.notify_observers()

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
        """Ressourcen aufräumen."""
        self.logger.info("🧹 Räume Wake-Word-Listener auf...")
        self.should_stop = True
        self.is_listening = False

        # Warte kurz, damit laufende Operationen beendet werden können
        time.sleep(0.2)

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pa_input:
            self.pa_input.terminate()
        if self.handle:
            self.handle.delete()

        self.logger.info("✅ Wake-Word-Listener erfolgreich beendet")

    def add_observer(self, observer: WakeWordObserver):
        """Fügt einen neuen Observer hinzu."""
        if observer not in self._observers:
            self._observers.append(observer)
            self.logger.info(f"Observer {observer.__class__.__name__} hinzugefügt")

    def remove_observer(self, observer: WakeWordObserver):
        """Entfernt einen Observer."""
        if observer in self._observers:
            self._observers.remove(observer)
            self.logger.info(f"Observer {observer.__class__.__name__} entfernt")

    def notify_observers(self):
        """Benachrichtigt alle Observer über die Wakeword-Erkennung."""
        for observer in self._observers:
            # Jeder Observer wird in einem eigenen Thread benachrichtigt,
            # damit langsame Observer die anderen nicht blockieren
            threading.Thread(
                target=observer.on_wakeword_detected, args=(), daemon=True
            ).start()
