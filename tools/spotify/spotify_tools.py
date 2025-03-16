import asyncio
from langchain.tools import BaseTool
from typing import Literal, Type
from pydantic import BaseModel, Field
from tools.spotify.spotify_player import SpotifyPlayer
from tools.spotify.spotify_commands import GetCurrentTrackCommand, PauseCommand, PlayPlaylistCommand, ResumeCommand, SetVolumeCommand

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
        
        
def get_spotify_tools():
    return [
        SpotifyVolumeTool(),
        SpotifyPlaybackControlTool(),
        SpotifyTrackInfoTool(),
        SpotifyPlaylistTool()
    ]