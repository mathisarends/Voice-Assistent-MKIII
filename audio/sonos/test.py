import os
import sys
from pathlib import Path
import time

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
        
        time.sleep(5)
        
        sonos_manager.play("stop-listening-new")
        
        time.sleep(10)
        
    except Exception as e:
        print(f"Fehler beim Initialisieren des Sonos Audio Managers: {e}")
        stop_http_server()
        return None, None
    
setup_sonos()