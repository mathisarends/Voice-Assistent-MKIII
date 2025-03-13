class LightDevice:
    """Basis-Klasse für Lichtgeräte."""
    
    def __init__(self, device_id: str, name: str):
        self.device_id = device_id
        self.name = name
        self._is_on = False
        self._brightness = 100  # 0-100%
    
    def turn_on(self) -> None:
        """Schaltet das Licht ein."""
        self._is_on = True
        print(f"[MOCK] {self.name} ({self.device_id}) eingeschaltet")
    
    def turn_off(self) -> None:
        """Schaltet das Licht aus."""
        self._is_on = False
        print(f"[MOCK] {self.name} ({self.device_id}) ausgeschaltet")
    
    def set_brightness(self, brightness: int) -> None:
        """Stellt die Helligkeit ein (0-100%)."""
        if 0 <= brightness <= 100:
            self._brightness = brightness
            print(f"[MOCK] {self.name} ({self.device_id}) Helligkeit auf {brightness}% gesetzt")
        else:
            raise ValueError("Helligkeit muss zwischen 0 und 100 liegen")
    
    def get_status(self) -> dict:
        """Gibt den aktuellen Status zurück."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "is_on": self._is_on,
            "brightness": self._brightness
        }