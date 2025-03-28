import spotipy
from tools.spotify.spotify_player import SpotifyClient


class SpotifyDeviceManager:
    def __init__(self):
        self.client = SpotifyClient().api
        self.devices = self.get_available_devices()
        self.active_device = self.find_active_device()

    def get_available_devices(self):
        """Holt alle verfügbaren Spotify-Geräte und speichert sie."""
        devices = self.client.devices().get("devices", [])
        return {device["name"]: device for device in devices}

    def find_active_device(self):
        """Findet das aktuell aktive Gerät."""
        for device in self.devices.values():
            if device["is_active"]:
                return device
        return None

    def switch_device(self, device_name):
        """Wechselt das aktive Gerät und setzt die Wiedergabe fort, falls möglich."""
        if device_name in self.devices:
            device_id = self.devices[device_name]["id"]
            self.client.transfer_playback(device_id=device_id, force_play=False)
            self.active_device = self.devices[device_name]

            try:
                self.client.start_playback(device_id=device_id)
                print(f"▶️ Wiedergabe fortgesetzt auf: {device_name}")
            except spotipy.exceptions.SpotifyException as e:
                print(f"⚠️ Wiedergabe konnte nicht fortgesetzt werden: {e}")

            print(f"🔄 Gerät gewechselt zu: {device_name}")
            return True
        else:
            print(
                f"❌ Gerät '{device_name}' nicht gefunden. Verfügbare Geräte: {', '.join(self.devices.keys())}"
            )
            return False

    def print_devices(self):
        """Listet alle verfügbaren Geräte auf."""
        print("📱 Verfügbare Geräte:")
        for name, device in self.devices.items():
            status = "🟢 Aktiv" if device["is_active"] else "⚫ Inaktiv"
            print(
                f"- {name} ({device['type']}), Lautstärke: {device['volume_percent']}% {status}"
            )


# Testen der Geräteverwaltung
if __name__ == "__main__":
    device_manager = SpotifyDeviceManager()
    device_manager.print_devices()

    # Beispiel: Wechsel zum Pixel 8, falls vorhanden
    device_manager.switch_device("Pixel 8")
