import threading
import pygame
import os
from pydub import AudioSegment
from io import BytesIO
from typing import Dict, Optional, Union, List
from pathlib import Path
import time

class AudioManager:
    """Ein zentraler Manager für alle Audiofunktionen mit cleaner API."""
    
    _instance = None
    
    def __new__(cls):
        # Singleton-Pattern - nur eine Instanz zur Laufzeit
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Initialisierung nur einmal durchführen
        if self._initialized:
            return
            
        self._initialized = True
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Initialisiere Pygame Mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        
        # Audio-Ressourcen Cache
        self._sounds: Dict[str, AudioSegment] = {}
        self._channels: Dict[str, pygame.mixer.Channel] = {}
        self._audio_lock = threading.Lock()
        
        # Volume settings
        self._volume = 1.0
        
        # Vorkonfigurierte Channels
        self._setup_channels()
    
    def _setup_channels(self):
        """Konfiguriert verschiedene Mixer-Channels für paralleles Abspielen."""
        num_channels = 8  # Standardmäßig erzeugen wir 8 Channels
        pygame.mixer.set_num_channels(num_channels)
        
        # Vordefinierte Channel-Typen
        channel_types = ["sfx", "voice", "music", "notification", "system"]
        
        for i, channel_type in enumerate(channel_types):
            if i < num_channels:
                self._channels[channel_type] = pygame.mixer.Channel(i)
    
    def load_sound(self, sound_id: str, file_path: Union[str, Path], preload: bool = True) -> bool:
        """
        Lädt einen Sound in den Manager.
        
        Args:
            sound_id: Eindeutiger Identifier für den Sound
            file_path: Relativer oder absoluter Pfad zur Sounddatei
            preload: Ob der Sound direkt in den Speicher geladen werden soll
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            # Konvertiere zu absolutem Pfad wenn nötig
            if not os.path.isabs(file_path):
                full_path = os.path.join(self.base_path, file_path)
            else:
                full_path = file_path
                
            if not os.path.exists(full_path):
                print(f"❌ Datei nicht gefunden: {full_path}")
                return False
                
            if preload:
                # Sofort in den Speicher laden
                self._sounds[sound_id] = AudioSegment.from_file(full_path)
                print(f"🔊 Sound '{sound_id}' geladen: {os.path.basename(full_path)}")
            else:
                # Nur Pfad speichern, Laden bei Bedarf
                self._sounds[sound_id] = full_path
                
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Laden von '{sound_id}': {e}")
            return False
    
    def play(self, sound_id: str, channel_type: str = "sfx", 
             volume: Optional[float] = None, loop: int = 0) -> bool:
        """
        Spielt einen Sound ab.
        
        Args:
            sound_id: ID des zu spielenden Sounds
            channel_type: Art des Channels (sfx, voice, music, notification, system)
            volume: Lautstärke zwischen 0.0 und 1.0 (None für Standardlautstärke)
            loop: Anzahl der Wiederholungen (-1 für Endlosschleife)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if sound_id not in self._sounds:
            print(f"❌ Sound '{sound_id}' nicht gefunden")
            return False
            
        if channel_type not in self._channels:
            print(f"❌ Channel-Typ '{channel_type}' nicht verfügbar")
            return False
            
        # Thread für asynchrones Abspielen starten
        threading.Thread(
            target=self._play_sound_thread,
            args=(sound_id, channel_type, volume, loop),
            daemon=True
        ).start()
        
        return True
    
    def _play_sound_thread(self, sound_id: str, channel_type: str, 
                          volume: Optional[float], loop: int):
        """Interne Methode zum Abspielen eines Sounds in einem separaten Thread."""
        with self._audio_lock:
            try:
                # Sound laden falls noch nicht geladen
                sound = self._sounds[sound_id]
                if isinstance(sound, str):  # Lazy loading
                    sound = AudioSegment.from_file(sound)
                    self._sounds[sound_id] = sound
                
                # Audio in Bytes konvertieren
                audio_io = BytesIO()
                sound.export(audio_io, format="wav")
                audio_io.seek(0)
                
                # Sound als pygame Sound-Objekt laden
                pygame_sound = pygame.mixer.Sound(audio_io)
                
                # Lautstärke setzen
                vol = volume if volume is not None else self._volume
                pygame_sound.set_volume(vol)
                
                # Auf dem entsprechenden Channel abspielen
                channel = self._channels[channel_type]
                channel.play(pygame_sound, loops=loop)
                
                # Warten bis Abspielen beendet, wenn nicht im Loop-Modus
                if loop == 0:
                    while channel.get_busy():
                        time.sleep(0.1)
                        
            except Exception as e:
                print(f"❌ Fehler beim Abspielen von '{sound_id}': {e}")
            finally:
                # Ressourcen freigeben
                if 'audio_io' in locals():
                    audio_io.close()
    
    def stop(self, channel_type: Optional[str] = None):
        """
        Stoppt die Wiedergabe auf dem angegebenen Channel oder auf allen Channels.
        
        Args:
            channel_type: Channel-Typ zum Stoppen, None für alle Channels
        """
        if channel_type is None:
            # Alle Channels stoppen
            pygame.mixer.stop()
        elif channel_type in self._channels:
            # Nur den angegebenen Channel stoppen
            self._channels[channel_type].stop()
    
    def set_volume(self, volume: float, channel_type: Optional[str] = None):
        """
        Setzt die Lautstärke global oder für einen bestimmten Channel.
        
        Args:
            volume: Lautstärke zwischen 0.0 und 1.0
            channel_type: Spezifischer Channel oder None für globale Einstellung
        """
        volume = max(0.0, min(1.0, volume))  # Auf Bereich 0.0-1.0 begrenzen
        
        if channel_type is None:
            # Globale Lautstärke
            self._volume = volume
            pygame.mixer.music.set_volume(volume)
            # Auch auf alle Channels anwenden
            for channel in self._channels.values():
                channel.set_volume(volume)
        elif channel_type in self._channels:
            # Nur für den angegebenen Channel
            self._channels[channel_type].set_volume(volume)
    
    def is_playing(self, channel_type: Optional[str] = None) -> bool:
        """
        Prüft, ob aktuell ein Sound abgespielt wird.
        
        Args:
            channel_type: Spezifischer Channel oder None für alle Channels
            
        Returns:
            True wenn Sound abgespielt wird, False sonst
        """
        if channel_type is None:
            # Prüfe alle Channels
            return pygame.mixer.get_busy()
        elif channel_type in self._channels:
            # Nur den angegebenen Channel prüfen
            return self._channels[channel_type].get_busy()
        return False
    
    def cleanup(self):
        """Gibt alle Ressourcen frei."""
        pygame.mixer.quit()
        self._sounds.clear()
        self._channels.clear()


# Einfache Funktionen für schnelleren direkten Zugriff

def play_sound(sound_id: str, channel: str = "sfx", volume: Optional[float] = None):
    """Spielt einen Sound über den AudioManager ab."""
    return AudioManager().play(sound_id, channel, volume)

def load_sound(sound_id: str, file_path: str):
    """Lädt einen Sound in den AudioManager."""
    return AudioManager().load_sound(sound_id, file_path)

def stop_sound(channel: Optional[str] = None):
    """Stoppt alle oder bestimmte Sounds."""
    AudioManager().stop(channel)

def set_volume(volume: float, channel: Optional[str] = None):
    """Setzt die Lautstärke."""
    AudioManager().set_volume(volume, channel)


# Beispielverwendung:
if __name__ == "__main__":
    # Sounds laden
    load_sound("ding", "sounds/ding.mp3")
    load_sound("notification", "sounds/notification.wav")
    
    # Sounds abspielen
    play_sound("ding")
    
    # Notification mit anderer Lautstärke auf dem notification-Channel abspielen
    play_sound("notification", "notification", 0.7)
    
    # 2 Sekunden warten
    time.sleep(2)
    
    # Alle Sounds stoppen
    stop_sound()