import os
import re
import random
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tools.spotify.playlist_config import CONCENTRATION_PLAYLISTS, EVENING_PLAYLISTS

class SpotifyClient:
    def __init__(self):
        load_dotenv()
        self.api = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri="http://localhost:8080",
            scope="user-modify-playback-state user-read-playback-state user-read-currently-playing streaming app-remote-control user-library-read user-library-modify user-read-private user-top-read"
            # cache_path=".cache"
        ))
class SpotifyPlayer:
    def __init__(self, device_name="MATHISPC"):
        self.client = SpotifyClient().api
        self.device_name = device_name
        self.device_id = None
        self.set_device_id(self.device_name)
    
    def set_device_id(self, device_name):
        devices = self.client.devices()
        
        for device in devices.get("devices", []):
            if device["name"] == device_name:
                print(f"✅ Gerät gefunden: {device_name} ({device['id']})")
                self.device_id = device["id"]
                return
        
        print("❌ Kein passendes Gerät gefunden!")
        
    def get_available_devices(self):
        devices = self.client.devices()
        return devices.get("devices", [])
    
    def _ensure_device_connection(self):
        if not self.device_id:
            self.set_device_id(self.device_name)
            return bool(self.device_id)
        return True
    
    def search_track(self, query):
        results = self.client.search(q=query, type="track", limit=5)
        
        if not results["tracks"]["items"]:
            print("❌ Kein Song gefunden!")
            return None
        
        tracks = results["tracks"]["items"]
        # Versuche, einen exakten Match des Künstlers zu finden
        # Wenn der Query einen Künstlernamen enthält (z.B. "Mr. Brightside The Killers")
        artist_keywords = query.lower().split()
        
        for track in tracks:
            track_artists = [artist["name"].lower() for artist in track["artists"]]
            if any(any(keyword in artist for keyword in artist_keywords) for artist in track_artists):
                print(f"🎵 Gefunden (Künstler-Match): {track['name']} - {track['artists'][0]['name']}")
                return track["uri"]
        
        track = tracks[0]
        print(f"🎵 Gefunden (Erstes Ergebnis): {track['name']} - {track['artists'][0]['name']}")
        return track["uri"]
    
    def play_track(self, query):
        if not self._ensure_device_connection():
            return
        
        track_uri = self.search_track(query)
        if track_uri:
            self.client.start_playback(device_id=self.device_id, uris=[track_uri])
            print("🎶 Song wird abgespielt!")
        else:
            print("❌ Song konnte nicht abgespielt werden!")
    
    def convert_to_uri(self, identifier):
        if identifier.startswith("spotify:"):
            return identifier
        
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
    
    def play_playlist(self, playlist_identifier):
        if not self._ensure_device_connection():
            return
        
        playlist_uri = self.convert_to_uri(playlist_identifier)
        
        if playlist_uri:
            try:
                self.client.start_playback(device_id=self.device_id, context_uri=playlist_uri)
                playlist_id = playlist_uri.split(":")[-1]
                try:
                    playlist_info = self.client.playlist(playlist_id)
                    playlist_name = playlist_info["name"]
                    print(f"📂 Playlist wird abgespielt: {playlist_name}")
                except:
                    print(f"📂 Playlist wird abgespielt: {playlist_uri}")
            except spotipy.exceptions.SpotifyException as e:
                print(f"❌ Fehler beim Abspielen der Playlist: {e}")
        else:
            print("❌ Ungültige Playlist-URL oder URI")
    
    def set_volume(self, volume):
        if not self._ensure_device_connection():
            return
        
        volume = max(0, min(100, volume))
        self.client.volume(volume, device_id=self.device_id)
        print(f"🔊 Lautstärke auf {volume}% gesetzt")
    
    def start_concentration_phase(self, playlist_type=None):
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
    
    def start_evening_phase(self, playlist_type=None):
        if not self._ensure_device_connection():
            print("❌ Gerät nicht verfügbar - Evening Mode kann nicht gestartet werden")
            return None
        
        self.set_volume(50)  # Für Abend etwas höhere Lautstärke als Konzentrationsmodus
        
        if playlist_type is None:
            playlist_type = random.choice(list(EVENING_PLAYLISTS.keys()))
        
        if playlist_type not in EVENING_PLAYLISTS:
            print(f"❌ Unbekannter Playlist-Typ: {playlist_type}")
            print(f"  Verfügbare Typen: {', '.join(EVENING_PLAYLISTS.keys())}")
            return None
        
        playlist_url = EVENING_PLAYLISTS[playlist_type]
        
        print(f"🌙 Starte Evening Mode mit Playlist-Typ: {playlist_type}")
        self.play_playlist(playlist_url)
        
        return playlist_type
    
    def next_track(self):
        if not self._ensure_device_connection():
            return False
        
        try:
            self.client.next_track(device_id=self.device_id)
            print("⏭️ Nächster Track")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Wechseln zum nächsten Track: {e}")
            return False
    
    def previous_track(self):
        if not self._ensure_device_connection():
            return False
        
        try:
            self.client.previous_track(device_id=self.device_id)
            print("⏮️ Vorheriger Track")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Wechseln zum vorherigen Track: {e}")
            return False
    
    def pause_playback(self):
        if not self._ensure_device_connection():
            return False
        
        try:
            self.client.pause_playback(device_id=self.device_id)
            print("⏸️ Wiedergabe pausiert")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Pausieren: {e}")
            return False
    
    def resume_playback(self):
        if not self._ensure_device_connection():
            return False
        
        try:
            self.client.start_playback(device_id=self.device_id)
            print("▶️ Wiedergabe fortgesetzt")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Fortsetzen der Wiedergabe: {e}")
            return False
    
    def get_current_track(self):
        try:
            current_playback = self.client.current_playback()
            
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
        
    def get_track_audio_features(self, track_uri=None):
        """
        Ruft die Audio-Features (Tempo, Lautstärke, Tonart, etc.) für den aktuellen oder einen bestimmten Track ab.
        
        Args:
            track_uri: Optional, URI des Tracks. Wenn None, wird der aktuelle Track verwendet.
            w
        Returns:
            Dictionary mit Audio-Features oder None wenn ein Fehler auftritt
        """
        try:
            if track_uri is None:
                current_track = self.get_current_track()
                if not current_track:
                    print("❌ Kein aktueller Track gefunden")
                    return None
                track_uri = current_track['uri']
            
            # Track-ID aus URI extrahieren
            track_id = track_uri.split(':')[-1]
            
            # Audio-Features abrufen
            features = self.client.audio_features(track_id)[0]
            
            if features:
                # Die wichtigsten Features formatieren und anzeigen
                print(f"🎵 Audio-Features für den Track:")
                print(f"   Tempo: {round(features['tempo'])} BPM")
                print(f"   Energie: {round(features['energy'] * 100)}%")
                print(f"   Tanzbarkeit: {round(features['danceability'] * 100)}%")
                print(f"   Akustik: {round(features['acousticness'] * 100)}%")
                print(f"   Instrumental: {round(features['instrumentalness'] * 100)}%")
                print(f"   Lautstärke: {features['loudness']} dB")
                print(f"   Stimmung (Valenz): {round(features['valence'] * 100)}%")
                
                return features
            else:
                print("❌ Keine Audio-Features gefunden")
                return None
                
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Abrufen der Audio-Features: {e}")
            return None

    def get_track_audio_analysis(self, track_uri=None):
        """
        Ruft die detaillierte Audio-Analyse für den aktuellen oder einen bestimmten Track ab.
        Diese enthält zeitgenaue Informationen über Takte, Segmente, Frequenzen etc.
        
        Args:
            track_uri: Optional, URI des Tracks. Wenn None, wird der aktuelle Track verwendet.
            
        Returns:
            Dictionary mit detaillierter Audio-Analyse oder None wenn ein Fehler auftritt
        """
        try:
            if track_uri is None:
                current_track = self.get_current_track()
                if not current_track:
                    print("❌ Kein aktueller Track gefunden")
                    return None
                track_uri = current_track['uri']
            
            # Track-ID aus URI extrahieren
            track_id = track_uri.split(':')[-1]
            
            # Detaillierte Audio-Analyse abrufen
            analysis = self.client.audio_analysis(track_id)
            
            if analysis:
                # Einige Basisinformationen anzeigen
                print(f"🔊 Audio-Analyse für den Track:")
                print(f"   Anzahl Takte: {len(analysis['bars'])}")
                print(f"   Anzahl Beats: {len(analysis['beats'])}")
                print(f"   Anzahl Segmente: {len(analysis['segments'])}")
                print(f"   Anzahl Sektionen: {len(analysis['sections'])}")
                
                # Beispiel für Sektionen-Analyse
                print(f"\n📊 Sektions-Übersicht:")
                for i, section in enumerate(analysis['sections'][:5]):  # Zeige nur die ersten 5 Sektionen
                    print(f"   Sektion {i+1}: Start {round(section['start'], 2)}s, Länge {round(section['duration'], 2)}s, " +
                        f"Tempo {round(section['tempo'])} BPM, Lautstärke {round(section['loudness'])} dB")
                
                if len(analysis['sections']) > 5:
                    print(f"   ... und {len(analysis['sections']) - 5} weitere Sektionen")
                
                return analysis
            else:
                print("❌ Keine Audio-Analyse gefunden")
                return None
                
        except spotipy.exceptions.SpotifyException as e:
            print(f"❌ Fehler beim Abrufen der Audio-Analyse: {e}")
            return None

    def get_frequency_spectrum(self, track_uri=None):
        """
        Extrahiert und bereitet die Frequenzspektrum-Daten aus der Audio-Analyse auf.
        
        Args:
            track_uri: Optional, URI des Tracks. Wenn None, wird der aktuelle Track verwendet.
            
        Returns:
            Dictionary mit aufbereiteten Frequenzspektrum-Daten oder None bei Fehler
        """
        analysis = self.get_track_audio_analysis(track_uri)
        if not analysis:
            return None
        
        # Frequenzbänder aus den Segmenten extrahieren
        segments = analysis['segments']
        
        # Durchschnittswerte für die Frequenzbänder berechnen
        avg_timbre = [0] * 12  # 12 Timbre-Koeffizienten
        for segment in segments:
            for i, timbre in enumerate(segment['timbre']):
                avg_timbre[i] += timbre
        
        # Durchschnitt berechnen
        if segments:
            avg_timbre = [t / len(segments) for t in avg_timbre]
        
        # Timbre beschreiben - dies sind die 12 Koeffizienten
        timbre_desc = [
            "Lautstärke",
            "Helligkeit",
            "Klangfarbe",
            "Attacke",
            "Decay",
            "Stärke der tiefen Frequenzen",
            "Stärke der mittleren Frequenzen",
            "Stärke der hohen Frequenzen",
            "Rauigkeit",
            "Harmonische vs. perkussive Anteile",
            "Perkussive Energie",
            "Harmonische Energie"
        ]
        
        # Ergebnisse formatieren
        freq_data = {}
        print("\n🎛️ Frequenzspektrum-Analyse:")
        for i, (desc, value) in enumerate(zip(timbre_desc, avg_timbre)):
            normalized = (value + 100) / 200  # Normalisierung auf 0-1 (Werte sind typischerweise zwischen -100 und +100)
            print(f"   {desc}: {round(normalized * 100)}%")
            freq_data[desc] = normalized
        
        return freq_data
       
if __name__ == "__main__":
    # Test der SpotifyPlayer-Instanz
    spotify_player = SpotifyPlayer()
    
    # Verfügbare Geräte anzeigen
    spotify_player.play_track("Lichter aus Makko")
    
    spotify_player.get_frequency_spectrum("spotify:track:5Z01UMMf7V1o0MzF86s6WJ")