import os
from pathlib import Path
from typing import Dict, List
import pygame
import threading
from io import BytesIO
from pydub import AudioSegment

class AudioManager:
    """Erstellt automatisch ein Mapping aller Audiodateien im System."""
    def __init__(self, root_dir: str = "audio/sounds"):
        # Basisverzeichnis setzen
        self.project_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.audio_dir = self.project_dir / root_dir
        
        self.sound_map: Dict[str, Dict] = {}
        
        pygame.mixer.init()
        
        # Thread-Lock für Audiowiedergabe
        self._lock = threading.Lock()
        
        self._discover_sounds()
    
    def _discover_sounds(self):
        """Durchsucht rekursiv das Audio-Verzeichnis nach Sounddateien."""
        print(f"🔍 Durchsuche Verzeichnis: {self.audio_dir}")
        
        if not self.audio_dir.exists():
            print(f"❌ Verzeichnis nicht gefunden: {self.audio_dir}")
            return
        
        # Rekursiv alle MP3-Dateien finden
        sound_files = list(self.audio_dir.glob("**/*.mp3"))
        
        if not sound_files:
            print(f"❌ Keine Sounddateien gefunden in: {self.audio_dir}")
            return
        
        for sound_file in sound_files:
            rel_path = sound_file.relative_to(self.audio_dir)
            
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "default"
            
            filename = sound_file.name
            
            # Sound-ID generieren (letzter Teil des Dateinamens nach Bindestrichen)
            # z.B. "get-up-aurora.mp3" -> "aurora"
            parts = sound_file.stem.split("-")
            sound_id = parts[-1] if len(parts) > 1 else sound_file.stem
            
            # Erstelle Eintrag im Sound-Map
            self.sound_map[sound_id] = {
                "path": str(sound_file),
                "category": category,
                "filename": filename
            }
        
        print(f"✅ {len(self.sound_map)} Sounds gefunden und gemappt.")
    
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
        if sound_id not in self.sound_map:
            print(f"❌ Sound '{sound_id}' nicht gefunden")
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
                sound_path = self.sound_map[sound_id]["path"]
                
                sound = AudioSegment.from_file(sound_path)
                
                # Audio in Bytes konvertieren
                audio_io = BytesIO()
                sound.export(audio_io, format="wav")
                audio_io.seek(0)
                
                pygame_sound = pygame.mixer.Sound(audio_io)
                
                # Lautstärke setzen
                pygame_sound.set_volume(max(0.0, min(1.0, volume)))
                
                pygame_sound.play()
                
                while pygame.mixer.get_busy():
                    pygame.time.wait(100)
                    
                return True
                
            except Exception as e:
                print(f"❌ Fehler beim Abspielen von '{sound_id}': {e}")
                return False
            finally:
                # Ressourcen freigeben
                if 'audio_io' in locals():
                    audio_io.close()
    
    def stop(self):
        """Stoppt alle Sounds."""
        pygame.mixer.stop()


_mapper = None

def get_mapper(root_dir: str = "audio/sounds") -> AudioManager:
    """Gibt die globale SoundMapper-Instanz zurück."""
    global _mapper
    if _mapper is None:
        _mapper = AudioManager(root_dir)
    return _mapper

def play(sound_id: str, block: bool = False, volume: float = 1.0) -> bool:
    """Spielt einen Sound ab."""
    return get_mapper().play(sound_id, block, volume)

if __name__ == "__main__":
    print("🔊 Sound-System wird initialisiert...")
    
    play("aurora")
    
    import time 
    time.sleep(10)