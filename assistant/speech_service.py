import os
import queue
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from singleton_decorator import singleton

from assistant.tts_generator import get_tts_generator
from audio.strategy.audio_manager import get_audio_manager
from util.decorator import log_exceptions_from_self_logger, non_blocking
from util.loggin_mixin import LoggingMixin


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
        """
        super().__init__()
        self.voice = voice
        self.category = category
        self.cache_dir = cache_dir

        self.tts_generator = get_tts_generator()
        self.audio_manager = get_audio_manager()

        self.tts_generator.set_category_path(category, cache_dir)

        self.cache_cleaner = AudioCacheCleaner(cache_dir, cache_cleanup_interval)

        self.tts_generator.load_existing_cache(category)

        self._audio_lock = threading.Lock()

        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()

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

                sound_id = self.tts_generator.generate_tts(
                    text, self.category, self.voice
                )

                if sound_id:
                    self.cache_cleaner.protect_file(sound_id, 30)
                    self.audio_queue.put(sound_id)

                self.text_queue.task_done()

            except queue.Empty:
                pass

    @log_exceptions_from_self_logger("bei der Audio-Wiedergabe")
    def _process_audio_queue(self) -> None:
        """Worker-Thread, der vorbereitete Audiodateien abspielt"""
        while self.active:
            try:
                sound_id = self.audio_queue.get(timeout=0.5)

                self.logger.debug("Spiele Audio ab: %s", sound_id)

                self.cache_cleaner.protect_file(sound_id, 60)

                with self._audio_lock:
                    self.audio_manager.play(sound_id, block=True)

                self.audio_queue.task_done()

            except queue.Empty:
                pass
    
    @non_blocking
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
        
    def cleanup_cache(self, max_age_seconds: Optional[int] = None) -> int:
        """
        Manuelles Auslösen der Cache-Bereinigung
        
        Args:
            max_age_seconds: Maximales Alter der Dateien in Sekunden, die behalten werden sollen
            
        Returns:
            int: Anzahl der gelöschten Dateien
        """
        return self.cache_cleaner.cleanup_cache(max_age_seconds)
        
    def shutdown(self) -> None:
        """Fährt den SpeechService ordnungsgemäß herunter"""
        self.active = False
        
        # CacheCleaner herunterfahren
        if hasattr(self, 'cache_cleaner'):
            self.cache_cleaner.shutdown()
            
        # Warten auf das Beenden der Worker-Threads
        if hasattr(self, 'tts_worker') and self.tts_worker.is_alive():
            self.tts_worker.join(timeout=1.0)
            
        if hasattr(self, 'playback_worker') and self.playback_worker.is_alive():
            self.playback_worker.join(timeout=1.0)
            
        self.logger.info("SpeechService heruntergefahren")


class AudioCacheCleaner(LoggingMixin):
    """
    Verwaltet temporäre Audiodateien und führt automatische Bereinigungen durch.
    Kann auch als Context-Manager verwendet werden, um sicherzustellen, dass
    Ressourcen ordnungsgemäß freigegeben werden.
    
    Beispiel:
        # Als normale Instanz
        cleaner = AudioCacheCleaner(cache_dir="/tmp/audio")
        cleaner.cleanup_cache()
        
        # Als Context-Manager
        with AudioCacheCleaner(cache_dir="/tmp/audio") as cleaner:
            # Verwende cleaner
            cleaner.protect_file("audio.mp3")
        # Hier wird automatisch shutdown() aufgerufen
    """
    
    def __init__(
        self,
        cache_dir: str,
        default_cleanup_interval: int = 3600,
        file_extension: str = ".mp3"
    ):
        """
        Initialisiert den AudioCacheCleaner zur Verwaltung von temporären Audiodateien.
        """
        super().__init__()
        self.cache_dir = cache_dir
        self.default_cleanup_interval = default_cleanup_interval
        self.file_extension = file_extension
        
        # Stellt sicher, dass das Cache-Verzeichnis existiert
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Verwaltung aktiver Audiodateien und deren Schutzzeiten
        self._protected_files: Dict[str, datetime] = {}
        self._cleanup_lock = threading.Lock()
        
        # Cleanup-Thread starten
        self._cleanup_active = True
        self._cleanup_thread = threading.Thread(target=self._scheduled_cleanup, daemon=True)
        self._cleanup_thread.start()
        
        self.logger.info(
            f"AudioCacheCleaner initialisiert für Verzeichnis '{cache_dir}' "
            f"mit Standard-Intervall von {default_cleanup_interval} Sekunden"
        )

    def protect_file(self, filename: str, duration_seconds: int = 30) -> None:
        """
        Schützt eine Audiodatei vor dem Löschen für die angegebene Dauer.
        """
        # Nur Dateiname ohne Pfad verwenden
        basename = os.path.basename(filename)
        
        with self._cleanup_lock:
            current_time = datetime.now()
            expiry_time = current_time + timedelta(seconds=duration_seconds)
            
            if basename in self._protected_files:
                existing_expiry = self._protected_files[basename]
                if expiry_time > existing_expiry:
                    self._protected_files[basename] = expiry_time
                    self.logger.debug(f"Schutzzeit für {basename} verlängert bis {expiry_time}")
            else:
                self._protected_files[basename] = expiry_time
                self.logger.debug(f"Datei {basename} geschützt bis {expiry_time}")

    def is_protected(self, filename: str) -> bool:
        """
        Prüft, ob eine Datei aktuell geschützt ist.

        """
        basename = os.path.basename(filename)
        
        with self._cleanup_lock:
            # Prüfen, ob Datei in der Liste ist und Schutzzeit noch nicht abgelaufen
            if basename in self._protected_files:
                if self._protected_files[basename] > datetime.now():
                    return True
                else:
                    # Abgelaufenen Schutz entfernen
                    del self._protected_files[basename]
            
            return False

    @log_exceptions_from_self_logger("beim Cache-Cleanup")
    def cleanup_cache(self, max_age_seconds: Optional[int] = None) -> int:
        """
        Löscht alte Audiodateien aus dem Cache-Verzeichnis.
        
        Args:
            max_age_seconds: Maximales Alter der Dateien in Sekunden, die behalten werden sollen.
                             Wenn None, wird default_cleanup_interval verwendet.
                             
        Returns:
            int: Anzahl der gelöschten Dateien
        """
        if max_age_seconds is None:
            max_age_seconds = self.default_cleanup_interval
            
        deleted_count = 0
        current_time = time.time()
        
        try:
            with self._cleanup_lock:
                # Aktualisiere Liste geschützter Dateien
                self._update_protected_files()
                
                # Alle Dateien im Cache-Verzeichnis durchgehen
                for filename in os.listdir(self.cache_dir):
                    if not filename.endswith(self.file_extension):
                        continue
                        
                    file_path = os.path.join(self.cache_dir, filename)
                    
                    # Prüfen, ob Datei geschützt ist
                    if self.is_protected(filename):
                        self.logger.debug(f"Datei {filename} ist geschützt, wird übersprungen")
                        continue
                    
                    # Prüfen, ob Datei alt genug ist, um gelöscht zu werden
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                            self.logger.debug(f"Gelöschte Audiodatei: {filename} (Alter: {file_age:.1f}s)")
                        except (OSError, PermissionError) as e:
                            self.logger.warning(f"Konnte Datei {filename} nicht löschen: {e}")
            
            self.logger.info(f"{deleted_count} alte Audiodateien aus {self.cache_dir} gelöscht")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Fehler beim Cache-Cleanup: {e}")
            return 0

    def _update_protected_files(self) -> None:
        """Entfernt abgelaufene Einträge aus der Liste geschützter Dateien"""
        current_time = datetime.now()
        expired_files = [
            filename for filename, expiry_time in self._protected_files.items() 
            if expiry_time <= current_time
        ]
        
        for filename in expired_files:
            del self._protected_files[filename]
            
        if expired_files:
            self.logger.debug(f"Schutz für {len(expired_files)} Dateien abgelaufen")

    def _scheduled_cleanup(self) -> None:
        """Thread-Funktion für regelmäßiges Bereinigen des Cache-Verzeichnisses"""
        while self._cleanup_active:
            try:
                # Warte für das konfigurierte Intervall
                time.sleep(self.default_cleanup_interval)
                
                # Führe Cleanup durch
                self.cleanup_cache()
                
            except Exception as e:
                self.logger.error(f"Fehler im Cleanup-Thread: {e}")

    def shutdown(self) -> None:
        """
        Beendet den Cleanup-Thread ordnungsgemäß und löscht alle Dateien im Cache-Verzeichnis.
        """
        # Zuerst den Cleanup-Thread stoppen
        self._cleanup_active = False
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)
        
        # Alle Dateien im Cache-Verzeichnis löschen, unabhängig vom Schutzstatus
        try:
            deleted_count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(self.file_extension):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except (OSError, PermissionError) as e:
                        self.logger.warning(f"Konnte Datei {filename} beim Herunterfahren nicht löschen: {e}")
            
            # Setze die Liste der geschützten Dateien zurück
            with self._cleanup_lock:
                self._protected_files.clear()
                
            self.logger.info(f"AudioCacheCleaner heruntergefahren: {deleted_count} Audiodateien gelöscht")
        except Exception as e:
            self.logger.error(f"Fehler beim Aufräumen des Cache-Verzeichnisses beim Shutdown: {e}")

    def __enter__(self):
        """Context Manager Entry-Point"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit-Point"""
        self.shutdown()
        
    def __del__(self) -> None:
        """Destruktor zum sicheren Beenden des Threads"""
        try:
            self.shutdown()
        except Exception:
            pass  # Ignoriere Fehler beim Herunterfahren im Destruktor