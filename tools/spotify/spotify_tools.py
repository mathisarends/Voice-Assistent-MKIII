import asyncio
from typing import Literal, Optional
from langchain.tools import tool
from tools.spotify.spotify_controller import SpotifyController
from tools.spotify.spotify_device_manager import SpotifyDeviceManager
from tools.spotify.spotify_player import SpotifyPlayer

player = SpotifyPlayer()
device_manager = SpotifyDeviceManager()

controller = SpotifyController(player, device_manager)

@tool
async def spotify_set_volume(volume: int) -> str:
    """Ändert die Lautstärke des aktuellen Spotify-Players auf einen bestimmten Wert.
    
    Args:
        volume: Lautstärke in Prozent (0-100)
    """
    if not 0 <= volume <= 100:
        return "Fehler: Die Lautstärke muss zwischen 0 und 100 liegen."
    
    try:
        controller.set_volume(volume)
        return f"Lautstärke auf {volume}% gesetzt."
    except Exception as e:
        return f"Fehler beim Ändern der Lautstärke: {str(e)}"

@tool
async def spotify_playback_control(action: Literal["pause", "resume"]) -> str:
    """Pausiert oder setzt die Wiedergabe von Spotify fort.
    
    Args:
        action: "pause" zum Pausieren oder "resume" zum Fortsetzen der Wiedergabe
    """
    try:
        if action == "pause":
            controller.pause()
            return "Wiedergabe pausiert."
        elif action == "resume":
            controller.resume()
            return "Wiedergabe fortgesetzt."
        else:
            return f"Ungültige Aktion: {action}. Verwende 'pause' oder 'resume'."
    except Exception as e:
        return f"Fehler bei der Wiedergabesteuerung: {str(e)}"

@tool
async def spotify_track_info() -> str:
    """Ruft Informationen zum aktuell laufenden Song ab."""
    try:
        result = controller.current_track()
        return f"Aktueller Song: {result}"
    except Exception as e:
        return f"Fehler beim Abrufen des aktuellen Songs: {str(e)}"

@tool
async def spotify_play_playlist(playlist_identifier: str) -> str:
    """Spielt eine angegebene Spotify-Playlist ab.
    
    Args:
        playlist_identifier: Playlist-Name oder Spotify-URI
    """
    try:
        controller.play_playlist(playlist_identifier)
        return f"Playlist '{playlist_identifier}' gestartet."
    except Exception as e:
        return f"Fehler beim Abspielen der Playlist: {str(e)}"

@tool
async def spotify_play_track(query: str) -> str:
    """Spielt einen bestimmten Song auf Spotify ab.
    
    Args:
        query: Suchbegriff oder Spotify-URI des Tracks
    """
    try:
        controller.play_track(query)
        return f"🎵 Spiele Track '{query}' ab."
    except Exception as e:
        return f"Fehler beim Abspielen des Tracks: {str(e)}"

@tool
async def spotify_next_track() -> str:
    """Springt zum nächsten Song in der aktuellen Wiedergabe."""
    try:
        controller.next_track()
        return "⏭️ Nächster Song abgespielt."
    except Exception as e:
        return f"Fehler beim Wechseln zum nächsten Song: {str(e)}"

@tool
async def spotify_previous_track() -> str:
    """Springt zum vorherigen Song in der aktuellen Wiedergabe."""
    try:
        controller.previous_track()
        return "⏮️ Vorheriger Song abgespielt."
    except Exception as e:
        return f"Fehler beim Wechseln zum vorherigen Song: {str(e)}"

@tool
async def spotify_get_active_devices() -> str:
    """Liefert eine Liste aller aktuell verbundenen Spotify-Geräte."""
    try:
        devices = controller.get_active_devices()
        return f"📱 Verfügbare Geräte: {', '.join(devices.keys())}" if devices else "❌ Keine verfügbaren Geräte gefunden."
    except Exception as e:
        return f"Fehler beim Abrufen der Geräte: {str(e)}"

@tool
async def spotify_switch_device(device_name: str) -> str:
    """Wechselt das aktive Spotify-Gerät zu einem angegebenen Namen.
    
    Args:
        device_name: Der Name des Geräts, auf das gewechselt werden soll
    """
    try:
        result = controller.switch_device(device_name)
        return result if result else f"❌ Konnte nicht zu '{device_name}' wechseln."
    except Exception as e:
        return f"Fehler beim Wechseln des Geräts: {str(e)}"

@tool
async def spotify_start_concentration(playlist_type: Optional[str] = None) -> str:
    """Startet eine Konzentrations-Playlist für fokussiertes Arbeiten oder Lernen.
    
    Args:
        playlist_type: Typ der Playlist (falls nicht angegeben, wird eine zufällig gewählt)
    """
    try:
        result = controller.start_concentration_phase(playlist_type)
        return f"🧠 Konzentrationsmodus gestartet mit Playlist-Typ: {result}" if result else "❌ Konzentrationsmodus konnte nicht gestartet werden."
    except Exception as e:
        return f"Fehler beim Starten des Konzentrationsmodus: {str(e)}"

@tool
async def spotify_start_evening(playlist_type: Optional[str] = None) -> str:
    """Startet eine Playlist für den Abendmodus, um zu entspannen oder herunterzufahren.
    
    Args:
        playlist_type: Typ der Playlist (falls nicht angegeben, wird eine zufällig gewählt)
    """
    try:
        result = controller.start_evening_phase(playlist_type)
        return f"🌙 Abendmodus gestartet mit Playlist-Typ: {result}" if result else "❌ Abendmodus konnte nicht gestartet werden."
    except Exception as e:
        return f"Fehler beim Starten des Abendmodus: {str(e)}"

def get_spotify_tools():
    return [
        spotify_set_volume,
        spotify_playback_control,
        spotify_track_info,
        spotify_play_playlist,
        spotify_play_track,
        spotify_next_track,
        spotify_previous_track,
        spotify_get_active_devices,
        spotify_switch_device,
        spotify_start_concentration,
        spotify_start_evening
    ]