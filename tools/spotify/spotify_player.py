import os
import re
from functools import wraps

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from tools.spotify.spotify_api_call_wrapper import spotify_api_call
from util.loggin_mixin import LoggingMixin


class SpotifyClient:
    def __init__(self):
        load_dotenv()
        self.api = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                redirect_uri="http://localhost:8080",
                scope="user-modify-playback-state user-read-playback-state user-read-currently-playing streaming app-remote-control user-library-read user-library-modify user-read-private user-top-read",
                # cache_path=".cache"
            )
        )


class SpotifyPlayer(LoggingMixin):
    def __init__(self, device_name="Pixel 8"):
        self.client = SpotifyClient().api
        self.device_name = device_name
        self.device_id = None
        self.set_device_id(self.device_name)

    def set_device_id(self, device_name):
        devices = self.client.devices()

        for device in devices.get("devices", []):
            self.logger.info(device["name"])
            if device["name"] == device_name:
                self.logger.info(f"✅ Gerät gefunden: {device_name} ({device['id']})")
                self.device_id = device["id"]
                return

        self.logger.error("❌ Kein passendes Gerät gefunden!")

    @spotify_api_call
    def get_available_devices(self):
        devices = self.client.devices()
        return devices.get("devices", [])

    def _ensure_device_connection(self):
        if not self.device_id:
            self.set_device_id(self.device_name)
            return bool(self.device_id)
        return True

    @spotify_api_call
    def search_track(self, query):
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
        track_uri = self.search_track(query)
        if track_uri:
            self.client.start_playback(device_id=self.device_id, uris=[track_uri])
            self.logger.info("🎶 Song wird abgespielt!")
            return True
        else:
            self.logger.info("❌ Song konnte nicht abgespielt werden!")
            return False

    @spotify_api_call
    def convert_to_uri(self, identifier):
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
    def set_volume(self, volume) -> bool:
        volume = max(0, min(100, volume))
        self.client.volume(volume, device_id=self.device_id)
        self.logger.info(f"🔊 Lautstärke auf {volume}% gesetzt")
        return True

    @spotify_api_call
    def next_track(self) -> bool:
        self.client.next_track(device_id=self.device_id)
        self.logger.info("⏭️ Nächster Track")
        return True

    @spotify_api_call
    def previous_track(self) -> bool:
        self.client.previous_track(device_id=self.device_id)
        self.logger.info("⏮️ Vorheriger Track")
        return True

    @spotify_api_call
    def pause_playback(self) -> bool:
        self.client.pause_playback(device_id=self.device_id)
        self.logger.info("⏸️ Wiedergabe pausiert")
        return True

    @spotify_api_call
    def resume_playback(self) -> bool:
        self.client.start_playback(device_id=self.device_id)
        self.logger.info("▶️ Wiedergabe fortgesetzt")
        return True

if __name__ == "__main__":
    spotify_player = SpotifyPlayer()
    devices = spotify_player.get_available_devices()
    print("Verfügbare Geräte:")
    for device in devices:
        print(f"- {device['name']} ({device['id']})")

    spotify_player.play_track("Lichter aus Makko")


