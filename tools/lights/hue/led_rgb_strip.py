from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import colorsys
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.light_device import LightDevice

@dataclass
class LightStatus:
    device_id: str
    name: str
    is_on: bool
    brightness: int
    color_rgb: Tuple[int, int, int]
    reachable: bool = True
    
    def __str__(self) -> str:
        """Menschenlesbare Darstellung des Status."""
        status = "AN" if self.is_on else "AUS"
        r, g, b = self.color_rgb
        return (
            f"{self.name} ({self.device_id}): {status}, "
            f"Helligkeit: {self.brightness}%, "
            f"Farbe: RGB({r},{g},{b})"
        )
    
    def as_dict(self) -> Dict[str, Any]:
        """Konvertiert den Status in ein Dictionary."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "is_on": self.is_on,
            "brightness": self.brightness,
            "color_rgb": self.color_rgb,
            "reachable": self.reachable
        }


class ColorPresets:
    # Grundfarben
    ROT = (255, 0, 0)
    GRÜN = (0, 255, 0)
    BLAU = (0, 0, 255)
    
    # Mischfarben
    GELB = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    CYAN = (0, 255, 255)
    
    # Weitere Farbtöne
    ORANGE = (255, 165, 0)
    PINK = (255, 192, 203)
    LILA = (128, 0, 128)
    TÜRKIS = (64, 224, 208)
    
    # Weiß und Grautöne
    WEISS = (255, 255, 255)
    WARMWEISS = (255, 223, 179)
    KALTWEISS = (240, 255, 255)
    
    # Stimmungen
    ENTSPANNUNG = (70, 130, 180)  # Steel Blue
    KONZENTRATION = (240, 248, 255)  # Alice Blue
    PARTY = (138, 43, 226)  # Blueviolet
    GEMÜTLICH = (210, 105, 30)  # Chocolate
    
    FARBEN = {
        "rot": ROT,
        "grün": GRÜN,
        "blau": BLAU,
        "gelb": GELB,
        "magenta": MAGENTA,
        "cyan": CYAN,
        "orange": ORANGE,
        "pink": PINK,
        "lila": LILA,
        "türkis": TÜRKIS,
        "weiss": WEISS,
        "weiß": WEISS,
        "warmweiss": WARMWEISS,
        "warmweiß": WARMWEISS,
        "kaltweiss": KALTWEISS,
        "kaltweiß": KALTWEISS,
        "entspannung": ENTSPANNUNG,
        "konzentration": KONZENTRATION,
        "party": PARTY,
        "gemütlich": GEMÜTLICH
    }
    
    @classmethod
    def get_color(cls, name: str) -> Optional[Tuple[int, int, int]]:
        """
        Gibt RGB-Werte für eine benannte Farbe zurück.
        
        Args:
            name: Name der Farbe (z.B. "rot", "grün", etc.)
            
        Returns:
            RGB-Tuple mit Werten von 0-255 oder None, wenn die Farbe nicht gefunden wurde
        """
        return cls.FARBEN.get(name.lower())
    
    @classmethod
    def list_colors(cls) -> List[str]:
        """Listet alle verfügbaren Farbnamen auf."""
        return list(cls.FARBEN.keys())


class RGBLightStrip(LightDevice):
    """Klasse für die Steuerung eines RGB LED-Strips über die Philips Hue Bridge."""

    def __init__(self, bridge: Bridge, device_id: str, name: str):
        """
        Initialisiert einen RGB LED-Strip.

        Args:
            bridge: Die Hue Bridge-Instanz zur Kommunikation
            device_id: Die ID des Geräts in der Hue Bridge
            name: Der Name des Geräts
        """
        super().__init__(device_id, name)
        self.bridge = bridge
        self._color: Tuple[int, int, int] = (255, 255, 255)
    
    @property
    def color(self) -> Tuple[int, int, int]:
        """Gibt die aktuelle RGB-Farbe zurück."""
        return self._color
    
    @color.setter
    def color(self, value: Tuple[int, int, int]) -> None:
        """Setzt die RGB-Farbe."""
        self._color = value
    
    @property
    def brightness(self) -> int:
        """Gibt die aktuelle Helligkeit (0-100%) zurück."""
        return self._brightness
    
    @brightness.setter
    def brightness(self, value: int) -> None:
        """Setzt die Helligkeit (0-100%)."""
        if 0 <= value <= 100:
            self._brightness = value
        else:
            raise ValueError("Helligkeit muss zwischen 0 und 100 liegen")
    
    async def initialize(self) -> None:
        """Initialisiert das Gerät mit seinen aktuellen Zuständen von der Bridge."""
        lights = await self.bridge.get_lights()
        if self.device_id in lights:
            light_data = lights[self.device_id]
            self.name = light_data.get("name", self.name)
            
            state = light_data.get("state", {})
            self.is_on = state.get("on", False)
            
            # Helligkeit von Hue (0-254) zu Prozent (0-100) konvertieren
            hue_bri = state.get("bri", 254)
            self.brightness = round(hue_bri / 254 * 100)
            
            # Farbe aus xy-Koordinaten extrahieren, falls vorhanden
            if "xy" in state and state.get("colormode") == "xy":
                self.color = self._xy_to_rgb(state["xy"][0], state["xy"][1], self.brightness)
        else:
            print(f"Warnung: Gerät mit ID {self.device_id} nicht in der Bridge gefunden")
    
    async def turn_on(self) -> List[Dict[str, Any]]:
        """
        Schaltet den LED-Strip ein.
        
        Returns:
            Die Antwort der Bridge
        """
        self.is_on = True
        return await self.bridge.set_light_state(self.device_id, {"on": True})
    
    async def turn_off(self) -> List[Dict[str, Any]]:
        """
        Schaltet den LED-Strip aus.
        
        Returns:
            Die Antwort der Bridge
        """
        self.is_on = False
        return await self.bridge.set_light_state(self.device_id, {"on": False})
    
    async def set_brightness(self, brightness: int) -> List[Dict[str, Any]]:
        """
        Stellt die Helligkeit ein (0-100%).
        
        Args:
            brightness: Helligkeitswert zwischen 0 und 100
            
        Returns:
            Die Antwort der Bridge
            
        Raises:
            ValueError: Wenn der Helligkeitswert außerhalb des gültigen Bereichs liegt
        """
        if 0 <= brightness <= 100:
            self.brightness = brightness
            # Umrechnung in Hue-Helligkeit (0-254)
            hue_brightness = round(brightness / 100 * 254)
            return await self.bridge.set_light_state(self.device_id, {"bri": hue_brightness})
        else:
            raise ValueError("Helligkeit muss zwischen 0 und 100 liegen")
    
    async def set_color_rgb(self, red: int, green: int, blue: int) -> List[Dict[str, Any]]:
        """
        Setzt die Farbe des LED-Strips über RGB-Werte.
        
        Args:
            red: Rotwert (0-255)
            green: Grünwert (0-255)
            blue: Blauwert (0-255)
            
        Returns:
            Die Antwort der Bridge
            
        Raises:
            ValueError: Wenn ein RGB-Wert außerhalb des gültigen Bereichs liegt
        """
        if not all(0 <= c <= 255 for c in (red, green, blue)):
            raise ValueError("RGB-Werte müssen zwischen 0 und 255 liegen")
        
        self.color = (red, green, blue)
        xy = self._rgb_to_xy(red, green, blue)
        
        return await self.bridge.set_light_state(self.device_id, {"xy": xy})
    
    async def set_color_preset(self, preset_name: str) -> List[Dict[str, Any]]:
        """
        Setzt die Farbe des LED-Strips über einen vordefinierten Farbnamen.
        
        Args:
            preset_name: Name der Farbe (z.B. "rot", "blau", "entspannung")
            
        Returns:
            Die Antwort der Bridge
            
        Raises:
            ValueError: Wenn der Farbname nicht gefunden wurde
        """
        rgb = ColorPresets.get_color(preset_name)
        if rgb is None:
            available_colors = ", ".join(ColorPresets.list_colors())
            raise ValueError(f"Unbekannte Farbe: '{preset_name}'. Verfügbare Farben: {available_colors}")
        
        r, g, b = rgb
        return await self.set_color_rgb(r, g, b)
    
    async def get_status(self) -> LightStatus:
        """
        Holt den aktuellen Status des LED-Strips von der Bridge.
        
        Returns:
            LightStatus-Objekt mit den aktuellen Gerätedaten
        """
        lights = await self.bridge.get_lights()
        if self.device_id in lights:
            light_data = lights[self.device_id]
            return LightStatus(
                device_id=self.device_id,
                name=light_data.get("name", self.name),
                is_on=light_data.get("state", {}).get("on", self.is_on),
                brightness=round(light_data.get("state", {}).get("bri", 254) / 254 * 100),
                color_rgb=self._get_current_rgb_from_bridge(light_data),
                reachable=light_data.get("state", {}).get("reachable", True)
            )
        
        return LightStatus(
            device_id=self.device_id,
            name=self.name,
            is_on=self.is_on,
            brightness=self.brightness,
            color_rgb=self.color,
            reachable=True  # Annahme: Lokal ist immer erreichbar
        )
    
    def get_available_color_presets(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Farbpresets zurück.
        
        Returns:
            Liste mit allen verfügbaren Farbnamen
        """
        return ColorPresets.list_colors()
    
    def _get_current_rgb_from_bridge(self, light_data: Dict[str, Any]) -> Tuple[int, int, int]:
        """
        Extrahiert die aktuelle RGB-Farbe aus den Bridge-Daten.
        
        Args:
            light_data: Die Daten des Lichts von der Bridge
            
        Returns:
            RGB-Tuple mit Werten von 0-255
        """
        state = light_data.get("state", {})
        colormode = state.get("colormode")
        
        if colormode == "xy" and "xy" in state:
            brightness = state.get("bri", 254)
            return self._xy_to_rgb(state["xy"][0], state["xy"][1], brightness / 254 * 100)
        elif colormode == "hs" and "hue" in state and "sat" in state:
            hue = state["hue"] / 65535 * 360
            sat = state["sat"] / 254 * 100
            val = state.get("bri", 254) / 254 * 100
            r, g, b = colorsys.hsv_to_rgb(hue/360, sat/100, val/100)
            return (int(r * 255), int(g * 255), int(b * 255))
        
        return self.color
    
    @staticmethod
    def _rgb_to_xy(red: int, green: int, blue: int) -> List[float]:
        """
        Konvertiert RGB-Farben in xy-Koordinaten für die Hue Bridge.
        
        Args:
            red: Rotwert (0-255)
            green: Grünwert (0-255)
            blue: Blauwert (0-255)
            
        Returns:
            Liste mit x- und y-Koordinaten [x, y]
        """
        # Normalisiere die RGB-Werte
        r = red / 255
        g = green / 255
        b = blue / 255
        
        # Gamma-Korrektur
        if r > 0.04045:
            r = ((r + 0.055) / 1.055) ** 2.4
        else:
            r = r / 12.92
            
        if g > 0.04045:
            g = ((g + 0.055) / 1.055) ** 2.4
        else:
            g = g / 12.92
            
        if b > 0.04045:
            b = ((b + 0.055) / 1.055) ** 2.4
        else:
            b = b / 12.92
        
        # Konvertiere zu XYZ
        X = r * 0.664511 + g * 0.154324 + b * 0.162028
        Y = r * 0.283881 + g * 0.668433 + b * 0.047685
        Z = r * 0.000088 + g * 0.072310 + b * 0.986039
        
        # Berechne xy-Koordinaten
        sum_XYZ = X + Y + Z
        
        # Verhindere Division durch Null
        if sum_XYZ == 0:
            return [0.0, 0.0]
            
        x = X / sum_XYZ
        y = Y / sum_XYZ
        
        return [x, y]
    
    @staticmethod
    def _xy_to_rgb(x: float, y: float, brightness: float = 100) -> Tuple[int, int, int]:
        """
        Konvertiert xy-Koordinaten zurück zu RGB-Farben.
        
        Args:
            x: x-Koordinate (0-1)
            y: y-Koordinate (0-1)
            brightness: Helligkeit in Prozent (0-100)
            
        Returns:
            RGB-Tuple (0-255)
        """
        # Verhindere Division durch Null
        if y == 0:
            return (0, 0, 0)
            
        # Berechne XYZ aus xy
        z = 1.0 - x - y
        Y = brightness / 100  # Anpassen der Helligkeit
        X = (Y / y) * x
        Z = (Y / y) * z
        
        # Konvertiere XYZ zu RGB
        r =  X * 1.656492 - Y * 0.354851 - Z * 0.255038
        g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
        b =  X * 0.051713 - Y * 0.121364 + Z * 1.011530
        
        # Initialisiere die RGB-Werte als lokale Variablen
        r_out, g_out, b_out = r, g, b
        
        # Gamut-Korrektur und inverse Gamma-Korrektur
        if r_out <= 0:
            r_out = 0
        elif r_out < 0.0031308:
            r_out = 12.92 * r_out
        else:
            r_out = 1.055 * (r_out ** (1/2.4)) - 0.055
            
        if g_out <= 0:
            g_out = 0
        elif g_out < 0.0031308:
            g_out = 12.92 * g_out
        else:
            g_out = 1.055 * (g_out ** (1/2.4)) - 0.055
            
        if b_out <= 0:
            b_out = 0
        elif b_out < 0.0031308:
            b_out = 12.92 * b_out
        else:
            b_out = 1.055 * (b_out ** (1/2.4)) - 0.055
        
        # Skaliere auf 0-255 und begrenzen
        r_int = max(0, min(255, int(r_out * 255)))
        g_int = max(0, min(255, int(g_out * 255)))
        b_int = max(0, min(255, int(b_out * 255)))
        
        return (r_int, g_int, b_int)