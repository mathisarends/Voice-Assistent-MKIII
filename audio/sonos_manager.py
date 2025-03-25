import os
import soco
import time
from soco.discovery import by_name
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SonosManager:
    def __init__(self, speaker_ip=None, speaker_name=None):
        """
        Initialisiert den Sonos Manager entweder mit einer festen IP oder durch Entdeckung via Namen.
        Falls weder IP noch Name angegeben ist, wird versucht, irgendeinen Sonos-Speaker zu finden.
        """
        self.speaker = None
        
        if speaker_ip:
            try:
                logger.info(f"Versuche Verbindung mit IP: {speaker_ip}")
                self.speaker = soco.SoCo(speaker_ip)
                logger.info(f"Verbunden mit: {self.speaker.player_name} via IP")
            except Exception as e:
                logger.error(f"Fehler bei der Verbindung mit IP {speaker_ip}: {e}")
                self.speaker = None
        
        if not self.speaker and speaker_name:
            try:
                logger.info(f"Versuche Verbindung mit Sonos-Gerät: {speaker_name}")
                self.speaker = by_name(speaker_name)
                if self.speaker:
                    logger.info(f"Verbunden mit: {self.speaker.player_name} via Name")
                else:
                    logger.error(f"Kein Sonos-Gerät mit dem Namen '{speaker_name}' gefunden")
            except Exception as e:
                logger.error(f"Fehler bei der Suche nach '{speaker_name}': {e}")
        
        if not self.speaker:
            try:
                logger.info("Versuche, irgendeinen Sonos-Speaker zu entdecken...")
                speakers = list(soco.discover())
                if speakers:
                    self.speaker = speakers[0]
                    logger.info(f"Verbunden mit: {self.speaker.player_name} via Entdeckung")
                else:
                    logger.error("Keine Sonos-Geräte im Netzwerk gefunden")
            except Exception as e:
                logger.error(f"Fehler bei der Sonos-Entdeckung: {e}")
        
        if not self.speaker:
            raise Exception("Konnte keinen Sonos-Speaker finden oder verbinden")
    
    def get_speaker_info(self):
        """Zeigt grundlegende Informationen über den Speaker an"""
        return {
            "name": self.speaker.player_name,
            "ip": self.speaker.ip_address,
            "volume": self.speaker.volume,
            "mute": self.speaker.mute,
            "status": self.speaker.get_current_transport_info()['current_transport_state']
        }
    
    def set_volume(self, volume):
        """Setzt die Lautstärke (0-100)"""
        if 0 <= volume <= 100:
            self.speaker.volume = volume
            logger.info(f"Lautstärke geändert auf: {volume}")
        else:
            logger.error("Lautstärke muss zwischen 0 und 100 liegen")
    
    def play(self):
        """Startet die Wiedergabe"""
        self.speaker.play()
        logger.info("Wiedergabe gestartet")
    
    def pause(self):
        """Pausiert die Wiedergabe"""
        self.speaker.pause()
        logger.info("Wiedergabe pausiert")
    
    def stop(self):
        """Stoppt die Wiedergabe"""
        self.speaker.stop()
        logger.info("Wiedergabe gestoppt")
    
    def next_track(self):
        """Spielt den nächsten Titel"""
        self.speaker.next()
        logger.info("Nächster Titel")
    
    def previous_track(self):
        """Spielt den vorherigen Titel"""
        self.speaker.previous()
        logger.info("Vorheriger Titel")
    
    def toggle_mute(self):
        """Schaltet die Stummschaltung um"""
        self.speaker.mute = not self.speaker.mute
        logger.info(f"Stummschaltung: {'Ein' if self.speaker.mute else 'Aus'}")
    
    def play_uri(self, uri, title=None):
        """
        Spielt einen URI ab (z.B. Radio-Stream, Spotify-Track)
        """
        try:
            self.speaker.play_uri(uri, title)
            logger.info(f"Spiele URI ab: {uri}")
            if title:
                logger.info(f"Titel: {title}")
        except Exception as e:
            logger.error(f"Fehler beim Abspielen von URI {uri}: {e}")
    
    def get_queue(self):
        """Gibt die aktuelle Warteschlange zurück"""
        queue = self.speaker.get_queue()
        logger.info(f"Warteschlange enthält {len(queue)} Titel")
        return queue
    
    def clear_queue(self):
        """Leert die Warteschlange"""
        self.speaker.clear_queue()
        logger.info("Warteschlange geleert")
    
    def add_to_queue(self, uri, position=0, as_next=False):
        """
        Fügt einen URI zur Warteschlange hinzu
        """
        try:
            result = self.speaker.add_uri_to_queue(uri, position=position, as_next=as_next)
            logger.info(f"URI zur Warteschlange hinzugefügt: {uri}")
            return result
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen von URI {uri} zur Warteschlange: {e}")
    
    def remove_from_queue(self, index):
        """
        Entfernt einen Titel aus der Warteschlange anhand des Index
        """
        try:
            self.speaker.remove_from_queue(index)
            logger.info(f"Titel an Position {index} aus der Warteschlange entfernt")
        except Exception as e:
            logger.error(f"Fehler beim Entfernen des Titels an Position {index}: {e}")
    
    
    def play_spotify_track(self, track_id):
        uri = f'spotify:track:{track_id}'
        self.play_uri(uri)
        
        
