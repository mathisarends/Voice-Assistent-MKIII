import os
import socket
import time
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

import pygame
import requests
import soco
from pydub import AudioSegment
from typing_extensions import override

from audio.strategy.sonos_http_server import start_http_server
from audio.strategy.sound_info import SoundInfo
from util.loggin_mixin import LoggingMixin


class AudioStrategyFactory:
    @staticmethod
    def create_pygame_strategy():
        return PygameAudioStrategy()

    @staticmethod
    def create_sonos_strategy(
        speaker_name=None, speaker_ip=None, http_server_port=8000
    ):
        return SonosAudioStrategy(speaker_name, speaker_ip, http_server_port)


class AudioPlaybackStrategy(ABC):
    """Abstract base class for audio playback strategies."""

    @abstractmethod
    def initialize(self):
        """Initialize the audio system."""
        pass

    @abstractmethod
    def play_sound(self, sound_path: str, volume: float) -> bool:
        """Play a sound file."""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        pass

    @abstractmethod
    def stop_playback(self):
        """Stop the current playback."""
        pass

    @abstractmethod
    def set_volume(self, volume: float):
        """Set the volume level."""
        pass

    @abstractmethod
    def fade_out(self, duration: float):
        """Perform a fade out effect."""
        pass


class SonosAudioStrategy(AudioPlaybackStrategy, LoggingMixin):
    """Implementiert Audio-Wiedergabe über Sonos-Lautsprecher."""

    def __init__(
        self,
        speaker_name: str = None,
        speaker_ip: str = None,
        http_server_port: int = 8000,
    ):
        self.speaker_name = speaker_name
        self.speaker_ip = speaker_ip
        self.http_server_port = http_server_port
        self.http_server_ip = None
        self.sonos_device = None
        self._initial_sonos_volume = None
        self._current_volume = 1.0
        self.http_server = None

    @override
    def initialize(self):
        self.http_server_ip = self._get_local_ip()

        self._start_http_server()

        self.logger.info("🔍 Suche nach Sonos-Lautsprechern im Netzwerk...")

        if self.speaker_ip:
            if self._connect_by_ip(self.speaker_ip):
                return

        if self.speaker_name:
            if self._connect_by_name(self.speaker_name):
                return

        try:
            devices = list(soco.discover())
            if not devices:
                self.logger.error("❌ Keine Sonos-Lautsprecher im Netzwerk gefunden")
                return

            device = devices[0]
            self.logger.info(
                "✅ Sonos-Lautsprecher automatisch gewählt: %s (%s)",
                device.player_name,
                device.ip_address,
            )
            self.sonos_device = device
            self._initial_sonos_volume = self.sonos_device.volume
        except Exception as e:
            self.logger.error("❌ Fehler bei der Suche nach Sonos-Lautsprechern: %s", e)

    def _connect_by_ip(self, ip):
        """Versucht eine Verbindung zu einem Sonos-Lautsprecher über IP herzustellen."""
        try:
            device = soco.SoCo(ip)
            device.player_name  # Dies schlägt fehl, wenn das Gerät nicht erreichbar ist
            self.logger.info(
                "✅ Sonos-Lautsprecher gefunden: %s (%s)", device.player_name, ip
            )
            self.sonos_device = device
            self._initial_sonos_volume = self.sonos_device.volume
            return True
        except Exception as e:
            self.logger.error(
                "❌ Konnte nicht mit Sonos-Lautsprecher unter %s verbinden: %s", ip, e
            )
            return False

    def _connect_by_name(self, name):
        """Versucht eine Verbindung zu einem Sonos-Lautsprecher über Namen herzustellen."""
        try:
            devices = list(soco.discover())
            for device in devices:
                if device.player_name.lower() == name.lower():
                    self.logger.info(
                        "✅ Sonos-Lautsprecher gefunden: %s (%s)",
                        device.player_name,
                        device.ip_address,
                    )
                    self.sonos_device = device
                    self._initial_sonos_volume = self.sonos_device.volume
                    return True

            self.logger.error(
                "❌ Kein Sonos-Lautsprecher mit Namen '%s' gefunden", name
            )
            return False
        except Exception as e:
            self.logger.error(
                "❌ Fehler bei der Suche nach Sonos-Lautsprecher '%s': %s", name, e
            )
            return False

    def _get_local_ip(self):
        """Ermittelt die lokale IP-Adresse des Geräts im Netzwerk."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            self.logger.error("❌ Fehler beim Ermitteln der IP-Adresse: %s", e)
            return "127.0.0.1"

    def _start_http_server(self):
        """Startet den HTTP-Server für Sonos."""
        try:
            # Starte den Server mit dem richtigen Projektverzeichnis
            project_dir = Path(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
            self.http_server = start_http_server(
                project_dir=project_dir, port=self.http_server_port
            )

            if not self.http_server or not self.http_server.is_running():
                self.logger.error("❌ HTTP-Server konnte nicht gestartet werden")
                return False

            self.logger.info(
                "✅ HTTP-Server für Sonos gestartet auf Port %d", self.http_server_port
            )
            return True

        except ImportError as e:
            self.logger.error("❌ Fehler beim Importieren des HTTP-Servers: %s", e)
            self.logger.warning("   Sonos-Funktionalität wird eingeschränkt sein!")
            return False
        except Exception as e:
            self.logger.error(
                "❌ Fehler beim Starten des HTTP-Servers für Sonos: %s", e
            )
            self.logger.warning("   Sonos-Funktionalität wird eingeschränkt sein!")
            return False

    @override
    def play_sound(self, sound_info: SoundInfo) -> bool:
        """Spielt einen Sound über Sonos-Lautsprecher ab."""
        if not self.sonos_device:
            self.logger.error("❌ Kein Sonos-Lautsprecher verfügbar")
            return False

        sound_url = self._get_sound_url(sound_info)
        if not sound_url:
            return False

        if not self._check_url_availability(sound_url):
            return False

        try:
            previous_volume = self.sonos_device.volume

            sonos_volume = int(min(100, max(0, self._current_volume * 100)))
            self.sonos_device.volume = sonos_volume

            self.sonos_device.play_uri(sound_url)

            while self.is_playing():
                time.sleep(0.1)

            self.sonos_device.volume = previous_volume

            return True

        except Exception as e:
            self.logger.error("❌ Fehler beim Abspielen der URL: %s", e)
            return False

    def _get_sound_url(self, sound_info: SoundInfo):
        """Ermittelt die URL für einen Sound."""
        if sound_info.url:
            return sound_info.url

        category = sound_info.category
        filename = sound_info.filename

        sound_url = f"http://{self.http_server_ip}:{self.http_server_port}/audio/sounds/{category}/{filename}"
        self.logger.info("🔊 Spiele Sound auf Sonos ab: %s", sound_url)

        return sound_url

    def _check_url_availability(self, url):
        """Prüft, ob eine URL verfügbar ist."""
        try:
            response = requests.head(url, timeout=2)
            if response.status_code == 200:
                return True

            self.logger.warning(
                "⚠️ Warnung: URL nicht erreichbar (Status %d): %s",
                response.status_code,
                url,
            )
            self.logger.warning(
                "   Stelle sicher, dass der HTTP-Server läuft und das Projektverzeichnis korrekt eingestellt ist."
            )
            return False
        except Exception as e:
            self.logger.warning("⚠️ Warnung: Konnte URL nicht überprüfen: %s", e)
            return True  # Im Zweifelsfall trotzdem versuchen

    @override
    def is_playing(self) -> bool:
        """Prüft, ob Sonos aktuell Audio abspielt."""
        if not self.sonos_device:
            return False

        try:
            return (
                self.sonos_device.get_current_transport_info()[
                    "current_transport_state"
                ]
                == "PLAYING"
            )
        except Exception as e:
            self.logger.error("❌ Fehler beim Prüfen des Sonos-Status: %s", e)
            return False

    @override
    def stop_playback(self):
        """Stoppt die Wiedergabe auf dem Sonos-Lautsprecher."""
        if not self.sonos_device:
            return

        try:
            self.sonos_device.stop()
        except Exception as e:
            self.logger.error("❌ Fehler beim Stoppen der Sonos-Wiedergabe: %s", e)

    @override
    def set_volume(self, volume: float):
        """Setzt die Lautstärke des Sonos-Lautsprechers (0.0 bis 1.0)."""
        if not self.sonos_device:
            return

        sonos_volume = int(min(100, max(0, volume * 100)))
        self.sonos_device.volume = sonos_volume
        self._current_volume = volume

    @override
    def fade_out(self, duration: float):
        """Führt einen Fade-Out-Effekt auf dem Sonos-Lautsprecher durch."""
        if not self.sonos_device or not self.is_playing():
            return

        self.logger.info("🔉 Führe Fade-Out über %.1f Sekunden durch...", duration)

        try:
            self._perform_fade_out(duration)
        except Exception as e:
            self.logger.error("❌ Fehler beim Fade-Out: %s", e)
            try:
                self.sonos_device.stop()
            except:
                pass

    def _perform_fade_out(self, duration):
        """Führt den eigentlichen Fade-Out durch."""
        start_volume = self.sonos_device.volume

        steps = int(duration * 4)
        if steps <= 0:
            self.sonos_device.stop()
            return

        volume_step = start_volume / steps
        time_step = duration / steps

        for step in range(steps):
            current_volume = start_volume - (volume_step * step)
            current_volume = max(0, int(current_volume))

            self.sonos_device.volume = current_volume
            time.sleep(time_step)

        self.sonos_device.stop()

        time.sleep(0.5)
        self.sonos_device.volume = start_volume

        self.logger.info("🔇 Fade-Out abgeschlossen")


class PygameAudioStrategy(AudioPlaybackStrategy, LoggingMixin):
    def __init__(self):
        self._current_volume = 1.0

    def initialize(self):
        """Initialisiert den Pygame-Mixer."""
        pygame.mixer.init()
        self.logger.info("✅ Pygame-Audiosystem initialisiert")

    def play_sound(self, sound_info: SoundInfo) -> bool:
        """Spielt einen Sound mit Pygame ab."""
        try:
            sound_path = sound_info.path

            sound = AudioSegment.from_file(sound_path)

            audio_io = BytesIO()
            sound.export(audio_io, format="wav")
            audio_io.seek(0)

            pygame_sound = pygame.mixer.Sound(audio_io)

            pygame_sound.set_volume(max(0.0, min(1.0, self._current_volume)))

            pygame_sound.play()

            while pygame.mixer.get_busy():
                pygame.time.wait(100)

            return True

        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abspielen des Sounds: {e}")
            return False
        finally:
            if "audio_io" in locals():
                audio_io.close()

    def is_playing(self) -> bool:
        return pygame.mixer.get_busy()

    def stop_playback(self):
        """Stoppt alle Pygame-Audio-Wiedergaben."""
        pygame.mixer.stop()

    def set_volume(self, volume: float):
        """Setzt die Lautstärke für alle aktiven Pygame-Kanäle."""
        self._current_volume = volume
        for i in range(pygame.mixer.get_num_channels()):
            channel = pygame.mixer.Channel(i)
            if channel.get_busy():
                channel.set_volume(volume)

    def fade_out(self, duration: float):
        """Führt einen Fade-Out-Effekt für alle Pygame-Kanäle durch."""
        import pygame

        if not self.is_playing():
            return

        self.logger.info(f"🔉 Führe Fade-Out über {duration} Sekunden durch...")

        start_volume = self._current_volume

        steps = int(duration * 20)

        volume_step = start_volume / steps if steps > 0 else 0

        time_step = duration / steps if steps > 0 else 0

        for step in range(steps):
            current_volume = start_volume - (volume_step * step)
            current_volume = max(0.0, current_volume)

            for i in range(pygame.mixer.get_num_channels()):
                channel = pygame.mixer.Channel(i)
                if channel.get_busy():
                    channel.set_volume(current_volume)

            time.sleep(time_step)

        pygame.mixer.stop()
        self.logger.info("🔇 Fade-Out abgeschlossen")
