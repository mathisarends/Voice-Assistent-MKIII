#!/usr/bin/env python3
import os
import time
from pathlib import Path
from typing import Dict, Optional
import threading
import soco
import socket
import requests
from singleton_decorator import singleton

@singleton
class SonosAudioManager:
    """Erweitert den AudioManager, um Audiodateien über Sonos-Lautsprecher abzuspielen."""
    
    def __init__(self, root_dir: str = "audio/sounds", sonos_speaker_name: str = None, sonos_ip: str = None,
                 http_server_port: int = 8000):
        self.project_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.audio_dir = self.project_dir / root_dir
        
        # Lokale IP und HTTP-Server-Port
        self.http_server_ip = self._get_local_ip()
        self.http_server_port = http_server_port
        
        self.sound_map: Dict[str, Dict] = {}
        
        self._lock = threading.Lock()
        
        self.supported_formats = [".mp3", ".wav"]
        
        self._stop_loop = False
        
        self._loop_thread = None
        
        self._current_volume = 1.0
        
        self.fade_out_duration = 2.5
        
        self.sonos_device = self._find_sonos_device(sonos_speaker_name, sonos_ip)
        
        if self.sonos_device:
            self._initial_sonos_volume = self.sonos_device.volume
        
        self._discover_sounds()
    
    def _get_local_ip(self):
        """Ermittelt die lokale IP-Adresse des Geräts im Netzwerk."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            print(f"❌ Fehler beim Ermitteln der IP-Adresse: {e}")
            return "127.0.0.1"
    
    def _find_sonos_device(self, speaker_name: str = None, ip_address: str = None):
        """Findet ein Sonos-Gerät basierend auf Namen oder IP-Adresse."""
        print("🔍 Suche nach Sonos-Lautsprechern im Netzwerk...")
        
        try:
            if ip_address:
                try:
                    device = soco.SoCo(ip_address)
                    device.player_name
                    print(f"✅ Sonos-Lautsprecher gefunden: {device.player_name} ({ip_address})")
                    return device
                except Exception as e:
                    print(f"❌ Konnte nicht mit Sonos-Lautsprecher unter {ip_address} verbinden: {e}")
            
            # Fall 2: Nach Namen suchen
            if speaker_name:
                devices = list(soco.discover())
                for device in devices:
                    if device.player_name.lower() == speaker_name.lower():
                        print(f"✅ Sonos-Lautsprecher gefunden: {device.player_name} ({device.ip_address})")
                        return device
                print(f"❌ Kein Sonos-Lautsprecher mit Namen '{speaker_name}' gefunden")
            
            devices = list(soco.discover())
            if devices:
                device = devices[0]
                print(f"✅ Sonos-Lautsprecher automatisch gewählt: {device.player_name} ({device.ip_address})")
                return device
            else:
                print("❌ Keine Sonos-Lautsprecher im Netzwerk gefunden")
                return None
                
        except Exception as e:
            print(f"❌ Fehler bei der Suche nach Sonos-Lautsprechern: {e}")
            return None
    
    def _discover_sounds(self):
        """Durchsucht rekursiv das Audio-Verzeichnis nach Sounddateien."""
        print(f"🔍 Durchsuche Verzeichnis: {self.audio_dir}")
        
        if not self.audio_dir.exists():
            print(f"❌ Verzeichnis nicht gefunden: {self.audio_dir}")
            return
        
        sound_files = []
        
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
            
            # Bereite die URL für den HTTP-Server vor
            # Achtung: Hier nehmen wir den relativen Pfad vom Projektverzeichnis!
            rel_path_from_project = sound_file.relative_to(self.project_dir)
            url_path = str(rel_path_from_project).replace("\\", "/")
            sound_url = f"http://{self.http_server_ip}:{self.http_server_port}/{url_path}"
            
            # Erstelle Eintrag im Sound-Map
            self.sound_map[sound_id] = {
                "path": str(sound_file),
                "category": category,
                "filename": filename,
                "format": sound_file.suffix.lower(),
                "url": sound_url
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
    
    def play(self, sound_id: str, block: bool = False, volume: float = 0.35) -> bool:
        """Spielt einen Sound über den Sonos-Lautsprecher ab."""
        if not self.sonos_device:
            print("❌ Kein Sonos-Lautsprecher verfügbar")
            return False
            
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
        """Prüft, ob aktuell ein Sound über Sonos abgespielt wird."""
        if not self.sonos_device:
            return False
        
        try:
            return self.sonos_device.get_current_transport_info()['current_transport_state'] == 'PLAYING'
        except Exception as e:
            print(f"❌ Fehler beim Prüfen des Sonos-Status: {e}")
            return False
    
    def play_loop(self, sound_id: str, duration: float, volume: float = 1.0) -> bool:
        """Spielt einen Sound im Loop für die angegebene Dauer ab."""
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
        Führt einen Fade-Out für Sonos durch
        
        Args:
            duration: Dauer des Fade-Outs in Sekunden, wenn None wird der Standardwert verwendet
        """
        if not self.sonos_device or not self.is_playing():
            return
        
        if duration is None:
            duration = self.fade_out_duration
        
        print(f"🔉 Führe Fade-Out über {duration} Sekunden durch...")
        
        try:
            # Starte mit der aktuellen Lautstärke
            start_volume = self.sonos_device.volume
            
            # Anzahl der Schritte für den Fade-Out
            steps = int(duration * 4)  # 4 Schritte pro Sekunde
            
            # Schrittweite
            volume_step = start_volume / steps if steps > 0 else 0
            
            # Zeit pro Schritt
            time_step = duration / steps if steps > 0 else 0
            
            # Wende Fade-Out an
            for step in range(steps):
                # Berechne neue Lautstärke
                current_volume = start_volume - (volume_step * step)
                current_volume = max(0, int(current_volume))  # Sonos benötigt Integer-Werte
                
                # Setze Lautstärke
                self.sonos_device.volume = current_volume
                
                time.sleep(time_step)
            
            # Stoppe die Wiedergabe
            self.sonos_device.stop()
            
            # Stelle die ursprüngliche Lautstärke nach einer kurzen Pause wieder her
            time.sleep(0.5)
            self.sonos_device.volume = start_volume
            
            print("🔇 Fade-Out abgeschlossen")
            
        except Exception as e:
            print(f"❌ Fehler beim Fade-Out: {e}")
            try:
                # Im Fehlerfall trotzdem versuchen zu stoppen
                self.sonos_device.stop()
            except:
                pass
    
    def _play_sound(self, sound_id: str, volume: float) -> bool:
        """Interne Methode zum Abspielen eines Sounds über Sonos."""
        if not self.sonos_device:
            print("❌ Kein Sonos-Lautsprecher verfügbar")
            return False
            
        with self._lock:
            try:
                sound_info = self.sound_map[sound_id]
                sound_url = sound_info["url"]
                print("sound_url", sound_url)
                
                print(f"🔊 Spiele Sound '{sound_id}' auf Sonos ab")
                
                # Teste die URL-Erreichbarkeit
                try:
                    response = requests.head(sound_url, timeout=2)
                    if response.status_code != 200:
                        print(f"⚠️ Warnung: URL nicht erreichbar (Status {response.status_code}): {sound_url}")
                        print("   Stelle sicher, dass der HTTP-Server läuft und das Projektverzeichnis korrekt eingestellt ist.")
                except Exception as e:
                    print(f"⚠️ Warnung: Konnte URL nicht überprüfen: {e}")
                
                # Stelle Lautstärke ein (Umrechnung von 0-1 auf 0-100)
                sonos_volume = int(min(100, max(0, volume * 100)))
                
                # Speichere aktuelle Sonos-Einstellungen
                previous_volume = self.sonos_device.volume
                
                # Setze Lautstärke
                self.sonos_device.volume = sonos_volume
                
                # Spiele die URL auf dem Sonos-Gerät ab
                try:
                    self.sonos_device.play_uri(sound_url)
                    
                    # Warte, bis der Sound fertig abgespielt wurde
                    while self.is_playing() and not self._stop_loop:
                        time.sleep(0.1)
                    
                    # Stelle ursprüngliche Lautstärke wieder her, wenn nicht im Loop
                    if not self._loop_thread or not self._loop_thread.is_alive():
                        self.sonos_device.volume = previous_volume
                    
                    return True
                except Exception as e:
                    print(f"❌ Fehler beim Abspielen der URL: {e}")
                    return False
                
            except Exception as e:
                print(f"❌ Fehler beim Abspielen von '{sound_id}': {e}")
                return False
    
    def stop(self):
        """Stoppt die Wiedergabe auf dem Sonos-Lautsprecher mit Fade-Out."""
        self.fade_out()
        
    def set_volume(self, volume: float):
        """Setzt die Lautstärke des Sonos-Lautsprechers (0.0 bis 1.0)."""
        if not self.sonos_device:
            return
            
        sonos_volume = int(min(100, max(0, volume * 100)))
        self.sonos_device.volume = sonos_volume
        
    def get_all_sonos_speakers(self):
        """Gibt eine Liste aller Sonos-Lautsprecher im Netzwerk zurück."""
        try:
            devices = list(soco.discover())
            return [{"name": device.player_name, "ip": device.ip_address} for device in devices]
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Sonos-Lautsprecher: {e}")
            return []

    def select_speaker(self, speaker_name=None, speaker_ip=None):
        """Wählt einen anderen Sonos-Lautsprecher aus."""
        self.sonos_device = self._find_sonos_device(speaker_name, speaker_ip)
        return self.sonos_device is not None