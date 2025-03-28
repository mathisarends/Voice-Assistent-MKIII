import os
import threading
import queue
import time
from typing import Optional

from assistant.tts_generator import get_tts_generator
from audio.strategy.audio_manager import get_audio_manager
from util.loggin_mixin import LoggingMixin
from singleton_decorator import singleton
from util.decorator import log_exceptions_from_self_logger


@singleton
class SpeechService(LoggingMixin):
    def __init__(
        self,
        voice: str = "nova",
        category: str = "tts_responses",
        cache_dir: str = "audio/sounds/temp_responses",
        cache_cleanup_interval: int = 3600,
    ):
        """
        Initialisiert den SpeechService mit TTSGenerator und AudioManager.

        Args:
            voice: Die zu verwendende TTS-Stimme
            category: Die Kategorie für die Sounds im AudioManager
            cache_dir: Verzeichnis für TTS-Audiodateien
            cache_cleanup_interval: Intervall in Sekunden für das Löschen alter Cache-Dateien
        """
        super().__init__()
        self.voice = voice
        self.category = category
        self.cache_dir = cache_dir

        # TTSGenerator und AudioManager als Singleton verwenden
        self.tts_generator = get_tts_generator()
        self.audio_manager = get_audio_manager()

        # Benutzerdefinierten Pfad für diese Kategorie setzen
        self.tts_generator.set_category_path(category, cache_dir)

        # Cache-Cleanup konfigurieren
        self.tts_generator.cache_cleanup_interval = cache_cleanup_interval

        # Existierende TTS-Dateien laden
        self.tts_generator.load_existing_cache(category)

        self._audio_lock = threading.Lock()

        # Queue-Mechanismen für die asynchrone Verarbeitung
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()

        # Worker-Threads für die TTS-Verarbeitung und Audiowiedergabe
        self.active = True
        self.tts_worker = threading.Thread(target=self._process_tts_queue, daemon=True)
        self.tts_worker.start()

        self.playback_worker = threading.Thread(
            target=self._process_audio_queue, daemon=True
        )
        self.playback_worker.start()

        self.logger.info(
            f"SpeechService initialisiert mit Stimme '{voice}', "
            f"Kategorie '{category}' und Cache-Verzeichnis '{cache_dir}'"
        )

    @log_exceptions_from_self_logger("bei der TTS-Verarbeitung")
    def _process_tts_queue(self) -> None:
        """Worker-Thread, der Texte in Audio umwandelt und zur Wiedergabe vorbereitet"""
        while self.active:
            try:
                text = self.text_queue.get(timeout=0.5)

                if not text.strip():
                    self.text_queue.task_done()
                    continue

                self.logger.debug(
                    "Generiere Sprache für: %s",
                    text[:50] + ("..." if len(text) > 50 else ""),
                )

                # TTSGenerator verwenden
                sound_id = self.tts_generator.generate_tts(
                    text, self.category, self.voice
                )

                if sound_id:
                    self.audio_queue.put(sound_id)

                self.text_queue.task_done()

            except queue.Empty:
                pass

    @log_exceptions_from_self_logger("bei der Audio-Wiedergabe")
    def _process_audio_queue(self) -> None:
        """Worker-Thread, der vorbereitete Audiodateien abspielt"""
        while self.active:
            try:
                # Hole die nächste Sound-ID aus der Queue
                sound_id = self.audio_queue.get(timeout=0.5)

                self.logger.debug("Spiele Audio ab: %s", sound_id)

                # Spiele die Audio-Datei über den AudioManager ab
                with self._audio_lock:
                    self.audio_manager.play(sound_id, block=True)

                # Markiere Aufgabe als erledigt
                self.audio_queue.task_done()

            except queue.Empty:
                # Queue Timeout, setze Schleife fort
                pass

    @log_exceptions_from_self_logger("beim Unterbrechen der Audioausgabe")
    def interrupt_and_reset(self) -> bool:
        """
        Unterbricht die aktuelle Sprachausgabe und leert die Queues.

        Returns:
            bool: True, wenn erfolgreich zurückgesetzt
        """
        self.logger.debug("Unterbreche aktuelle Audioausgabe...")

        # Leere Queues sicher
        self._clear_queues()

        # Versuche Lock zu erwerben mit Timeout
        if self._audio_lock.acquire(timeout=1.0):
            try:
                # Stoppe alle laufenden Sounds über den AudioManager
                self.audio_manager.stop()

                self.logger.info("System bereit für neue Eingabe")
                return True
            finally:
                self._audio_lock.release()
        else:
            # Notfall-Reset bei Lock-Timeout
            self.logger.warning(
                "Konnte Audio-Lock nicht erwerben, versuche alternative Stopstrategie"
            )
            self.audio_manager.stop()  # Stopp-Versuch ohne Lock
            return True

    @log_exceptions_from_self_logger("beim Leeren der Queues")
    def _clear_queues(self) -> None:
        """Leert alle Aufgaben-Queues sicher"""
        with self.text_queue.mutex:
            self.text_queue.queue.clear()
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

    def enqueue_text(self, response_text: str, is_interrupting=True) -> str:
        """
        Fügt Text zur Sprachausgabe hinzu.

        Args:
            response_text: Der auszugebende Text
            is_interrupting: Wenn True, wird die aktuelle Wiedergabe unterbrochen

        Returns:
            str: Der zur Ausgabe hinzugefügte Text
        """
        self.logger.info("🤖 Assistenten-Antwort: %s", response_text)

        if not response_text or response_text.strip() == "":
            self.logger.warning("Leere Antwort erhalten, keine Sprachausgabe")
            return ""

        if is_interrupting:
            self.interrupt_and_reset()

        self.text_queue.put(response_text)
        self.logger.info(
            "Text zur Sprachausgabe hinzugefügt: %s",
            response_text[:50] + ("..." if len(response_text) > 50 else ""),
        )

        return response_text
