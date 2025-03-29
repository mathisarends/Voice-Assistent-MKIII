from typing import Literal

from langchain.tools import tool

from audio.workflow_audio_response_manager import WorkflowAudioResponseManager
from integrations.spotify.spotify_api import SpotifyPlaybackController

# Konstanten für die Antworten
# Konstanten für die Antworten
VOLUME_SET_SUCCESS = "Lautstärke auf {volume}% gesetzt."
VOLUME_ERROR_RANGE = "Fehler: Die Lautstärke muss zwischen 0 und 100 liegen."
PLAYBACK_PAUSED = "Wiedergabe pausiert."
PLAYBACK_RESUMED = "Wiedergabe fortgesetzt."
PLAYBACK_CONTROL_ERROR = "Ungültige Aktion: {action}. Verwende 'pause' oder 'resume'."
TRACK_PLAY_SUCCESS = "Spiele Track '{query}' ab."
TRACK_PLAY_ERROR = "Konnte Track '{query}' nicht abspielen."
NEXT_TRACK_SUCCESS = "Nächster Song abgespielt."
NEXT_TRACK_ERROR = "Konnte nicht zum nächsten Song wechseln."
PREV_TRACK_SUCCESS = "Vorheriger Song abgespielt."
PREV_TRACK_ERROR = "Konnte nicht zum vorherigen Song wechseln."
DEVICES_LIST = "Verfügbare Geräte: {devices}"
DEVICES_EMPTY = "Keine verfügbaren Geräte gefunden."
DEVICE_SWITCH_SUCCESS = "Zu '{device_name}' gewechselt."
DEVICE_SWITCH_ERROR = "Konnte nicht zu '{device_name}' wechseln. Prüfe verfügbare Geräte mit spotify_get_active_devices()."

spotify_playback_controller = SpotifyPlaybackController()

audio_manager = WorkflowAudioResponseManager(
    category="spotify_responses",
)

@tool
async def spotify_set_volume(volume: int) -> str:
    """Ändert die Lautstärke des aktuellen Spotify-Players auf einen bestimmten Wert.

    Args:
        volume: Lautstärke in Prozent (0-100)
    """
    if not 0 <= volume <= 100:
        return audio_manager.respond_with_audio(VOLUME_ERROR_RANGE)

    try:
        spotify_playback_controller.set_volume(volume)
        response = VOLUME_SET_SUCCESS.format(volume=volume)
        return audio_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler beim Ändern der Lautstärke: {str(e)}"
        return error_msg  # Fehlermeldungen nicht cachen


@tool
async def spotify_playback_control(action: Literal["pause", "resume"]) -> str:
    """Pausiert oder setzt die Wiedergabe von Spotify fort.

    Args:
        action: "pause" zum Pausieren oder "resume" zum Fortsetzen der Wiedergabe
    """
    try:
        if action == "pause":
            result = spotify_playback_controller.pause_playback()
            return audio_manager.respond_with_audio(PLAYBACK_PAUSED) if result else "Konnte Wiedergabe nicht pausieren."
        elif action == "resume":
            result = spotify_playback_controller.resume_playback()
            return audio_manager.respond_with_audio(PLAYBACK_RESUMED) if result else "Konnte Wiedergabe nicht fortsetzen."
        else:
            response = PLAYBACK_CONTROL_ERROR.format(action=action)
            return audio_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler bei der Wiedergabesteuerung: {str(e)}"
        return error_msg


@tool
async def spotify_play_track(query: str) -> str:
    """Spielt einen bestimmten Song auf Spotify ab.

    Args:
        query: Suchbegriff oder Spotify-URI des Tracks
    """
    try:
        result = spotify_playback_controller.play_track(query)
        if result:
            response = TRACK_PLAY_SUCCESS.format(query=query)
            return audio_manager.respond_with_audio(response)
        else:
            response = TRACK_PLAY_ERROR.format(query=query)
            return audio_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler beim Abspielen des Tracks: {str(e)}"
        return error_msg


@tool
async def spotify_next_track() -> str:
    """Springt zum nächsten Song in der aktuellen Wiedergabe."""
    try:
        result = spotify_playback_controller.next_track()
        if result:
            return audio_manager.respond_with_audio(NEXT_TRACK_SUCCESS)
        else:
            return audio_manager.respond_with_audio(NEXT_TRACK_ERROR)
    except Exception as e:
        error_msg = f"Fehler beim Wechseln zum nächsten Song: {str(e)}"
        return error_msg


@tool
async def spotify_previous_track() -> str:
    """Springt zum vorherigen Song in der aktuellen Wiedergabe."""
    try:
        result = spotify_playback_controller.previous_track()
        if result:
            return audio_manager.respond_with_audio(PREV_TRACK_SUCCESS)
        else:
            return audio_manager.respond_with_audio(PREV_TRACK_ERROR)
    except Exception as e:
        error_msg = f"Fehler beim Wechseln zum vorherigen Song: {str(e)}"
        return error_msg


@tool
async def spotify_get_active_devices() -> str:
    """Liefert eine Liste aller aktuell verbundenen Spotify-Geräte.
    
    Diese Funktion sollte vor spotify_switch_device() aufgerufen werden,
    um zu prüfen, welche Geräte verfügbar sind.
    """
    try:
        devices = spotify_playback_controller.get_available_devices()
        if isinstance(devices, dict):
            device_names = list(devices.keys())
        else:  # Falls es eine Liste von Geräten ist
            device_names = [device.get('name', 'Unbekannt') for device in devices]
            
        if device_names:
            response = DEVICES_LIST.format(devices=', '.join(device_names))
            return response
        
        return audio_manager.respond_with_audio(DEVICES_EMPTY)
    
    except Exception as e:
        error_msg = f"Fehler beim Abrufen der Geräte: {str(e)}"
        return error_msg


@tool
async def spotify_switch_device(device_name: str) -> str:
    """Wechselt das aktive Spotify-Gerät zu einem angegebenen Namen.
    
    WICHTIG: Rufe zuerst spotify_get_active_devices() auf, um
    zu sehen, welche Geräte verfügbar sind, bevor du versuchst,
    zu einem Gerät zu wechseln.

    Args:
        device_name: Der Name des Geräts, auf das gewechselt werden soll
    """
    try:
        result = spotify_playback_controller.switch_device(device_name)
        if result:
            response = DEVICE_SWITCH_SUCCESS.format(device_name=device_name)
            return response
        
        response = DEVICE_SWITCH_ERROR.format(device_name=device_name)
        return audio_manager.respond_with_audio(response)
    
    except Exception as e:
        error_msg = f"❌ Fehler beim Wechseln des Geräts: {str(e)}"
        return error_msg


def get_spotify_tools():
    return [
        spotify_set_volume,
        spotify_playback_control,
        spotify_play_track,
        spotify_next_track,
        spotify_previous_track,
        spotify_get_active_devices,
        spotify_switch_device,
    ]