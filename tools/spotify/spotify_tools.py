import asyncio
from typing import Literal, Optional

from langchain.tools import tool

from tools.spotify.spotify_device_manager import SpotifyDeviceManager
from tools.spotify.spotify_player import SpotifyPlayer

# Direktes Erstellen der Objekte ohne Controller-Wrapper
player = SpotifyPlayer()
device_manager = SpotifyDeviceManager()


@tool
async def spotify_set_volume(volume: int) -> str:
    """Ändert die Lautstärke des aktuellen Spotify-Players auf einen bestimmten Wert.

    Args:
        volume: Lautstärke in Prozent (0-100)
    """
    if not 0 <= volume <= 100:
        return "Fehler: Die Lautstärke muss zwischen 0 und 100 liegen."

    try:
        player.set_volume(volume)
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
            result = player.pause_playback()
            return "Wiedergabe pausiert." if result else "Konnte Wiedergabe nicht pausieren."
        elif action == "resume":
            result = player.resume_playback()
            return "Wiedergabe fortgesetzt." if result else "Konnte Wiedergabe nicht fortsetzen."
        else:
            return f"Ungültige Aktion: {action}. Verwende 'pause' oder 'resume'."
    except Exception as e:
        return f"Fehler bei der Wiedergabesteuerung: {str(e)}"


@tool
async def spotify_play_track(query: str) -> str:
    """Spielt einen bestimmten Song auf Spotify ab.

    Args:
        query: Suchbegriff oder Spotify-URI des Tracks
    """
    try:
        result = player.play_track(query)
        return f"🎵 Spiele Track '{query}' ab." if result else f"Konnte Track '{query}' nicht abspielen."
    except Exception as e:
        return f"Fehler beim Abspielen des Tracks: {str(e)}"


@tool
async def spotify_next_track() -> str:
    """Springt zum nächsten Song in der aktuellen Wiedergabe."""
    try:
        result = player.next_track()
        return "⏭️ Nächster Song abgespielt." if result else "Konnte nicht zum nächsten Song wechseln."
    except Exception as e:
        return f"Fehler beim Wechseln zum nächsten Song: {str(e)}"


@tool
async def spotify_previous_track() -> str:
    """Springt zum vorherigen Song in der aktuellen Wiedergabe."""
    try:
        result = player.previous_track()
        return "⏮️ Vorheriger Song abgespielt." if result else "Konnte nicht zum vorherigen Song wechseln."
    except Exception as e:
        return f"Fehler beim Wechseln zum vorherigen Song: {str(e)}"


@tool
async def spotify_get_active_devices() -> str:
    """Liefert eine Liste aller aktuell verbundenen Spotify-Geräte."""
    try:
        devices = device_manager.get_available_devices()
        if isinstance(devices, dict):
            device_names = list(devices.keys())
        else:  # Falls es eine Liste von Geräten ist
            device_names = [device.get('name', 'Unbekannt') for device in devices]
            
        return (
            f"📱 Verfügbare Geräte: {', '.join(device_names)}"
            if device_names
            else "❌ Keine verfügbaren Geräte gefunden."
        )
    except Exception as e:
        return f"Fehler beim Abrufen der Geräte: {str(e)}"


@tool
async def spotify_switch_device(device_name: str) -> str:
    """Wechselt das aktive Spotify-Gerät zu einem angegebenen Namen.

    Args:
        device_name: Der Name des Geräts, auf das gewechselt werden soll
    """
    try:
        result = device_manager.switch_device(device_name)
        return f"Zu '{device_name}' gewechselt." if result else f"❌ Konnte nicht zu '{device_name}' wechseln."
    except Exception as e:
        return f"Fehler beim Wechseln des Geräts: {str(e)}"


@tool
async def spotify_start_concentration_phase(playlist_type: Optional[str] = None) -> str:
    """Startet eine Konzentrations-Playlist.
    
    Args:
        playlist_type: Optionaler Typ der Playlist (z.B. 'WHITE_NOISE', 'FOCUS', etc.)
    """
    try:
        result = player.start_concentration_phase(playlist_type)
        return f"Konzentrationsmodus gestartet: {result}" if result else "Konnte Konzentrationsmodus nicht starten."
    except Exception as e:
        return f"Fehler beim Starten des Konzentrationsmodus: {str(e)}"


@tool
async def spotify_start_evening_phase(playlist_type: Optional[str] = None) -> str:
    """Startet eine Abend-Playlist zum Entspannen.
    
    Args:
        playlist_type: Optionaler Typ der Playlist
    """
    try:
        result = player.start_evening_phase(playlist_type)
        return f"Abendmodus gestartet: {result}" if result else "Konnte Abendmodus nicht starten."
    except Exception as e:
        return f"Fehler beim Starten des Abendmodus: {str(e)}"


def get_spotify_tools():
    return [
        spotify_set_volume,
        spotify_playback_control,
        spotify_play_track,
        spotify_next_track,
        spotify_previous_track,
        spotify_get_active_devices,
        spotify_switch_device,
        spotify_start_concentration_phase,
        spotify_start_evening_phase,
    ]