from tools.spotify.spotify_command import SpotifyCommand
from tools.spotify.spotify_commands import GetActiveDevicesCommand, GetCurrentTrackCommand, NextTrackCommand, PauseCommand, PlayPlaylistCommand, PlayTrackCommand, PreviousTrackCommand, ResumeCommand, SetVolumeCommand, StartConcentrationPhaseCommand, StartEveningPhaseCommand, SwitchDeviceCommand
from tools.spotify.spotify_device_manager import SpotifyDeviceManager
from tools.spotify.spotify_player import SpotifyPlayer

class SpotifyController:
    def __init__(self, player: SpotifyPlayer, device_manager: SpotifyDeviceManager):
        self.player = player
        self.device_manager = device_manager
        self.history = [] 
    
    def execute_command(self, command: SpotifyCommand):
        result = command.execute()
        self.history.append(command)
        return result
    
    def play_track(self, query):
        return self.execute_command(PlayTrackCommand(self.player, query))
    
    def play_playlist(self, playlist_identifier):
        return self.execute_command(PlayPlaylistCommand(self.player, playlist_identifier))
    
    def next_track(self):
        return self.execute_command(NextTrackCommand(self.player))
    
    def previous_track(self):
        return self.execute_command(PreviousTrackCommand(self.player))
    
    def pause(self):
        return self.execute_command(PauseCommand(self.player))
    
    def resume(self):
        return self.execute_command(ResumeCommand(self.player))
    
    def set_volume(self, volume):
        return self.execute_command(SetVolumeCommand(self.player, volume))
    
    def current_track(self):
        return self.execute_command(GetCurrentTrackCommand(self.player))
    
    def start_concentration_phase(self, playlist_type=None):
        return self.execute_command(StartConcentrationPhaseCommand(self.player, playlist_type))
    
    def start_evening_phase(self, playlist_type=None):
        return self.execute_command(StartEveningPhaseCommand(self.player, playlist_type))
    
    def get_active_devices(self):
        return self.execute_command(GetActiveDevicesCommand(self.device_manager))

    def switch_device(self, device_name):
        return self.execute_command(SwitchDeviceCommand(self.device_manager, device_name))

if __name__ == "__main__":
    player = SpotifyPlayer()
    device_manager = SpotifyDeviceManager()
    
    controller = SpotifyController(player, device_manager)
    
    controller.start_evening_phase()
    
    input("Drücke Enter für nächsten Track...")
    controller.next_track()
    
    # Zeige aktuellen Track an
    input("Drücke Enter für Track-Info...")
    current = controller.current_track()
    
    # Pause
    input("Drücke Enter zum Pausieren...")
    controller.pause()
    
    # Fortsetzen
    input("Drücke Enter zum Fortsetzen...")
    controller.resume()
    
    # Konzentrationsmodus starten
    input("Drücke Enter für Konzentrationsmodus...")
    controller.start_concentration_phase("WHITE_NOISE")