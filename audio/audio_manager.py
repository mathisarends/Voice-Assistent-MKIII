import os
import threading
import pygame
from io import BytesIO
from pydub import AudioSegment
from typing import Dict

class SimpleAudio:
    """Eine schlanke, einfach zu nutzende Audio-Klasse."""
    
    # Singleton-Instanz
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimpleAudio, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Mixer initialisieren
        pygame.mixer.init()
        
        # Sound-Cache
        self._sounds: Dict[str, str] = {}
        self._lock = threading.Lock()
    
    def register(self, sound_id: str, file_path: str) -> bool:
        """
        Registriert einen Sound ohne ihn zu laden.
        
        Args:
            sound_id: Name/ID des Sounds
            file_path: Pfad zur Sound-Datei
            
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
                print(f"Datei nicht gefunden: {full_path}")
                return False
                
            # Nur Pfad speichern
            self._sounds[sound_id] = full_path
            return True
            
        except Exception as e:
            print(f"Fehler beim Registrieren von '{sound_id}': {e}")
            return False
    
    def play(self, sound_id: str, block: bool = False, volume: float = 1.0) -> bool:
        """
        Spielt einen Sound ab.
        
        Args:
            sound_id: ID des zu spielenden Sounds
            block: Wenn True, blockiert die Methode bis der Sound fertig ist
            volume: Lautstärke zwischen 0.0 und 1.0
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if sound_id not in self._sounds:
            print(f"Sound '{sound_id}' nicht registriert")
            return False
            
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
    
    def _play_sound(self, sound_id: str, volume: float) -> bool:
        """Interne Methode zum Abspielen eines Sounds."""
        with self._lock:
            try:
                # Sound laden
                sound_path = self._sounds[sound_id]
                sound = AudioSegment.from_file(sound_path)
                
                # Audio in Bytes konvertieren
                audio_io = BytesIO()
                sound.export(audio_io, format="wav")
                audio_io.seek(0)
                
                # Sound als pygame Sound-Objekt laden
                pygame_sound = pygame.mixer.Sound(audio_io)
                
                # Lautstärke setzen
                pygame_sound.set_volume(max(0.0, min(1.0, volume)))
                
                # Abspielen
                pygame_sound.play()
                
                # Warten bis Abspielen beendet
                while pygame.mixer.get_busy():
                    pygame.time.wait(100)
                    
                return True
                
            except Exception as e:
                print(f"Fehler beim Abspielen von '{sound_id}': {e}")
                return False
            finally:
                # Ressourcen freigeben
                if 'audio_io' in locals():
                    audio_io.close()
    
    def stop(self):
        """Stoppt alle Sounds."""
        pygame.mixer.stop()


_audio = SimpleAudio()

def register(sound_id: str, file_path: str) -> bool:
    """Registriert einen Sound für spätere Verwendung."""
    # Normalisiere Pfad (konvertiert / und \ konsistent)
    normalized_path = os.path.normpath(file_path)
    return _audio.register(sound_id, normalized_path)

def play(sound_id: str, block: bool = False, volume: float = 1.0) -> bool:
    """Spielt einen registrierten Sound ab."""
    return _audio.play(sound_id, block, volume)

def stop():
    """Stoppt alle laufenden Sounds."""
    _audio.stop()


# Beispielverwendung
if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    audio_path = os.path.join(project_dir, "audio", "get_up_sounds", "get-up-aurora.mp3")
    register("aurora", audio_path)
    
    # Nicht-blockierend abspielen
    play("aurora")
    print("Diese Nachricht erscheint sofort!")
    
    import time
    import time.sleep(10)