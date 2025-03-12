import os
import time
from pathlib import Path
from typing import Dict, List, Optional
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
        
        self._lock = threading.Lock()
        
        self.supported_formats = [".mp3", ".wav"]
        
        self._stop_loop = False
        
        self._loop_thread = None
        
        # Aktuelle Lautstärke speichern
        self._current_volume = 1.0
        
        # Standard-Fade-Out-Dauer in Sekunden
        self.fade_out_duration = 2.5
        
        self._discover_sounds()
    
    def _discover_sounds(self):
        """Durchsucht rekursiv das Audio-Verzeichnis nach Sounddateien."""
        print(f"🔍 Durchsuche Verzeichnis: {self.audio_dir}")
        
        if not self.audio_dir.exists():
            print(f"❌ Verzeichnis nicht gefunden: {self.audio_dir}")
            return
        
        # Liste für alle gefundenen Sounddateien
        sound_files = []
        
        # Alle unterstützten Formate suchen
        for format_ext in self.supported_formats:
            sound_files.extend(list(self.audio_dir.glob(f"**/*{format_ext}")))
        
        if not sound_files:
            print(f"❌ Keine Sounddateien gefunden in: {self.audio_dir}")
            return
        
        for sound_file in sound_files:
            rel_path = sound_file.relative_to(self.audio_dir)
            
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "default"
            
            filename = sound_file.name
            
            sound_id = sound_file.stem
            
            # Erstelle Eintrag im Sound-Map
            self.sound_map[sound_id] = {
                "path": str(sound_file),
                "category": category,
                "filename": filename,
                "format": sound_file.suffix.lower()
            }
        
        print(f"✅ {len(self.sound_map)} Sounds gefunden und gemappt.")
        
        # Zeige Statistik der gefundenen Formate
        format_stats = {}
        for info in self.sound_map.values():
            format_ext = info["format"]
            format_stats[format_ext] = format_stats.get(format_ext, 0) + 1
        
        for fmt, count in format_stats.items():
            print(f"  - {fmt}: {count} Dateien")
    
    def get_sounds_by_category(self, category: str) -> Dict[str, Dict]:
        """Gibt alle Sounds einer bestimmten Kategorie zurück."""
        return {
            sound_id: info for sound_id, info in self.sound_map.items()
            if info["category"] == category
        }
    
    def play(self, sound_id: str, block: bool = False, volume: float = 1.0) -> bool:
        if sound_id not in self.sound_map:
            print(f"❌ Sound '{sound_id}' nicht gefunden")
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
        return pygame.mixer.get_busy()
    
    def play_loop(self, sound_id: str, duration: float, volume: float = 1.0) -> bool:
        if sound_id not in self.sound_map:
            print(f"❌ Sound '{sound_id}' nicht gefunden")
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
        
        print(f"🔄 Loop gestartet für '{sound_id}' ({duration} Sekunden)")
        
        try:
            while time.time() < end_time and not self._stop_loop:
                self._play_sound(sound_id, volume)
                
                if self._stop_loop:
                    break
                
                if time.time() >= end_time:
                    break
        except Exception as e:
            print(f"❌ Fehler beim Loopen von '{sound_id}': {e}")
        finally:
            print(f"🔄 Loop beendet für '{sound_id}'")
    
    def stop_loop(self):
        """Stoppt den aktuellen Sound-Loop mit Fade-Out."""
        if self._loop_thread and self._loop_thread.is_alive():
            # Fade-Out ausführen, bevor wir den Loop stoppen
            self.fade_out()
            
            self._stop_loop = True
            
            # Warte bis der Loop-Thread beendet ist (mit Timeout)
            self._loop_thread.join(timeout=1.0)
            print("🔄 Loop gestoppt")
    
    def fade_out(self, duration: Optional[float] = None):
        """
        Führt einen Fade-Out für alle aktuell spielenden Sounds durch.
        
        Args:
            duration: Dauer des Fade-Outs in Sekunden, wenn None wird der Standardwert verwendet
        """
        if not pygame.mixer.get_busy():
            return
        
        if duration is None:
            duration = self.fade_out_duration
        
        print(f"🔉 Führe Fade-Out über {duration} Sekunden durch...")
        
        # Starte mit der aktuellen Lautstärke
        start_volume = self._current_volume
        
        # Anzahl der Schritte für den Fade-Out
        steps = int(duration * 20) 
        
        # Schrittweite
        volume_step = start_volume / steps if steps > 0 else 0
        
        # Zeit pro Schritt
        time_step = duration / steps if steps > 0 else 0
        
        # Wende Fade-Out auf alle aktive Channels an
        for step in range(steps):
            # Berechne neue Lautstärke
            current_volume = start_volume - (volume_step * step)
            current_volume = max(0.0, current_volume)  # Nicht unter 0
            
            # Setze Lautstärke für alle aktiven Kanäle
            for i in range(pygame.mixer.get_num_channels()):
                channel = pygame.mixer.Channel(i)
                if channel.get_busy():
                    channel.set_volume(current_volume)
            
            time.sleep(time_step)
        
        pygame.mixer.stop()
        print("🔇 Fade-Out abgeschlossen")
    
    def _play_sound(self, sound_id: str, volume: float) -> bool:
        """Interne Methode zum Abspielen eines Sounds."""
        with self._lock:
            try:
                sound_path = self.sound_map[sound_id]["path"]
                sound_format = self.sound_map[sound_id]["format"]
                
                # Optimierung: Bei WAV-Dateien direkt pygame verwenden
                if sound_format == ".wav" and os.path.exists(sound_path):
                    try:
                        # Versuche direkte Wiedergabe mit pygame
                        pygame_sound = pygame.mixer.Sound(sound_path)
                        pygame_sound.set_volume(max(0.0, min(1.0, volume)))
                        pygame_sound.play()
                        
                        while pygame.mixer.get_busy() and not self._stop_loop:
                            pygame.time.wait(100)
                            
                        return True
                    except Exception as e:
                        print(f"⚠️ Direkte WAV-Wiedergabe fehlgeschlagen, versuche mit pydub: {e}")
                        # Fallback auf pydub-Methode
                
                # Wiedergabe mit pydub (funktioniert für MP3 und als Fallback für WAV)
                sound = AudioSegment.from_file(sound_path)
                
                # Audio in Bytes konvertieren
                audio_io = BytesIO()
                sound.export(audio_io, format="wav")
                audio_io.seek(0)
                
                pygame_sound = pygame.mixer.Sound(audio_io)
                
                # Lautstärke setzen
                pygame_sound.set_volume(max(0.0, min(1.0, volume)))
                
                pygame_sound.play()
                
                while pygame.mixer.get_busy() and not self._stop_loop:
                    pygame.time.wait(100)
                    
                return True
                
            except Exception as e:
                print(f"❌ Fehler beim Abspielen von '{sound_id}': {e}")
                return False
            finally:
                if 'audio_io' in locals():
                    audio_io.close()
    
    def stop(self):
        """Stoppt alle Sounds mit Fade-Out."""
        self.fade_out()


