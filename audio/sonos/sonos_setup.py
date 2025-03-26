import os
import sys
import time
from pathlib import Path

# Füge das Projektverzeichnis zum Python-Pfad hinzu
project_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, str(project_dir))

from audio.sonos.sonos_manager import SonosAudioManager
from audio.sonos.sonos_http_server import start_http_server, stop_http_server

def setup_sonos(speaker_ip="192.168.178.68"):  
    audio_dir = "audio/sounds"
    
    print("\n1. Starte HTTP-Server...")
    http_server = start_http_server(project_dir)
    
    # Wenn der Server nicht gestartet wurde, beenden
    if not http_server.is_running():
        print("Fehler beim Starten des HTTP-Servers. Beende...")
        return None, None
    
    print("\n2. Initialisiere Sonos Audio Manager...")
    try:
        sonos_manager = SonosAudioManager(
            root_dir=audio_dir, 
            http_server_port=http_server.port,
            sonos_ip=speaker_ip
        )
        
        sonos_manager.play("startup")
        
    except Exception as e:
        print(f"Fehler beim Initialisieren des Sonos Audio Managers: {e}")
        stop_http_server()
        return None, None
    
    # Prüfe, ob die Verbindung erfolgreich war
    if not sonos_manager.sonos_device:
        print(f"Konnte keine Verbindung zu Sonos unter IP {speaker_ip} herstellen.")
        stop_http_server()
        return None, None
    
    print(f"\n✅ Erfolgreich mit Sonos-Lautsprecher '{sonos_manager.sonos_device.player_name}' verbunden!")
    
setup_sonos()