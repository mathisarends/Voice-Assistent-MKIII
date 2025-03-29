import os
import re
from functools import wraps

import spotipy
from dotenv import load_dotenv
from singleton_decorator import singleton
from spotipy.oauth2 import SpotifyOAuth

from util.loggin_mixin import LoggingMixin


class SpotifyClient:
    def __init__(self):
        load_dotenv()
        
        cache_folder = os.path.join(os.path.dirname(__file__), ".cache")
        cache_file = os.path.join(cache_folder, ".spotify_cache")
        
        os.makedirs(cache_folder, exist_ok=True)
        
        self.api = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                redirect_uri="http://localhost:8080",
                scope="user-modify-playback-state user-read-playback-state user-read-currently-playing streaming app-remote-control user-library-read user-library-modify user-read-private user-top-read",
                cache_path=cache_file,
            )
        )
        
        
def spotify_api_call(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except spotipy.exceptions.SpotifyException as e:
            action_name = func.__name__.replace('_', ' ')
            self.logger.error(f"❌ Spotify API Fehler bei '{action_name}': {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unerwarteter Fehler bei '{func.__name__}': {e}")
            return False
            
    return wrapper


@singleton
class SpotifyPlaybackController(LoggingMixin):
    def __init__(self, fallback_device_pattern="PC"):
        self.client = SpotifyClient().api
        self.fallback_device_pattern = fallback_device_pattern
        self.active_device_id = None
        self.devices = {}
        self.refresh_devices()
        
        # Versuche ein passendes Gerät zu finden
        self._find_and_set_initial_device()

    def _find_and_set_initial_device(self):
        # Zuerst schauen wir nach einem aktiven Gerät
        active_device = self.get_active_device()
        if active_device:
            self.logger.info(f"✅ Aktives Gerät gefunden: {active_device['name']}")
            self.active_device_id = active_device['id']
            return True
            
        pc_devices = [name for name in self.devices.keys() if self.fallback_device_pattern.lower() in name.lower()]
        if pc_devices:
            self.set_active_device(pc_devices[0])
            return True
            
        if self.devices:
            first_device = list(self.devices.keys())[0]
            self.set_active_device(first_device)
            return True
            
        self.logger.warning("⚠️ Kein Spotify-Gerät gefunden!")
        return False

    @spotify_api_call
    def refresh_devices(self):
        """Aktualisiert die Liste der verfügbaren Geräte."""
        device_list = self.client.devices().get("devices", [])
        self.devices = {device["name"]: device for device in device_list}
        return self.devices

    @spotify_api_call
    def get_available_devices(self):
        """Gibt eine Liste aller verfügbaren Spotify-Geräte zurück."""
        self.refresh_devices()
        return list(self.devices.values())

    def get_active_device(self):
        """Findet das aktuell aktive Gerät."""
        self.refresh_devices()
        for device in self.devices.values():
            if device["is_active"]:
                return device
        return None

    def set_active_device(self, device_name):
        """Setzt das angegebene Gerät als aktives Gerät für Wiedergabe."""
        if device_name in self.devices:
            self.logger.info(f"✅ Gerät gefunden: {device_name} ({self.devices[device_name]['id']})")
            self.active_device_id = self.devices[device_name]["id"]
            return True
        else:
            self.logger.error(f"❌ Gerät '{device_name}' nicht gefunden. Verfügbare Geräte: {', '.join(self.devices.keys())}")
            return False

    def _ensure_device_connection(self):
        """Stellt sicher, dass ein aktives Gerät verfügbar ist."""
        if not self.active_device_id:
            self.refresh_devices()
            return self._find_and_set_initial_device()
        return True

    @spotify_api_call
    def switch_device(self, device_name, force_play=False):
        """Wechselt das aktive Gerät und setzt die Wiedergabe fort, falls gewünscht."""
        if device_name in self.devices:
            device_id = self.devices[device_name]["id"]
            self.client.transfer_playback(device_id=device_id, force_play=force_play)
            self.active_device_id = device_id
            
            if force_play:
                self.logger.info(f"▶️ Wiedergabe fortgesetzt auf: {device_name}")
            else:
                self.logger.info(f"✅ Aktives Gerät gewechselt zu: {device_name}")
            
            return True
        else:
            self.logger.error(f"❌ Gerät '{device_name}' nicht gefunden. Verfügbare Geräte: {', '.join(self.devices.keys())}")
            return False

    @spotify_api_call
    def search_track(self, query):
        """Sucht nach einem Track basierend auf der Anfrage."""
        results = self.client.search(q=query)
        tracks = results.get("tracks", {}).get("items", [])
        
        if not tracks:
            self.logger.info("❌ Kein Song gefunden!")
            return None
        
        track_with_artist_match = self._find_track_with_artist_match(query, tracks)
        if track_with_artist_match:
            return track_with_artist_match
        
        track = tracks[0]
        self.logger.info(f"🎵 Gefunden (Erstes Ergebnis): {track['name']} - {track['artists'][0]['name']}")
        return track["uri"]

    def _find_track_with_artist_match(self, query, tracks):
        """Sucht nach einem Track, bei dem ein Keyword aus der Query im Künstlernamen vorkommt."""
        keywords = query.lower().split()
        
        for track in tracks:
            track_artists = [artist["name"].lower() for artist in track["artists"]]
            
            if any(keyword in ' '.join(track_artists) for keyword in keywords):
                self.logger.info(f"🎵 Gefunden (Künstler-Match): {track['name']} - {track['artists'][0]['name']}")
                return track["uri"]
        
        return None

    @spotify_api_call
    def play_track(self, query):
        """Spielt einen Track basierend auf der Suchanfrage ab."""
        self._ensure_device_connection()
        track_uri = self.search_track(query)
        if track_uri:
            self.client.start_playback(device_id=self.active_device_id, uris=[track_uri])
            self.logger.info("🎶 Song wird abgespielt!")
            return True
        else:
            self.logger.info("❌ Song konnte nicht abgespielt werden!")
            return False

    @spotify_api_call
    def convert_to_uri(self, identifier):
        """Konvertiert eine Spotify-URL oder ID in ein URI-Format."""
        if identifier.startswith("spotify:"):
            return identifier

        patterns = {
            "playlist": r"open\.spotify\.com/playlist/([a-zA-Z0-9]+)",
            "track": r"open\.spotify\.com/track/([a-zA-Z0-9]+)",
            "album": r"open\.spotify\.com/album/([a-zA-Z0-9]+)",
        }

        for content_type, pattern in patterns.items():
            match = re.search(pattern, identifier)
            if match:
                content_id = match.group(1)
                return f"spotify:{content_type}:{content_id}"

        return None

    @spotify_api_call
    def set_volume(self, volume):
        """Setzt die Wiedergabelautstärke (0-100%)."""
        self._ensure_device_connection()
        volume = max(0, min(100, volume))
        self.client.volume(volume, device_id=self.active_device_id)
        self.logger.info(f"🔊 Lautstärke auf {volume}% gesetzt")
        return True

    @spotify_api_call
    def next_track(self):
        """Springt zum nächsten Track."""
        self._ensure_device_connection()
        self.client.next_track(device_id=self.active_device_id)
        self.logger.info("⏭️ Nächster Track")
        return True

    @spotify_api_call
    def previous_track(self):
        """Springt zum vorherigen Track."""
        self._ensure_device_connection()
        self.client.previous_track(device_id=self.active_device_id)
        self.logger.info("⏮️ Vorheriger Track")
        return True

    @spotify_api_call
    def pause_playback(self):
        """Pausiert die aktuelle Wiedergabe."""
        self._ensure_device_connection()
        self.client.pause_playback(device_id=self.active_device_id)
        self.logger.info("⏸️ Wiedergabe pausiert")
        return True

    @spotify_api_call
    def resume_playback(self):
        """Setzt die Wiedergabe fort."""
        self._ensure_device_connection()
        self.client.start_playback(device_id=self.active_device_id)
        self.logger.info("▶️ Wiedergabe fortgesetzt")
        return True
    
    
if __name__ == "__main__":
    spot = SpotifyPlaybackController()
    spot.play_track("Sticky Drake")