_mapper = None

def get_mapper(root_dir: str = "audio/sounds") -> AudioManager:
    """Gibt die globale AudioManager-Instanz zurück."""
    global _mapper
    if _mapper is None:
        _mapper = AudioManager(root_dir)
    return _mapper

def play(sound_id: str, block: bool = False, volume: float = 1.0) -> bool:
    """Spielt einen Sound ab."""
    return get_mapper().play(sound_id, block, volume)

def stop():
    """Stoppt alle Sounds mit Fade-Out."""
    get_mapper().stop()

def fade_out(duration: Optional[float] = None):
    """Führt einen Fade-Out für alle aktuell spielenden Sounds durch."""
    get_mapper().fade_out(duration)

def play_loop(sound_id: str, duration: float, volume: float = 1.0) -> bool:
    """Spielt einen Sound im Loop für die angegebene Dauer ab."""
    return get_mapper().play_loop(sound_id, duration, volume)

def stop_loop():
    """Stoppt den aktuellen Sound-Loop mit Fade-Out."""
    get_mapper().stop_loop()

if __name__ == "__main__":
    print("🔊 Sound-System wird initialisiert...")
    
    # Beispiel: Sound im Loop abspielen
    print("\nVersuche 'wake-up-focus' für 10 Sekunden zu loopen...")
    if play_loop("wake-up-focus", 10):
        print("Sound wird geloopt!")
    
    # Nach 5 Sekunden stoppen wir mit Fade-Out
    time.sleep(5)
    print("Stoppe mit Fade-Out...")
    stop()
    
    time.sleep(2)  # Kurz warten
    
    # Noch ein Sound abspielen und dann mit Fade-Out beenden
    print("\nSpiele einen Sound ab und beende mit Fade-Out...")
    play("wake-up-focus")
    time.sleep(3)
    fade_out(2.0)  # 2 Sekunden Fade-Out
    
    time.sleep(3)  # Warte, bis alles fertig ist