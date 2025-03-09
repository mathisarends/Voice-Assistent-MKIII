import subprocess

class VolumeControl:
    """Steuert die Systemlautstärke mit PulseAudio über `pactl`."""

    @staticmethod
    def get_volume() -> int:
        """Holt die aktuelle Lautstärke als Prozentwert (0-100%)."""
        result = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], capture_output=True, text=True)
        return int(result.stdout.split('/')[1].strip().replace('%', ''))

    @staticmethod
    def set_volume_level(level: int):
        """
        Setzt die Lautstärke auf eine Stufe von 1 bis 10.
        
        :param level: Lautstärkestufe (1 = 10%, 10 = 100%)
        """
        if not 1 <= level <= 10:
            raise ValueError("Lautstärkelevel muss zwischen 1 und 10 liegen.")
        volume = level * 10  # Umrechnung in Prozent
        VolumeControl.set_volume(volume)

    @staticmethod
    def set_volume(volume: int):
        """
        Setzt die Lautstärke direkt als Prozentwert (0-100%).
        
        :param volume: Lautstärke in Prozent (z. B. 50 für 50%)
        """
        if not 0 <= volume <= 100:
            raise ValueError("Lautstärke muss zwischen 0 und 100 liegen.")
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"])

    @staticmethod
    def increase_volume(step: int = 15):
        """Erhöht die Lautstärke um den angegebenen Schritt (Standard: 15%)."""
        current_volume = VolumeControl.get_volume()
        new_volume = min(100, current_volume + step)
        VolumeControl.set_volume(new_volume)

    @staticmethod
    def decrease_volume(step: int = 15):
        """Verringert die Lautstärke um den angegebenen Schritt (Standard: 15%)."""
        current_volume = VolumeControl.get_volume()
        new_volume = max(0, current_volume - step)
        VolumeControl.set_volume(new_volume)

    @staticmethod
    def mute():
        """Schaltet die Lautstärke stumm oder hebt die Stummschaltung auf."""
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])

if __name__ == "__main__":
    VolumeControl.mute()
    
    print(f"Aktuelle Lautstärke: {VolumeControl.get_volume()}%")

    VolumeControl.set_volume_level(5)
    print(f"Neue Lautstärke nach Stufenanpassung: {VolumeControl.get_volume()}%")

    VolumeControl.increase_volume()
    print(f"Neue Lautstärke nach Erhöhung: {VolumeControl.get_volume()}%")

    VolumeControl.decrease_volume()
    print(f"Neue Lautstärke nach Verringerung: {VolumeControl.get_volume()}%")