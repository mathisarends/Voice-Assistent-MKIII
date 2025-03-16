import asyncio
from langchain.tools import BaseTool
from typing import Literal, Type, Optional
from pydantic import BaseModel, Field
from tools.spotify.spotify_device_manager import SpotifyDeviceManager
from tools.spotify.spotify_player import SpotifyPlayer
from tools.spotify.spotify_commands import GetCurrentTrackCommand, NextTrackCommand, PauseCommand, PlayPlaylistCommand, PreviousTrackCommand, ResumeCommand, SetVolumeCommand

class SpotifyVolumeInput(BaseModel):
    """Eingabemodell für die Lautstärkeregelung."""
    volume: int = Field(..., ge=0, le=100, description="Lautstärke in Prozent (0-100)")

class SpotifyVolumeTool(BaseTool):
    """Setzt die Lautstärke des Spotify-Players."""
    
    name: str = "spotify_set_volume"
    description: str = "Ändert die Lautstärke des aktuellen Spotify-Players auf einen bestimmten Wert (0-100%)."
    args_schema: Type[BaseModel] = SpotifyVolumeInput

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    def _run(self, volume: int) -> str:
        return asyncio.run(self._arun(volume))

    async def _arun(self, volume: int) -> str:
        try:
            await SetVolumeCommand(self.player, volume).execute()
            return f"Lautstärke auf {volume}% gesetzt."
        except Exception as e:
            return f"Fehler beim Ändern der Lautstärke: {str(e)}"
        
    
        
class SpotifyPlaybackControlInput(BaseModel):
    """Eingabemodell für die Wiedergabesteuerung."""
    action: Literal["pause", "resume"] = Field(..., description="Pause oder Wiedergabe fortsetzen.")

class SpotifyPlaybackControlTool(BaseTool):
    """Steuert die Wiedergabe von Spotify (Pause/Fortsetzen)."""
    
    name: str = "spotify_playback_control"
    description: str = "Pausiert oder setzt die Wiedergabe von Spotify fort."
    args_schema: Type[BaseModel] = SpotifyPlaybackControlInput

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    def _run(self, action: str) -> str:
        return asyncio.run(self._arun(action))

    async def _arun(self, action: str) -> str:
        try:
            if action == "pause":
                result = await PauseCommand(self.player).execute()
                return "Wiedergabe pausiert."
            elif action == "resume":
                result = await ResumeCommand(self.player).execute()
                return "Wiedergabe fortgesetzt."
        except Exception as e:
            return f"Fehler bei der Wiedergabesteuerung: {str(e)}"
        

class SpotifyTrackInfoTool(BaseTool):
    """Gibt den aktuell abgespielten Spotify-Track zurück."""
    
    name: str = "spotify_track_info"
    description: str = "Ruft Informationen zum aktuell laufenden Song ab."

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    def _run(self) -> str:
        return asyncio.run(self._arun())

    async def _arun(self) -> str:
        try:
            result = await GetCurrentTrackCommand(self.player).execute()
            return f"Aktueller Song: {result}"
        except Exception as e:
            return f"Fehler beim Abrufen des aktuellen Songs: {str(e)}"
        
        
        
class SpotifyPlaylistInput(BaseModel):
    """Eingabemodell für das Abspielen einer Playlist."""
    playlist_identifier: str = Field(..., description="Playlist-Name oder Spotify-URI.")

class SpotifyPlaylistTool(BaseTool):
    """Startet eine bestimmte Spotify-Playlist."""
    
    name: str = "spotify_play_playlist"
    description: str = "Spielt eine angegebene Spotify-Playlist ab."
    args_schema: Type[BaseModel] = SpotifyPlaylistInput

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    def _run(self, playlist_identifier: str) -> str:
        return asyncio.run(self._arun(playlist_identifier))

    async def _arun(self, playlist_identifier: str) -> str:
        try:
            await PlayPlaylistCommand(self.player, playlist_identifier).execute()
            return f"Playlist '{playlist_identifier}' gestartet."
        except Exception as e:
            return f"Fehler beim Abspielen der Playlist: {str(e)}"
        
class SpotifyNextTrackTool(BaseTool):
    name: str = "spotify_next_track"
    description: str = "Springt zum nächsten Song in der aktuellen Wiedergabe."

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    def _run(self) -> str:
        return asyncio.run(self._arun())

    async def _arun(self) -> str:
        try:
            await NextTrackCommand(self.player).execute()
            return "⏭️ Nächster Song abgespielt."
        except Exception as e:
            return f"Fehler beim Wechseln zum nächsten Song: {str(e)}"


