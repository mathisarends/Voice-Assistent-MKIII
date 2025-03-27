import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from audio.strategy.audio_playback_strategy import AudioPlaybackStrategy
from audio.strategy.sound_info import SoundInfo
from singleton_decorator import singleton
from util.loggin_mixin import LoggingMixin

@singleton
class AudioManager(LoggingMixin):
    """Haupt-Audio-Manager, der eine Strategie für die Wiedergabe verwendet."""
    
    def __init__(self, strategy: AudioPlaybackStrategy = None, root_dir: str = "sounds"):
        self.project_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.audio_dir = self.project_dir / root_dir
        
        self.sound_map: Dict[str, SoundInfo] = {}
        
        self._lock = threading.Lock()
        
        self.supported_formats = [".mp3", ".wav"]
        
        self._stop_loop = False
        self._loop_thread = None
        
        self._current_volume = 1.0
        
        self.fade_out_duration = 2.5
        
        if strategy is None:
            # Lazy import, um zirkuläre Imports zu vermeiden
            from audio.strategy.pygame_audio_strategy import PygameAudioStrategy
            self.strategy = PygameAudioStrategy()
        else:
            self.strategy = strategy
            
        self.strategy.initialize()
        
        # Sounds entdecken
        self._discover_sounds()
    
    def _discover_sounds(self):
        """Durchsucht rekursiv das Audio-Verzeichnis nach Sounddateien."""
        self.logger.info(f"🔍 Durchsuche Verzeichnis: {self.audio_dir}")
        
        if not self.audio_dir.exists():
            self.logger.info(f"❌ Verzeichnis nicht gefunden: {self.audio_dir}")
            return
        
        # Liste für alle gefundenen Sounddateien
        sound_files = []
        
        # Alle unterstützten Formate suchen
        for format_ext in self.supported_formats:
            sound_files.extend(list(self.audio_dir.glob(f"**/*{format_ext}")))
        
        if not sound_files:
            self.logger.info(f"❌ Keine Sounddateien gefunden in: {self.audio_dir}")
            return
        
        for sound_file in sound_files:
            rel_path = sound_file.relative_to(self.audio_dir)
            
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "default"
            
            filename = sound_file.name
            
            sound_id = sound_file.stem
            
            # SoundInfo-Objekt erstellen
            sound_info = SoundInfo(
                path=str(sound_file),
                category=category,
                filename=filename,
                format=sound_file.suffix.lower()
            )
            
            # URL für Sonos erzeugen falls nötig
            if hasattr(self.strategy, 'http_server_ip') and hasattr(self.strategy, 'http_server_port'):
                sound_info.create_sonos_url(
                    self.audio_dir, 
                    self.strategy.http_server_ip, 
                    self.strategy.http_server_port
                )

            self.sound_map[sound_id] = sound_info
        
        self.logger.info(f"✅ {len(self.sound_map)} Sounds gefunden und gemappt.")
        
        # Zeige Statistik der gefundenen Formate
        format_stats = {}
        for info in self.sound_map.values():
            format_ext = info.format
            format_stats[format_ext] = format_stats.get(format_ext, 0) + 1
        
        for fmt, count in format_stats.items():
            self.logger.info(f"  - {fmt}: {count} Dateien")
    
    def set_strategy(self, strategy: AudioPlaybackStrategy):
        """Ändert die Wiedergabe-Strategie zur Laufzeit."""
        if self.is_playing():
            self.stop()
        
        self.strategy = strategy
        self.strategy.initialize()
        
        # URLs für Sonos aktualisieren, falls nötig
        if hasattr(strategy, 'http_server_ip') and hasattr(strategy, 'http_server_port'):
            for sound_info in self.sound_map.values():
                sound_info.create_sonos_url(
                    self.audio_dir,
                    strategy.http_server_ip,
                    strategy.http_server_port
                )
        
        self.logger.info(f"✅ Gewechselt zu {strategy.__class__.__name__}")
    
    def get_sounds_by_category(self, category: str) -> Dict[str, SoundInfo]:
        """Gibt alle Sounds einer bestimmten Kategorie zurück."""
        return {
            sound_id: info for sound_id, info in self.sound_map.items()
            if info.category == category
        }
    
    def play(self, sound_id: str, block: bool = False, volume: float = 1.0) -> bool:
        """Spielt einen Sound ab."""
        if sound_id not in self.sound_map:
            self.logger.info(f"❌ Sound '{sound_id}' nicht gefunden")
            return False
        
        # Aktuelle Lautstärke speichern
        self._current_volume = volume
        
        if block:
            # Im aktuellen Thread abspielen
            return self._play_sound(sound_id, volume)
        else:
            # In separatem Thread abspielen
            threading.Thread(
                target=self._play_sound,
                args=(sound_id, volume),
                daemon=True
            ).start()
            return True
    
    def is_playing(self) -> bool:
        """Prüft, ob aktuell ein Sound abgespielt wird."""
        return self.strategy.is_playing()
    
    def play_loop(self, sound_id: str, duration: float, volume: float = 1.0) -> bool:
        """Spielt einen Sound im Loop für die angegebene Dauer ab."""
        if sound_id not in self.sound_map:
            self.logger.info(f"❌ Sound '{sound_id}' nicht gefunden")
            return False
        
        # Aktuelle Lautstärke speichern
        self._current_volume = volume
        
        # Stoppe eventuell laufenden Loop
        self.stop_loop()
        
        # Starte neuen Loop-Thread
        self._stop_loop = False
        self._loop_thread = threading.Thread(
            target=self._loop_sound,
            args=(sound_id, duration, volume),
            daemon=True
        )
        self._loop_thread.start()
        return True
    
    def _loop_sound(self, sound_id: str, duration: float, volume: float):
        """Interne Methode zum Loopen eines Sounds für eine bestimmte Dauer."""
        start_time = time.time()
        end_time = start_time + duration
        
        self.logger.info(f"🔄 Loop gestartet für '{sound_id}' ({duration} Sekunden)")
        
        try:
            while time.time() < end_time and not self._stop_loop:
                self._play_sound(sound_id, volume)
                
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
            
            # Warte bis der Loop-Thread beendet ist (mit Timeout)
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
    
    def _play_sound(self, sound_id: str, volume: float) -> bool:
        """Interne Methode zum Abspielen eines Sounds."""
        with self._lock:
            try:
                sound_info = self.sound_map[sound_id]
                return self.strategy.play_sound(sound_info, volume)
            except Exception as e:
                self.logger.info(f"❌ Fehler beim Abspielen von '{sound_id}': {e}")
                return False
    
    def stop(self):
        """Stoppt alle Sounds mit Fade-Out."""
        self.fade_out()
    
    def set_volume(self, volume: float):
        """Setzt die Lautstärke für die Wiedergabe."""
        self._current_volume = volume
        self.strategy.set_volume(volume)


