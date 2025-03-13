from tools.lights.light_device import LightDevice

class RGBLedStrip(LightDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self._color = {"r": 255, "g": 255, "b": 255}  # Standard: Weiß
    
    def set_color(self, r: int, g: int, b: int) -> None:
        """Stellt die RGB-Farbe ein."""
        if all(0 <= c <= 255 for c in [r, g, b]):
            self._color = {"r": r, "g": g, "b": b}
            print(f"[MOCK] {self.name} ({self.device_id}) Farbe auf RGB({r},{g},{b}) gesetzt")
        else:
            raise ValueError("RGB-Werte müssen zwischen 0 und 255 liegen")
    
    def set_preset(self, preset: str) -> None:
        """Stellt ein Farbpreset ein."""
        presets = {
            "rot": {"r": 255, "g": 0, "b": 0},
            "grün": {"r": 0, "g": 255, "b": 0},
            "blau": {"r": 0, "g": 0, "b": 255},
            "warm": {"r": 255, "g": 200, "b": 100},
            "kalt": {"r": 200, "g": 220, "b": 255}
        }
        
        if preset.lower() in presets:
            color = presets[preset.lower()]
            self.set_color(color["r"], color["g"], color["b"])
        else:
            raise ValueError(f"Unbekanntes Preset: {preset}")
    
    def get_status(self) -> dict:
        """Überschreibt die Basisimplementierung um Farbinformationen hinzuzufügen."""
        status = super().get_status()
        status["color"] = self._color
        return status