class SpotifyPreviousTrackTool(BaseTool):
    """Springt zum vorherigen Track in der Spotify-Wiedergabe."""
    
    name: str = "spotify_previous_track"
    description: str = "Springt zum vorherigen Song in der aktuellen Wiedergabe."

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    def _run(self) -> str:
        return asyncio.run(self._arun())

    async def _arun(self) -> str:
        try:
            await PreviousTrackCommand(self.player).execute()
            return "⏮️ Vorheriger Song abgespielt."
        except Exception as e:
            return f"Fehler beim Wechseln zum vorherigen Song: {str(e)}"
        
class SpotifyGetActiveDevicesTool(BaseTool):
    """Gibt eine Liste aller verfügbaren Spotify-Geräte zurück."""
    
    name: str = "spotify_get_active_devices"
    description: str = "Liefert eine Liste aller aktuell verbundenen Spotify-Geräte."

    device_manager: SpotifyDeviceManager = Field(default_factory=SpotifyDeviceManager, exclude=True)

    def _run(self) -> str:
        return asyncio.run(self._arun())

    async def _arun(self) -> str:
        try:
            devices = self.device_manager.get_available_devices()
            return f"📱 Verfügbare Geräte: {', '.join(devices.keys())}" if devices else "❌ Keine verfügbaren Geräte gefunden."
        except Exception as e:
            return f"Fehler beim Abrufen der Geräte: {str(e)}"


class SpotifySwitchDeviceTool(BaseTool):
    """Wechselt das aktive Spotify-Wiedergabegerät."""
    
    name: str = "spotify_switch_device"
    description: str = "Wechselt das aktive Spotify-Gerät zu einem angegebenen Namen."

    device_manager: SpotifyDeviceManager = Field(default_factory=SpotifyDeviceManager, exclude=True)

    class SwitchDeviceInput(BaseModel):
        device_name: str = Field(..., description="Der Name des Geräts, auf das gewechselt werden soll.")

    args_schema: Type[BaseModel] = SwitchDeviceInput

    def _run(self, device_name: str) -> str:
        return asyncio.run(self._arun(device_name))

    async def _arun(self, device_name: str) -> str:
        try:
            result = self.device_manager.switch_device(device_name)
            return result if result else f"❌ Konnte nicht zu '{device_name}' wechseln."
        except Exception as e:
            return f"Fehler beim Wechseln des Geräts: {str(e)}"
        
class SpotifyStartConcentrationTool(BaseTool):
    """Startet den Konzentrationsmodus mit einer spezifischen oder zufälligen Playlist."""
    
    name: str = "spotify_start_concentration"
    description: str = "Startet eine Konzentrations-Playlist für fokussiertes Arbeiten oder Lernen."

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    class ConcentrationInput(BaseModel):
        playlist_type: Optional[str] = Field(None, description="Typ der Playlist (falls nicht angegeben, wird eine zufällig gewählt).")

    args_schema: Type[BaseModel] = ConcentrationInput

    def _run(self, playlist_type: Optional[str] = None) -> str:
        return asyncio.run(self._arun(playlist_type))

    async def _arun(self, playlist_type: Optional[str] = None) -> str:
        try:
            result = self.player.start_concentration_phase(playlist_type)
            return f"🧠 Konzentrationsmodus gestartet mit Playlist-Typ: {result}" if result else "❌ Konzentrationsmodus konnte nicht gestartet werden."
        except Exception as e:
            return f"Fehler beim Starten des Konzentrationsmodus: {str(e)}"


class SpotifyStartEveningTool(BaseTool):
    """Startet eine Abend-Playlist zur Entspannung."""
    
    name: str = "spotify_start_evening"
    description: str = "Startet eine Playlist für den Abendmodus, um zu entspannen oder herunterzufahren."

    player: SpotifyPlayer = Field(default_factory=SpotifyPlayer, exclude=True)

    class EveningInput(BaseModel):
        playlist_type: Optional[str] = Field(None, description="Typ der Playlist (falls nicht angegeben, wird eine zufällig gewählt).")

    args_schema: Type[BaseModel] = EveningInput

    def _run(self, playlist_type: Optional[str] = None) -> str:
        return asyncio.run(self._arun(playlist_type))

    async def _arun(self, playlist_type: Optional[str] = None) -> str:
        try:
            result = self.player.start_evening_phase(playlist_type)
            return f"🌙 Abendmodus gestartet mit Playlist-Typ: {result}" if result else "❌ Abendmodus konnte nicht gestartet werden."
        except Exception as e:
            return f"Fehler beim Starten des Abendmodus: {str(e)}"



def get_spotify_tools():
    return [
        SpotifyVolumeTool(),
        SpotifyPlaybackControlTool(),
        SpotifyTrackInfoTool(),
        SpotifyPlaylistTool(),
        SpotifyNextTrackTool(),
        SpotifyPreviousTrackTool(),
        SpotifyGetActiveDevicesTool(),
        SpotifySwitchDeviceTool(),
        SpotifyStartConcentrationTool(),
        SpotifyStartEveningTool()
    ]     