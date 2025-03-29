import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from singleton_decorator import singleton

from audio.strategy.audio_strategies import AudioPlaybackStrategy
from audio.strategy.sound_info import SoundInfo
from util.loggin_mixin import LoggingMixin


@singleton
class AudioManager(LoggingMixin):
    """Haupt-Audio-Manager, der eine Strategie für die Wiedergabe verwendet."""

    def __init__(
        self, strategy: AudioPlaybackStrategy = None, root_dir: str = "sounds"
    ):
        self.project_dir = Path(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.audio_dir = self.project_dir / root_dir

        self.sound_map: Dict[str, SoundInfo] = {}

        self._lock = threading.Lock()

        self._stop_loop = False
        self._loop_thread = None

        self._current_volume = 0.65

        self.fade_out_duration = 2.5

        if strategy is None:
            from audio.strategy.audio_strategies import PygameAudioStrategy

            self.strategy = PygameAudioStrategy()
        else:
            self.strategy = strategy

        self.strategy.initialize()

        self.strategy.set_volume(self._current_volume)

        # Sounds entdecken
        self._discover_sounds()

    def _discover_sounds(self):
        """Durchsucht rekursiv das Audio-Verzeichnis nach MP3-Dateien."""
        self.logger.info(
            f"🔍 Durchsuche Verzeichnis nach MP3-Dateien: {self.audio_dir}"
        )

        if not self.audio_dir.exists():
            self.logger.info(f"❌ Verzeichnis nicht gefunden: {self.audio_dir}")
            return

        # Wir suchen jetzt nur noch nach MP3-Dateien
        sound_files = list(self.audio_dir.glob("**/*.mp3"))

        if not sound_files:
            self.logger.info(f"❌ Keine MP3-Dateien gefunden in: {self.audio_dir}")
            return

        for sound_file in sound_files:
            rel_path = sound_file.relative_to(self.audio_dir)

            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "default"

            filename = sound_file.name

            sound_id = sound_file.stem

            sound_info = SoundInfo(
                path=str(sound_file),
                category=category,
                filename=filename,
            )

            # URL für Sonos erzeugen falls nötig
            if hasattr(self.strategy, "http_server_ip") and hasattr(
                self.strategy, "http_server_port"
            ):
                sound_info.create_sonos_url(
                    self.audio_dir,
                    self.strategy.http_server_ip,
                    self.strategy.http_server_port,
                )

            self.sound_map[sound_id] = sound_info

        self.logger.info(f"✅ {len(self.sound_map)} MP3-Sounds gefunden und gemappt.")

    def register_sound(
        self, sound_id: str, file_path: str, category: str = "runtime"
    ) -> bool:
        """
        Registriert einen einzelnen MP3-Sound zur Laufzeit in der sound_map.
        """
        try:
            from pathlib import Path

            sound_path = Path(file_path)

            if not sound_path.exists():
                self.logger.info(f"❌ MP3-Datei nicht gefunden: {file_path}")
                return False

            if sound_path.suffix.lower() != ".mp3":
                self.logger.info(
                    f"❌ Nur MP3-Format wird unterstützt: {sound_path.suffix}"
                )
                return False

            sound_info = SoundInfo(
                path=str(sound_path),
                category=category,
                filename=sound_path.name,
            )

            if hasattr(self.strategy, "http_server_ip") and hasattr(
                self.strategy, "http_server_port"
            ):
                sound_info.create_sonos_url(
                    self.audio_dir,
                    self.strategy.http_server_ip,
                    self.strategy.http_server_port,
                )

            with self._lock:
                self.sound_map[sound_id] = sound_info

            self.logger.info(
                f"✅ MP3-Sound '{sound_id}' erfolgreich registriert: {file_path}"
            )
            return True

        except Exception as e:
            self.logger.info(
                f"❌ Fehler beim Registrieren von MP3-Sound '{sound_id}': {e}"
            )
            return False

    def set_strategy(self, strategy: AudioPlaybackStrategy):
        """Ändert die Wiedergabe-Strategie zur Laufzeit."""
        if self.is_playing():
            self.stop()

        self.strategy = strategy
        self.strategy.initialize()

        if hasattr(strategy, "http_server_ip") and hasattr(
            strategy, "http_server_port"
        ):
            for sound_info in self.sound_map.values():
                sound_info.create_sonos_url(
                    self.audio_dir, strategy.http_server_ip, strategy.http_server_port
                )

        self.logger.info(f"✅ Gewechselt zu {strategy.__class__.__name__}")

    def play(self, sound_id: str, block: bool = False) -> bool:
        """Spielt einen Sound ab."""
        if sound_id not in self.sound_map:
            self.logger.info(f"❌ Sound '{sound_id}' nicht gefunden")
            return False

        if block:
            return self._play_sound(sound_id)
        else:
            threading.Thread(
                target=self._play_sound, args=(sound_id,), daemon=True
            ).start()
            return True

    def is_playing(self) -> bool:
        """Prüft, ob aktuell ein Sound abgespielt wird."""
        return self.strategy.is_playing()

    def play_loop(self, sound_id: str, duration: float) -> bool:
        """Spielt einen Sound im Loop für die angegebene Dauer ab."""
        if sound_id not in self.sound_map:
            self.logger.info(f"❌ Sound '{sound_id}' nicht gefunden")
            return False

        # Stoppe eventuell laufenden Loop
        self.stop_loop()

        # Starte neuen Loop-Thread
        self._stop_loop = False
        self._loop_thread = threading.Thread(
            target=self._loop_sound, args=(sound_id, duration), daemon=True
        )
        self._loop_thread.start()
        return True

    def _loop_sound(self, sound_id: str, duration: float):
        """Interne Methode zum Loopen eines Sounds für eine bestimmte Dauer."""
        start_time = time.time()
        end_time = start_time + duration

        self.logger.info(f"🔄 Loop gestartet für '{sound_id}' ({duration} Sekunden)")

        try:
            while time.time() < end_time and not self._stop_loop:
                self._play_sound(sound_id)

                if self._stop_loop:
                    break

                if time.time() >= end_time:
                    break
        except Exception as e:
            self.logger.info(f"❌ Fehler beim Loopen von '{sound_id}': {e}")
        finally:
            self.logger.info(f"🔄 Loop beendet für '{sound_id}'")

    def stop_loop(self):
        """Stoppt den aktuellen Sound-Loop mit Fade-Out."""
        if self._loop_thread and self._loop_thread.is_alive():
            # Fade-Out ausführen, bevor wir den Loop stoppen
            self.fade_out()

            self._stop_loop = True

            self._loop_thread.join(timeout=1.0)
            self.logger.info("🔄 Loop gestoppt")

    def fade_out(self, duration: Optional[float] = None):
        """
        Führt einen Fade-Out für alle aktuell spielenden Sounds durch.
        """
        if not self.is_playing():
            return

        if duration is None:
            duration = self.fade_out_duration

        # Delegiere an Strategie
        self.strategy.fade_out(duration)

    def _play_sound(self, sound_id: str) -> bool:
        """Interne Methode zum Abspielen eines Sounds."""
        with self._lock:
            try:
                sound_info = self.sound_map[sound_id]
                return self.strategy.play_sound(sound_info)
            except Exception as e:
                self.logger.info(f"❌ Fehler beim Abspielen von '{sound_id}': {e}")
                return False

    def stop(self):
        """Stoppt alle Sounds mit Fade-Out."""
        self.fade_out()

    @property
    def volume(self) -> float:
        return self._current_volume

    @volume.setter
    def volume(self, value: float):
        """
        Setzt die Lautstärke zwischen 0.0 und 1.0.
        """
        if value > 1.0:
            value = value / 100.0

        value = max(0.0, min(1.0, value))

        self._current_volume = value

        self.strategy.set_volume(value)

        self.logger.info(f"🔊 Lautstärke auf {value:.2f} ({value*100:.0f}%) gesetzt")


def get_audio_manager() -> AudioManager:
    """Gibt die globale AudioManager-Instanz zurück."""
    return AudioManager()