# Factory-Funktionen für einfachen Zugriff
def create_pygame_strategy():
    """Erstellt eine Pygame-Audio-Strategie."""
    from audio.strategy.pygame_audio_strategy import PygameAudioStrategy
    return PygameAudioStrategy()

def create_sonos_strategy(speaker_name: str = None, speaker_ip: str = None, http_server_port: int = 8000):
    """Erstellt eine Sonos-Audio-Strategie."""
    from audio.strategy.sonos_playback_strategy import SonosAudioStrategy
    return SonosAudioStrategy(speaker_name, speaker_ip, http_server_port)


# Globaler Zugriff und Hilfsfunktionen
def get_audio_manager() -> AudioManager:
    """Gibt die globale AudioManager-Instanz zurück."""
    return AudioManager()

def switch_to_pygame():
    """Wechselt zur Pygame-Wiedergabe-Strategie."""
    get_audio_manager().set_strategy(create_pygame_strategy())

def switch_to_sonos(speaker_name: str = None, speaker_ip: str = None, http_server_port: int = 8000):
    """Wechselt zur Sonos-Wiedergabe-Strategie."""
    get_audio_manager().set_strategy(create_sonos_strategy(speaker_name, speaker_ip, http_server_port))

def play(sound_id: str, block: bool = False, volume: float = 1.0) -> bool:
    """Spielt einen Sound ab."""
    return get_audio_manager().play(sound_id, block, volume)

def stop():
    """Stoppt alle Sounds mit Fade-Out."""
    get_audio_manager().stop()

def fade_out(duration: Optional[float] = None):
    """Führt einen Fade-Out für alle aktuell spielenden Sounds durch."""
    get_audio_manager().fade_out(duration)

def play_loop(sound_id: str, duration: float, volume: float = 1.0) -> bool:
    """Spielt einen Sound im Loop für die angegebene Dauer ab."""
    return get_audio_manager().play_loop(sound_id, duration, volume)

def stop_loop():
    """Stoppt den aktuellen Sound-Loop mit Fade-Out."""
    get_audio_manager().stop_loop()

def set_volume(volume: float):
    """Setzt die Lautstärke für die Wiedergabe."""
    get_audio_manager().set_volume(volume)

def get_sounds_by_category(category: str) -> Dict[str, SoundInfo]:
    """Gibt alle Sounds einer bestimmten Kategorie zurück."""
    return get_audio_manager().get_sounds_by_category(category)


# Beispielcode für die Verwendung:
if __name__ == "__main__":
    import time
    # 1. Normaler Gebrauch mit Standard-Strategie (Pygame)
    audio_manager = get_audio_manager()
    
    # Sound abspielen
    audio_manager.play("wakesound")
    
    switch_to_sonos(speaker_ip="192.168.178.68")
    
    play("wakesound")
    
    time.sleep(10)
    
    switch_to_pygame()