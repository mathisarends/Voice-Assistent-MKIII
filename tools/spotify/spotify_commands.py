from typing import Optional, Any
from tools.spotify.spotify_command import SpotifyCommand
from tools.spotify.spotify_player import SpotifyPlayer

class PlayTrackCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer, query: str) -> None:
        self.player: SpotifyPlayer = player
        self.query: str = query
    
    def execute(self) -> Optional[bool]:
        return self.player.play_track(self.query)


class PlayPlaylistCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer, playlist_identifier: str) -> None:
        self.player: SpotifyPlayer = player
        self.playlist_identifier: str = playlist_identifier
    
    def execute(self) -> Optional[bool]:
        return self.player.play_playlist(self.playlist_identifier)


class NextTrackCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer) -> None:
        self.player: SpotifyPlayer = player
    
    def execute(self) -> bool:
        return self.player.next_track()


class PreviousTrackCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer) -> None:
        self.player: SpotifyPlayer = player
    
    def execute(self) -> bool:
        return self.player.previous_track()


class PauseCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer) -> None:
        self.player: SpotifyPlayer = player
    
    def execute(self) -> bool:
        return self.player.pause_playback()


class ResumeCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer) -> None:
        self.player: SpotifyPlayer = player
    
    def execute(self) -> bool:
        return self.player.resume_playback()

class SetVolumeCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer, volume: int) -> None:
        self.player: SpotifyPlayer = player
        self.volume: int = volume
    
    def execute(self) -> Optional[bool]:
        return self.player.set_volume(self.volume)


class GetCurrentTrackCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer) -> None:
        self.player: SpotifyPlayer = player
    
    def execute(self) -> Optional[dict[str, Any]]:
        return self.player.get_current_track()


class StartConcentrationPhaseCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer, playlist_type: Optional[str] = None) -> None:
        self.player: SpotifyPlayer = player
        self.playlist_type: Optional[str] = playlist_type
    
    def execute(self) -> Optional[str]:
        return self.player.start_concentration_phase(self.playlist_type)
    
class StartEveningPhaseCommand(SpotifyCommand):
    def __init__(self, player: SpotifyPlayer, playlist_type: Optional[str] = None) -> None:
        self.player: SpotifyPlayer = player
        self.playlist_type: Optional[str] = playlist_type
    
    def execute(self) -> Optional[str]:
        return self.player.start_evening_phase(self.playlist_type)