import os
import time
import http.server
import socketserver
import threading
import socket
def get_local_ip():
    """Ermittelt die lokale IP-Adresse des Computers im Netzwerk"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Keine tatsächliche Verbindung erforderlich
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"  # Fallback
    finally:
        s.close()
    return local_ip

def start_http_server(directory, port=8000):
    """Startet einen einfachen HTTP-Server im angegebenen Verzeichnis"""
    # In das Zielverzeichnis wechseln
    os.chdir(directory)
    
    # HTTP-Server konfigurieren
    handler = http.server.SimpleHTTPRequestHandler
    
    # Setze "allow_reuse_address", um den Port schnell wieder freizugeben
    socketserver.TCPServer.allow_reuse_address = True
    
    # Server erstellen und starten
    httpd = socketserver.TCPServer(("", port), handler)
    
    print(f"HTTP-Server gestartet auf Port {port}, serviert Verzeichnis {directory}")
    
    # Server in einem separaten Thread starten
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True  # Thread wird beendet, wenn das Hauptprogramm endet
    server_thread.start()
    
    return httpd
        
        
def main():
    # Aktuelles Verzeichnis ermitteln
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Pfad zum sounds-Verzeichnis (Annahme: Verzeichnisstruktur wie im Beispiel)
    sounds_dir = os.path.join(current_dir, "sounds")
    
    # HTTP-Server starten im sounds-Verzeichnis (enthält wake_up_sounds)
    port = 8080
    httpd = start_http_server(sounds_dir, port)
    
    # Lokale IP-Adresse ermitteln
    local_ip = get_local_ip()
    
    try:
        # Verbindung zum Sonos-Speaker herstellen
        sonos = SonosManager()
        
        # Aktuelle Lautstärke speichern
        current_volume = sonos.get_speaker_info()["volume"]
        
        # Lautstärke für die Weckgeräusche setzen
        sonos.set_volume(20)  # Auf 20% setzen
        
        # Pfad zum wake_up_sounds-Verzeichnis
        wake_up_dir = os.path.join(sounds_dir, "wake_up_sounds")
        
        # Überprüfen, ob das Verzeichnis existiert
        if not os.path.exists(wake_up_dir):
            print(f"Fehler: Verzeichnis '{wake_up_dir}' nicht gefunden!")
            return
        
        # Audiodateien im Verzeichnis auflisten
        files = [f for f in os.listdir("wake_up_sounds") if f.endswith('.mp3')]
        
        if not files:
            print(f"Keine MP3-Dateien im Verzeichnis 'wake_up_sounds' gefunden!")
            return
        
        print(f"Gefundene Audiodateien: {len(files)}")
        for i, file in enumerate(files):
            print(f"{i+1}. {file}")
        
        # Beispiel: Spiele die erste Datei ab
        if files:
            # Wähle eine Datei aus (hier die erste)
            file_to_play = files[0]
            
            # HTTP-URL zur Datei erstellen
            http_url = f"http://{local_ip}:{port}/wake_up_sounds/{file_to_play}"
            
            print(f"Versuche Datei abzuspielen: {file_to_play}")
            print(f"HTTP URL: {http_url}")
            
            # Warteschlange leeren
            sonos.clear_queue()
            
            try:
                # Direkt mit play_uri abspielen
                sonos.play_uri(http_url, title=file_to_play)
                
                # Warte etwas, damit die Wiedergabe starten kann
                print("Wiedergabe gestartet. Spielt für 10 Sekunden...")
                time.sleep(10)
                
                # Wiedergabe pausieren
                sonos.pause()
                print("Wiedergabe pausiert.")
                
            except Exception as e:
                print(f"Fehler beim Abspielen: {e}")
        
        # Ursprüngliche Lautstärke wiederherstellen
        sonos.set_volume(current_volume)
        print(f"Lautstärke zurück auf {current_volume}%")
        
    finally:
        # HTTP-Server beenden
        print("Beende HTTP-Server...")
        httpd.shutdown()
        httpd.server_close()
        print("HTTP-Server beendet.")

if __name__ == "__main__":
    main()