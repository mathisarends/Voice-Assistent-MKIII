import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import socket
from singleton_decorator import singleton

class CustomHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    rbufsize = 64 * 1024
    
    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def guess_type(self, path):
        """Überschriebe Methode, um korrekte MIME-Typen für Audio-Dateien zu liefern."""
        base, ext = os.path.splitext(path)
        if ext.lower() == '.wav':
            return 'audio/wav'
        return super().guess_type(path)

@singleton
class SonosHTTPServer:
    """Einfacher HTTP-Server, um Audiodateien für Sonos bereitzustellen."""
    
    def __init__(self, project_dir=None, port=8000):
        """
        Initialisiert den HTTP-Server.
        """
        if project_dir is None:
            # Wenn kein Projektverzeichnis angegeben ist,
            # nehme das übergeordnete Verzeichnis der aktuellen Datei
            # (Annahme: Skript liegt in project_dir/audio/sonos/...)
            self.project_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        else:
            self.project_dir = Path(project_dir)
        
        self.port = port
        self._server = None
        self._server_thread = None
        self._is_running = False
        
        # Die IP-Adresse des Servers im lokalen Netzwerk
        self.server_ip = self._get_local_ip()
    
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
    
    def start(self):
        """Startet den HTTP-Server in einem separaten Thread."""
        if self._is_running:
            print(f"ℹ️ HTTP-Server läuft bereits auf Port {self.port}")
            return self
        
        os.chdir(self.project_dir)
        

        
        try:
            self._server = HTTPServer(("", self.port), CustomHandler)
            self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._server_thread.start()
            self._is_running = True
            
            print(f"✅ HTTP-Server gestartet auf http://{self.server_ip}:{self.port}/")
            print(f"   Basis-Verzeichnis: {self.project_dir}")
            
            return self
        except Exception as e:
            print(f"❌ Fehler beim Starten des HTTP-Servers: {e}")
            return self
    
    def stop(self):
        """Stoppt den HTTP-Server."""
        if not self._is_running or self._server is None:
            return
            
        try:
            self._server.shutdown()
            self._server.server_close()
            self._is_running = False
            print(f"✅ HTTP-Server auf Port {self.port} gestoppt")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Stoppen des HTTP-Servers: {e}")
            return False
    
    def is_running(self):
        """Prüft, ob der Server läuft."""
        return self._is_running
    
    def get_url_for_file(self, file_path):
        """
        Erstellt eine URL für eine Datei relativ zum Projektverzeichnis.
        """
        file_path = Path(file_path)
        
        # Relativer Pfad vom Projektverzeichnis zur Datei
        try:
            rel_path = file_path.relative_to(self.project_dir)
        except ValueError:
            print(f"⚠️ Warnung: Datei liegt nicht im Projektverzeichnis: {file_path}")
            return None
        
        url_path = str(rel_path).replace("\\", "/")
        
        # Vollständige URL
        return f"http://{self.server_ip}:{self.port}/{url_path}"


_http_server = None

def get_http_server(project_dir=None, port=8000):
    """Gibt die globale HTTP-Server-Instanz zurück."""
    global _http_server
    if _http_server is None:
        _http_server = SonosHTTPServer(project_dir, port)
    return _http_server

def start_http_server(project_dir=None, port=8000):
    """Startet den HTTP-Server und gibt die Instanz zurück."""
    server = get_http_server(project_dir, port)
    server.start()
    return server

def stop_http_server():
    """Stoppt den HTTP-Server."""
    if _http_server:
        return _http_server.stop()
    return False
