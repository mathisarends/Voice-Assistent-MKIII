import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import random
from audio.spotify.playlist_config import CONCENTRATION_PLAYLISTS

# Diesen Player hier beef up mit Algorithmischen Empfehlungen:
class SpotifyPlayer:
    def __init__(self, device_name="MATHISPC"):
        """Initialisiert die Spotify API und wählt das gewünschte Gerät aus."""
        load_dotenv()
        
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri="http://localhost:8080",
            scope="user-modify-playback-state,user-read-playback-state"
        ))
            
        self.device_name = device_name
        self.device_id = None
        self.set_device_id(self.device_name)
    
    def set_device_id(self, device_name):
        """Sucht nach einem Spotify-Gerät anhand des Namens und gibt die ID zurück."""
        devices = self.sp.devices()
        
        for device in devices.get("devices", []):
            if device["name"] == device_name:
                print(f"✅ Gerät gefunden: {device_name} ({device['id']})")
                self.device_id = device["id"]
                return
        
        print("❌ Kein passendes Gerät gefunden!")
    
    def search_track(self, query):
        """Sucht einen Song bei Spotify und gibt die Track-URI zurück."""
        results = self.sp.search(q=query, type="track", limit=1)
        
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            print(f"🎵 Gefunden: {track['name']} - {track['artists'][0]['name']}")
            return track["uri"]
                
        print("❌ Kein Song gefunden!")
        return None
    
    def play_track(self, query):
        """Sucht einen Song und spielt ihn ab, falls ein Gerät vorhanden ist."""
        if not self.device_id:
            self.set_device_id(self.device_name)
            if not self.device_id:
                return
        
        track_uri = self.search_track(query)
        if track_uri:
            self.sp.start_playback(device_id=self.device_id, uris=[track_uri])
            print("🎶 Song wird abgespielt!")
        else:
            print("❌ Song konnte nicht abgespielt werden!")
                
    def play_playlist(self, playlist_identifier):
        """
        Spielt eine Playlist ab.
        playlist_identifier kann eine Spotify-URI oder eine Web-URL sein.
        """
        if not self.device_id:
            self.set_device_id(self.device_name)
            if not self.device_id:
                return
        
        # Konvertiere URL zu URI falls nötig
        playlist_uri = self.convert_to_uri(playlist_identifier)
        
        if playlist_uri:
            try:
                self.sp.start_playback(device_id=self.device_id, context_uri=playlist_uri)
                # Hole Playlist-Name für besseres Feedback
                playlist_id = playlist_uri.split(":")[-1]
                try:
                    playlist_info = self.sp.playlist(playlist_id)
                    playlist_name = playlist_info["name"]
                    print(f"📂 Playlist wird abgespielt: {playlist_name}")
                except:
                    print(f"📂 Playlist wird abgespielt: {playlist_uri}")
            except spotipy.exceptions.SpotifyException as e:
                print(f"❌ Fehler beim Abspielen der Playlist: {e}")
        else:
            print("❌ Ungültige Playlist-URL oder URI")
    
    def set_volume(self, volume):
        """Setzt die Lautstärke (0-100%)"""
        if not self.device_id:
            self.set_device_id(self.device_name)
            if not self.device_id:
                return
        
        volume = max(0, min(100, volume))
        self.sp.volume(volume, device_id=self.device_id)
        print(f"🔊 Lautstärke auf {volume}% gesetzt")
    
    def convert_to_uri(self, identifier):
        """
        Konvertiert verschiedene Spotify-Identifikatoren in URIs.
        Unterstützt:
        - Spotify URIs (spotify:playlist:xxxx)
        - Spotify Web URLs (https://open.spotify.com/playlist/xxxx)
        - Spotify Web URLs mit Query-Parametern (https://open.spotify.com/playlist/xxxx?si=yyyy)
        """
        # Wenn es bereits eine URI ist
        if identifier.startswith("spotify:"):
            return identifier
        
        # Extrahiere ID aus URL
        patterns = {
            "playlist": r"open\.spotify\.com/playlist/([a-zA-Z0-9]+)",
            "track": r"open\.spotify\.com/track/([a-zA-Z0-9]+)",
            "album": r"open\.spotify\.com/album/([a-zA-Z0-9]+)"
        }
        
        for content_type, pattern in patterns.items():
            match = re.search(pattern, identifier)
            if match:
                content_id = match.group(1)
                return f"spotify:{content_type}:{content_id}"
        
        return None

    def start_concentration_phase(self, playlist_type=None):
        """
        Startet eine Konzentrations-Playlist und setzt die Lautstärke auf 40%.
        Verwendet immer das Gerät "MATHISPC".
        
        Args:
            playlist_type: Der Typ der Playlist ("WHITE_NOISE", "BROWN_NOISE", "BINAURAL_BEATS")
                          Wenn None, wird eine zufällige Playlist ausgewählt.
        
        Returns:
            str: Der verwendete Playlist-Typ oder None bei Fehler
        """
        # Stelle sicher, dass MATHISPC als Gerät verwendet wird
        if self.device_name != "MATHISPC":
            self.device_name = "MATHISPC"
            self.set_device_id(self.device_name)
        
        if not self.device_id:
            print("❌ Gerät MATHISPC nicht verfügbar - Konzentrationsphase kann nicht gestartet werden")
            return None
        
        self.set_volume(40)
        
        if playlist_type is None:
            playlist_type = random.choice(list(CONCENTRATION_PLAYLISTS.keys()))
        
        if playlist_type not in CONCENTRATION_PLAYLISTS:
            print(f"❌ Unbekannter Playlist-Typ: {playlist_type}")
            print(f"  Verfügbare Typen: {', '.join(CONCENTRATION_PLAYLISTS.keys())}")
            return None
        
        playlist_url = CONCENTRATION_PLAYLISTS[playlist_type]
        
        print(f"🧠 Starte Konzentrationsmodus mit Playlist-Typ: {playlist_type}")
        self.play_playlist(playlist_url)
        
        return playlist_type

    def next_track(self):
        """Wechselt zum nächsten Track in der Warteschlange."""
        if not self.device_id:
            self.set_device_id(self.device_name)
            if not self.device_id:
                return False
        try:
            self.sp.next_track(device_id=self.device_id)
            print("⏭️ Nächster Track")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Wechseln zum nächsten Track: {e}")
            return False
    
    def previous_track(self):
        """Wechselt zum vorherigen Track."""
        if not self.device_id:
            self.set_device_id(self.device_name)
            if not self.device_id:
                return False
        try:
            self.sp.previous_track(device_id=self.device_id)
            print("⏮️ Vorheriger Track")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Wechseln zum vorherigen Track: {e}")
            return False
    
    def pause_playback(self):
        """Pausiert die Wiedergabe."""
        if not self.device_id:
            self.set_device_id(self.device_name)
            if not self.device_id:
                return False
        try:
            self.sp.pause_playback(device_id=self.device_id)
            print("⏸️ Wiedergabe pausiert")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Pausieren: {e}")
            return False
    
    def resume_playback(self):
        """Setzt die Wiedergabe fort."""
        if not self.device_id:
            self.set_device_id(self.device_name)
            if not self.device_id:
                return False
        try:
            self.sp.start_playback(device_id=self.device_id)
            print("▶️ Wiedergabe fortgesetzt")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Fortsetzen der Wiedergabe: {e}")
            return False
    
    def get_current_track(self):
        """Gibt Informationen zum aktuell spielenden Track zurück."""
        try:
            current_playback = self.sp.current_playback()
            
            if current_playback and current_playback.get('item'):
                track = current_playback['item']
                artists = ", ".join([artist['name'] for artist in track['artists']])
                duration_ms = track['duration_ms']
                progress_ms = current_playback['progress_ms']
                
                duration_min = duration_ms // 60000
                duration_sec = (duration_ms % 60000) // 1000
                progress_min = progress_ms // 60000
                progress_sec = (progress_ms % 60000) // 1000
                
                is_playing = current_playback['is_playing']
                
                print(f"{'▶️' if is_playing else '⏸️'} {track['name']} - {artists}")
                print(f"   {progress_min}:{progress_sec:02d}/{duration_min}:{duration_sec:02d}")
                
                return {
                    'name': track['name'],
                    'artists': artists,
                    'duration_ms': duration_ms,
                    'progress_ms': progress_ms,
                    'is_playing': is_playing,
                    'album': track['album']['name'],
                    'uri': track['uri']
                }
            else:
                print("❌ Kein Track wird derzeit abgespielt")
                return None
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Abrufen des aktuellen Tracks: {e}")
            return None
