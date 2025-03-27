import os
import requests
import soco
import socket
from pathlib import Path
import time
from typing import Dict
import socket

from audio.sonos.sonos_http_server import start_http_server
from audio.strategy.audio_playback_strategy import AudioPlaybackStrategy

class SonosAudioStrategy(AudioPlaybackStrategy):
    """Implementiert Audio-Wiedergabe über Sonos-Lautsprecher."""
    
    def __init__(self, speaker_name: str = None, speaker_ip: str = None, http_server_port: int = 8000):
        self.speaker_name = speaker_name
        self.speaker_ip = speaker_ip
        self.http_server_port = http_server_port
        self.http_server_ip = None
        self.sonos_device = None
        self._initial_sonos_volume = None
        self._current_volume = 1.0
        self.http_server = None
    
    def initialize(self):
        """Initialisiert die Sonos-Verbindung und startet den HTTP-Server."""
        
        # Lokale IP ermitteln
        self.http_server_ip = self._get_local_ip()
        
        # HTTP-Server starten
        self._start_http_server()
        
        print("🔍 Suche nach Sonos-Lautsprechern im Netzwerk...")
        
        try:
            # Fall 1: Suche nach IP
            if self.speaker_ip:
                try:
                    device = soco.SoCo(self.speaker_ip)
                    device.player_name  # Dies schlägt fehl, wenn das Gerät nicht erreichbar ist
                    print(f"✅ Sonos-Lautsprecher gefunden: {device.player_name} ({self.speaker_ip})")
                    self.sonos_device = device
                    self._initial_sonos_volume = self.sonos_device.volume
                    return
                except Exception as e:
                    print(f"❌ Konnte nicht mit Sonos-Lautsprecher unter {self.speaker_ip} verbinden: {e}")
            
            # Fall 2: Suche nach Namen
            if self.speaker_name:
                devices = list(soco.discover())
                for device in devices:
                    if device.player_name.lower() == self.speaker_name.lower():
                        print(f"✅ Sonos-Lautsprecher gefunden: {device.player_name} ({device.ip_address})")
                        self.sonos_device = device
                        self._initial_sonos_volume = self.sonos_device.volume
                        return
                print(f"❌ Kein Sonos-Lautsprecher mit Namen '{self.speaker_name}' gefunden")
            
            # Fall 3: Automatisch ersten verfügbaren Lautsprecher auswählen
            devices = list(soco.discover())
            if devices:
                device = devices[0]
                print(f"✅ Sonos-Lautsprecher automatisch gewählt: {device.player_name} ({device.ip_address})")
                self.sonos_device = device
                self._initial_sonos_volume = self.sonos_device.volume
                return
            else:
                print("❌ Keine Sonos-Lautsprecher im Netzwerk gefunden")
                
        except Exception as e:
            print(f"❌ Fehler bei der Suche nach Sonos-Lautsprechern: {e}")
    
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
    
    def _start_http_server(self):
        """Startet den HTTP-Server für Sonos."""
        try:
            # Starte den Server mit dem richtigen Projektverzeichnis
            project_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.http_server = start_http_server(project_dir=project_dir, port=self.http_server_port)
            
            if self.http_server and self.http_server.is_running():
                print(f"✅ HTTP-Server für Sonos gestartet auf Port {self.http_server_port}")
                return True
            else:
                print("❌ HTTP-Server konnte nicht gestartet werden")
                return False
                
        except ImportError as e:
            print(f"❌ Fehler beim Importieren des HTTP-Servers: {e}")
            print("   Sonos-Funktionalität wird eingeschränkt sein!")
            return False
        except Exception as e:
            print(f"❌ Fehler beim Starten des HTTP-Servers für Sonos: {e}")
            print("   Sonos-Funktionalität wird eingeschränkt sein!")
            return False
    
    def play_sound(self, sound_info: Dict, volume: float) -> bool:
        """Spielt einen Sound über Sonos-Lautsprecher ab."""
        if not self.sonos_device:
            print("❌ Kein Sonos-Lautsprecher verfügbar")
            return False
        
        try:
            # URL aus Sound-Info verwenden oder neu erstellen
            if "url" in sound_info:
                sound_url = sound_info["url"]
            else:
                # Sonst manuell eine URL erstellen
                category = sound_info["category"]
                filename = sound_info["filename"]
                sound_url = f"http://{self.http_server_ip}:{self.http_server_port}/audio/sounds/{category}/{filename}"
            
            print(f"🔊 Spiele Sound auf Sonos ab: {sound_url}")
            
            # Teste die URL-Erreichbarkeit
            try:
                response = requests.head(sound_url, timeout=2)
                if response.status_code != 200:
                    print(f"⚠️ Warnung: URL nicht erreichbar (Status {response.status_code}): {sound_url}")
                    print("   Stelle sicher, dass der HTTP-Server läuft und das Projektverzeichnis korrekt eingestellt ist.")
                    return False
            except Exception as e:
                print(f"⚠️ Warnung: Konnte URL nicht überprüfen: {e}")
            
            # Stelle Lautstärke ein (Umrechnung von 0-1 auf 0-100)
            sonos_volume = int(min(100, max(0, volume * 100)))
            
            # Speichere aktuelle Sonos-Einstellungen
            previous_volume = self.sonos_device.volume
            
            # Setze Lautstärke
            self.sonos_device.volume = sonos_volume
            self._current_volume = volume
            
            # Spiele die URL auf dem Sonos-Gerät ab
            self.sonos_device.play_uri(sound_url)
            
            # Warte, bis der Sound fertig abgespielt wurde
            while self.is_playing():
                time.sleep(0.1)
            
            # Stelle ursprüngliche Lautstärke wieder her
            self.sonos_device.volume = previous_volume
            
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Abspielen der URL: {e}")
            return False
    
    def is_playing(self) -> bool:
        """Prüft, ob Sonos aktuell Audio abspielt."""
        if not self.sonos_device:
            return False
        
        try:
            return self.sonos_device.get_current_transport_info()['current_transport_state'] == 'PLAYING'
        except Exception as e:
            print(f"❌ Fehler beim Prüfen des Sonos-Status: {e}")
            return False
    
    def stop_playback(self):
        """Stoppt die Wiedergabe auf dem Sonos-Lautsprecher."""
        if not self.sonos_device:
            return
        
        try:
            self.sonos_device.stop()
        except Exception as e:
            print(f"❌ Fehler beim Stoppen der Sonos-Wiedergabe: {e}")
    
    def set_volume(self, volume: float):
        """Setzt die Lautstärke des Sonos-Lautsprechers (0.0 bis 1.0)."""
        if not self.sonos_device:
            return
        
        sonos_volume = int(min(100, max(0, volume * 100)))
        self.sonos_device.volume = sonos_volume
        self._current_volume = volume
    
    def fade_out(self, duration: float):
        """Führt einen Fade-Out-Effekt auf dem Sonos-Lautsprecher durch."""
        if not self.sonos_device or not self.is_playing():
            return
        
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
    
    def get_all_sonos_speakers(self):
        """Gibt eine Liste aller Sonos-Lautsprecher im Netzwerk zurück."""
        import soco
        try:
            devices = list(soco.discover())
            return [{"name": device.player_name, "ip": device.ip_address} for device in devices]
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Sonos-Lautsprecher: {e}")
            return []
    
    def select_speaker(self, speaker_name=None, speaker_ip=None):
        """Wählt einen anderen Sonos-Lautsprecher aus."""
        import soco
        
        print("🔍 Suche nach Sonos-Lautsprechern im Netzwerk...")
        
        try:
            # Fall 1: Suche nach IP
            if speaker_ip:
                try:
                    device = soco.SoCo(speaker_ip)
                    device.player_name  # Dies schlägt fehl, wenn das Gerät nicht erreichbar ist
                    print(f"✅ Sonos-Lautsprecher gefunden: {device.player_name} ({speaker_ip})")
                    self.sonos_device = device
                    self._initial_sonos_volume = self.sonos_device.volume
                    return True
                except Exception as e:
                    print(f"❌ Konnte nicht mit Sonos-Lautsprecher unter {speaker_ip} verbinden: {e}")
            
            # Fall 2: Suche nach Namen
            if speaker_name:
                devices = list(soco.discover())
                for device in devices:
                    if device.player_name.lower() == speaker_name.lower():
                        print(f"✅ Sonos-Lautsprecher gefunden: {device.player_name} ({device.ip_address})")
                        self.sonos_device = device
                        self._initial_sonos_volume = self.sonos_device.volume
                        return True
                print(f"❌ Kein Sonos-Lautsprecher mit Namen '{speaker_name}' gefunden")
            
            # Kein passender Lautsprecher gefunden
            return False
                
        except Exception as e:
            print(f"❌ Fehler bei der Suche nach Sonos-Lautsprechern: {e}")
            return False