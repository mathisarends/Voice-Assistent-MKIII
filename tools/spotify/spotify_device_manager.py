from tools.spotify.spotify_api_call_wrapper import spotify_api_call
from tools.spotify.spotify_player import SpotifyClient
from util.loggin_mixin import LoggingMixin


class SpotifyDeviceManager(LoggingMixin):
    def __init__(self):
        self.client = SpotifyClient().api
        self.devices = self.get_available_devices()
        self.active_device = self.find_active_device()

    def find_active_device(self):
        """Findet das aktuell aktive Gerät."""
        for device in self.devices.values():
            if device["is_active"]:
                return device
        return None

    @spotify_api_call
    def get_available_devices(self):
        """Holt alle verfügbaren Spotify-Geräte und speichert sie."""
        devices = self.client.devices().get("devices", [])
        return {device["name"]: device for device in devices}
#

    @spotify_api_call
    def switch_device(self, device_name):
        """Wechselt das aktive Gerät und setzt die Wiedergabe fort, falls möglich."""
        if device_name in self.devices:
            device_id = self.devices[device_name]["id"]
            self.client.transfer_playback(device_id=device_id, force_play=False)
            self.active_device = self.devices[device_name]

            self.client.start_playback(device_id=device_id)
            self.logger.info(f"▶️ Wiedergabe fortgesetzt auf: {device_name}")
            
            return True
        else:
            self.logger.info(
                f"❌ Gerät '{device_name}' nicht gefunden. Verfügbare Geräte: {', '.join(self.devices.keys())}"
            )
            return False

    @spotify_api_call
    def refresh_devices(self):
        """Aktualisiert die Liste der verfügbaren Geräte."""
        self.devices = self.get_available_devices()
        self.active_device = self.find_active_device()
        return True