from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional, ClassVar
import colorsys
from tools.lights.color_presets import ColorPresets
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.light_device import LightDevice
from tools.lights.hue.light_status import LightStatus

class HueLight(LightDevice):
    """Universelle Klasse für die Steuerung von Philips Hue Lampen."""

    # Typspezifische Eigenschaften
    DEVICE_TYPES: ClassVar[Dict[str, Dict[str, Any]]] = {
        "LCL007": {  # Hue Lightstrip Plus
            "name": "Hue Lightstrip Plus",
            "max_brightness": 100,  # Prozent
            "min_brightness": 1,    # Prozent
            "max_lumen": 1600,
            "min_dim_level": 40
        },
        "LCE002": {  # Hue Color Candle
            "name": "Hue Color Candle",
            "max_brightness": 100,  # Prozent
            "min_brightness": 10,   # Höhere Mindesthelligkeit für Kerzenlampen
            "max_lumen": 470,
            "min_dim_level": 200
        },
        # Standardwerte für unbekannte Geräte
        "default": {
            "name": "Hue Light",
            "max_brightness": 100,
            "min_brightness": 1,
            "max_lumen": 800,
            "min_dim_level": 0
        }
    }

    def __init__(self, bridge: Bridge, device_id: str, name: str):
        """
        Initialisiert eine Hue Lampe.

        Args:
            bridge: Die Hue Bridge-Instanz zur Kommunikation
            device_id: Die ID des Geräts in der Hue Bridge
            name: Der Name des Geräts
        """
        super().__init__(device_id, name)
        self.bridge = bridge
        self._color: Tuple[int, int, int] = (255, 255, 255)
        self._model_id: str = ""
        self._device_type: str = ""
        self._max_lumen: int = 0
        self._min_dim_level: int = 0
        
        # Diese Werte werden bei initialize() mit den tatsächlichen Werten überschrieben
        self._min_brightness = 1
        self._max_brightness = 100
    
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
        if value < self._min_brightness:
            value = self._min_brightness
        elif value > self._max_brightness:
            value = self._max_brightness
        self._brightness = value
    
    @property
    def model_id(self) -> str:
        """Gibt die Modell-ID des Geräts zurück."""
        return self._model_id
    
    @property
    def device_type(self) -> str:
        """Gibt den Gerätetyp zurück."""
        return self._device_type
    
    async def initialize(self) -> None:
        """Initialisiert das Gerät mit seinen aktuellen Zuständen von der Bridge."""
        lights = await self.bridge.get_lights()
        if self.device_id in lights:
            light_data = lights[self.device_id]
            self.name = light_data.get("name", self.name)
            
            # Modell-ID und Gerätetyp speichern
            self._model_id = light_data.get("modelid", "")
            self._device_type = light_data.get("type", "")
            
            # Gerätetypspezifische Eigenschaften abrufen
            device_props = self.DEVICE_TYPES.get(self._model_id, self.DEVICE_TYPES["default"])
            self._min_brightness = device_props["min_brightness"]
            self._max_brightness = device_props["max_brightness"]
            self._max_lumen = device_props.get("max_lumen", 0)
            self._min_dim_level = device_props.get("min_dim_level", 0)
            
            # Capabilities auslesen, wenn vorhanden
            capabilities = light_data.get("capabilities", {}).get("control", {})
            if "maxlumen" in capabilities:
                self._max_lumen = capabilities["maxlumen"]
            if "mindimlevel" in capabilities:
                self._min_dim_level = capabilities["mindimlevel"]
            
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
        Schaltet das Licht ein.
        
        Returns:
            Die Antwort der Bridge
        """
        self.is_on = True
        return await self.bridge.set_light_state(self.device_id, {"on": True})
    
    async def turn_off(self) -> List[Dict[str, Any]]:
        """
        Schaltet das Licht aus.
        
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
        """
        # Sicherstellen, dass die Helligkeit im erlaubten Bereich liegt
        if brightness < self._min_brightness:
            brightness = self._min_brightness
            print(f"Hinweis: Helligkeit auf Mindestwert {self._min_brightness}% angehoben")
        elif brightness > self._max_brightness:
            brightness = self._max_brightness
            print(f"Hinweis: Helligkeit auf Maximalwert {self._max_brightness}% begrenzt")
        
        self.brightness = brightness
        
        # Umrechnung in Hue-Helligkeit (0-254)
        hue_brightness = round(brightness / 100 * 254)
        return await self.bridge.set_light_state(self.device_id, {"bri": hue_brightness})
    
    async def set_color_rgb(self, red: int, green: int, blue: int, transition_time: float = 0.0) -> List[Dict[str, Any]]:
        """
        Setzt die Farbe des Lichts über RGB-Werte.
        
        Args:
            red: Rotwert (0-255)
            green: Grünwert (0-255)
            blue: Blauwert (0-255)
            transition_time: Übergangszeit in Sekunden (0 = sofort)
            
        Returns:
            Die Antwort der Bridge
            
        Raises:
            ValueError: Wenn ein RGB-Wert außerhalb des gültigen Bereichs liegt
        """
        if not all(0 <= c <= 255 for c in (red, green, blue)):
            raise ValueError("RGB-Werte müssen zwischen 0 und 255 liegen")
        
        self.color = (red, green, blue)
        xy = self._rgb_to_xy(red, green, blue)
        
        state = {"xy": xy}
        
        # Füge Übergangszeit hinzu, wenn gewünscht
        # Hue API verwendet Zeiteinheiten von 1/10 Sekunden
        if transition_time > 0:
            state["transitiontime"] = int(transition_time * 10)
        
        return await self.bridge.set_light_state(self.device_id, state)
    
    async def set_color_preset(self, preset_name: str, transition_time: float = 0.0) -> List[Dict[str, Any]]:
        """
        Setzt die Farbe des Lichts über einen vordefinierten Farbnamen.
        
        Args:
            preset_name: Name der Farbe (z.B. "rot", "blau", "entspannung")
            transition_time: Übergangszeit in Sekunden (0 = sofort)
            
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
        return await self.set_color_rgb(r, g, b, transition_time)
    
    async def set_color_temperature(self, temperature_k: int, transition_time: float = 0.0) -> List[Dict[str, Any]]:
        """
        Setzt die Farbtemperatur in Kelvin.
        
        Args:
            temperature_k: Farbtemperatur in Kelvin (2000-6500)
            transition_time: Übergangszeit in Sekunden (0 = sofort)
            
        Returns:
            Die Antwort der Bridge
            
        Raises:
            ValueError: Wenn die Farbtemperatur außerhalb des gültigen Bereichs liegt
        """
        if not 2000 <= temperature_k <= 6500:
            raise ValueError("Farbtemperatur muss zwischen 2000K und 6500K liegen")
        
        # Umrechnung von Kelvin in Mired (1000000/K)
        mired = int(1000000 / temperature_k)
        
        # Sicherstellen, dass der Mired-Wert innerhalb des zulässigen Bereichs liegt (153-500)
        mired = max(153, min(500, mired))
        
        state = {"ct": mired}
        
        # Füge Übergangszeit hinzu, wenn gewünscht
        if transition_time > 0:
            state["transitiontime"] = int(transition_time * 10)
        
        return await self.bridge.set_light_state(self.device_id, state)
    
    async def get_status(self) -> LightStatus:
        """
        Holt den aktuellen Status des Lichts von der Bridge.
        
        Returns:
            LightStatus-Objekt mit den aktuellen Gerätedaten
        """
        lights = await self.bridge.get_lights()
        if self.device_id in lights:
            light_data = lights[self.device_id]
            state = light_data.get("state", {})
            
            # Extrahiere Capabilities
            capabilities = light_data.get("capabilities", {}).get("control", {})
            max_lumen = capabilities.get("maxlumen", self._max_lumen)
            min_dim_level = capabilities.get("mindimlevel", self._min_dim_level)
            
            return LightStatus(
                device_id=self.device_id,
                name=light_data.get("name", self.name),
                is_on=state.get("on", self.is_on),
                brightness=round(state.get("bri", 254) / 254 * 100),
                color_rgb=self._get_current_rgb_from_bridge(light_data),
                reachable=state.get("reachable", True),
                device_type=light_data.get("type", self._device_type),
                model_id=light_data.get("modelid", self._model_id),
                max_lumen=max_lumen,
                min_dim_level=min_dim_level
            )
        
        return LightStatus(
            device_id=self.device_id,
            name=self.name,
            is_on=self.is_on,
            brightness=self.brightness,
            color_rgb=self.color,
            reachable=True,  # Annahme: Lokal ist immer erreichbar
            device_type=self._device_type,
            model_id=self._model_id,
            max_lumen=self._max_lumen,
            min_dim_level=self._min_dim_level
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
        elif colormode == "ct" and "ct" in state:
            # Konvertiere Farbtemperatur in RGB-Approximation
            mired = state["ct"]
            temp_k = 1000000 / mired
            return self._color_temp_to_rgb(temp_k)
        
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
    
    @staticmethod
    def _color_temp_to_rgb(temp_k: float) -> Tuple[int, int, int]:
        """
        Konvertiert Farbtemperatur (Kelvin) in RGB-Werte.
        
        Args:
            temp_k: Farbtemperatur in Kelvin (typischerweise 2000-6500)
            
        Returns:
            RGB-Tuple (0-255)
        """
        # Begrenze die Temperatur auf den unterstützten Bereich
        temp = min(max(temp_k, 1000), 40000) / 100
        
        # Rote Komponente
        if temp <= 66:
            red = 255
        else:
            red = temp - 60
            red = 329.698727446 * (red ** -0.1332047592)
            red = max(0, min(255, red))
        
        # Grüne Komponente
        if temp <= 66:
            green = temp
            green = 99.4708025861 * (green ** 0.1332047592)
        else:
            green = temp - 60
            green = 288.1221695283 * (green ** -0.0755148492)
        green = max(0, min(255, green))
        
        # Blaue Komponente
        if temp >= 66:
            blue = 255
        elif temp <= 19:
            blue = 0
        else:
            blue = temp - 10
            blue = 138.5177312231 * (blue ** 0.2271896232)
            blue = max(0, min(255, blue))
        
        return (int(red), int(green), int(blue))


# Beispiel für die Nutzung mit verschiedenen Lampentypen
async def setup_lights(bridge: Bridge) -> Dict[str, HueLight]:
    """
    Richtet alle verfügbaren Lampen ein und gibt sie in einem Dictionary zurück.
    
    Args:
        bridge: Eine verbundene Bridge-Instanz
        
    Returns:
        Dictionary mit Lampen-IDs als Schlüssel und HueLight-Instanzen als Werte
    """
    # Alle Lampen von der Bridge abrufen
    light_data = await bridge.get_lights()
    lights = {}
    
    for light_id, data in light_data.items():
        light = HueLight(bridge, light_id, data.get("name", f"Lampe {light_id}"))
        await light.initialize()
        lights[light_id] = light
        
        print(f"Lampe initialisiert: {light.name} (ID: {light_id}, Typ: {light.device_type}, Modell: {light.model_id})")
    
    return lights