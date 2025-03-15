# Hilfsfunktionen für Farbkonvertierungen
import colorsys
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from tools.lights.color_presets import ColorPresets
from tools.lights.commands import LightCommandGroup, SetBrightnessCommand, SetColorPresetCommand, SetColorRGBCommand, SetColorTemperatureCommand, TurnOffCommand, TurnOnCommand
from tools.lights.core.light_command import LightCommand
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.light_status import LightStatus


class HueColorUtils:
    """Hilfsfunktionen für Farbkonvertierungen bei Philips Hue Lampen."""
    
    @staticmethod
    def rgb_to_xy(red: int, green: int, blue: int) -> List[float]:
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
    def xy_to_rgb(x: float, y: float, brightness: float = 100) -> Tuple[int, int, int]:
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
    def color_temp_to_rgb(temp_k: float) -> Tuple[int, int, int]:
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


# Die überarbeitete HueLight-Klasse, die das Command-Pattern unterstützt
class HueLight:
    """Universelle Klasse für die Steuerung von Philips Hue Lampen mit Command-Pattern."""

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
        self.bridge = bridge
        self.device_id = device_id
        self.name = name
        self._model_id: str = ""
        self._device_type: str = ""
        self._max_lumen: int = 0
        self._min_dim_level: int = 0
        self._is_on: bool = False
        self._brightness: int = 100
        self._color: Tuple[int, int, int] = (255, 255, 255)
        
        # Diese Werte werden bei initialize() mit den tatsächlichen Werten überschrieben
        self._min_brightness = 1
        self._max_brightness = 100
        
        # Command-History für Undo-Funktionalität
        self._command_history: List[LightCommand] = []
    
    @property
    def model_id(self) -> str:
        """Gibt die Modell-ID des Geräts zurück."""
        return self._model_id
    
    @property
    def device_type(self) -> str:
        """Gibt den Gerätetyp zurück."""
        return self._device_type
    
    @property
    def is_on(self) -> bool:
        """Gibt zurück, ob die Lampe eingeschaltet ist."""
        return self._is_on
    
    @property
    def brightness(self) -> int:
        """Gibt die aktuelle Helligkeit (0-100%) zurück."""
        return self._brightness
    
    @property
    def color(self) -> Tuple[int, int, int]:
        """Gibt die aktuelle RGB-Farbe zurück."""
        return self._color
    
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
            self._is_on = state.get("on", False)
            
            # Helligkeit von Hue (0-254) zu Prozent (0-100) konvertieren
            hue_bri = state.get("bri", 254)
            self._brightness = round(hue_bri / 254 * 100)
            
            # Farbe aus xy-Koordinaten extrahieren, falls vorhanden
            if "xy" in state and state.get("colormode") == "xy":
                self._color = HueColorUtils.xy_to_rgb(state["xy"][0], state["xy"][1], self._brightness)
        else:
            print(f"Warnung: Gerät mit ID {self.device_id} nicht in der Bridge gefunden")
    
    async def execute_command(self, command: LightCommand) -> List[Dict[str, Any]]:
        """
        Führt einen Befehl für diese Lampe aus.
        
        Args:
            command: Der auszuführende Befehl
            
        Returns:
            Die Antwort der Bridge
        """
        result = await command.execute(self)
        self._command_history.append(command)
        
        # Status aktualisieren nach der Ausführung des Befehls
        await self._update_status_after_command(command)
        
        return result
    
    async def _update_status_after_command(self, command: LightCommand) -> None:
        """
        Aktualisiert den internen Status nach der Ausführung eines Befehls.
        
        Args:
            command: Der ausgeführte Befehl
        """
        # Je nach Befehlstyp den internen Status aktualisieren
        if isinstance(command, TurnOnCommand):
            self._is_on = True
        elif isinstance(command, TurnOffCommand):
            self._is_on = False
        elif isinstance(command, SetBrightnessCommand):
            self._brightness = command.brightness
        elif isinstance(command, SetColorRGBCommand):
            self._color = (command.red, command.green, command.blue)
        elif isinstance(command, SetColorPresetCommand):
            rgb = ColorPresets.get_color(command.preset_name)
            if rgb:
                self._color = rgb
        elif isinstance(command, SetColorTemperatureCommand):
            self._color = HueColorUtils.color_temp_to_rgb(command.temperature_k)
        elif isinstance(command, LightCommandGroup):
            # Bei Befehlsgruppen jedes Unterkommando behandeln
            for cmd in command.commands:
                await self._update_status_after_command(cmd)
    
    async def get_last_command(self) -> Optional[LightCommand]:
        """Gibt den zuletzt ausgeführten Befehl zurück, falls vorhanden."""
        if self._command_history:
            return self._command_history[-1]
        return None
    
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
            
            # Status aktualisieren
            self._is_on = state.get("on", self._is_on)
            brightness = round(state.get("bri", 254) / 254 * 100)
            self._brightness = brightness
            
            # Aktuelle Farbe bestimmen
            colormode = state.get("colormode")
            if colormode == "xy" and "xy" in state:
                self._color = HueColorUtils.xy_to_rgb(state["xy"][0], state["xy"][1], brightness)
            elif colormode == "hs" and "hue" in state and "sat" in state:
                hue = state["hue"] / 65535 * 360
                sat = state["sat"] / 254 * 100
                val = brightness / 100
                r, g, b = colorsys.hsv_to_rgb(hue/360, sat/100, val)
                self._color = (int(r * 255), int(g * 255), int(b * 255))
            elif colormode == "ct" and "ct" in state:
                mired = state["ct"]
                temp_k = 1000000 / mired
                self._color = HueColorUtils.color_temp_to_rgb(temp_k)
            
            return LightStatus(
                device_id=self.device_id,
                name=light_data.get("name", self.name),
                is_on=self._is_on,
                brightness=brightness,
                color_rgb=self._color,
                reachable=state.get("reachable", True),
                device_type=light_data.get("type", self._device_type),
                model_id=light_data.get("modelid", self._model_id),
                max_lumen=max_lumen,
                min_dim_level=min_dim_level
            )
        
        # Wenn die Lampe nicht in der Bridge gefunden wurde, lokale Daten zurückgeben
        return LightStatus(
            device_id=self.device_id,
            name=self.name,
            is_on=self._is_on,
            brightness=self._brightness,
            color_rgb=self._color,
            reachable=False,
            device_type=self._device_type,
            model_id=self._model_id,
            max_lumen=self._max_lumen,
            min_dim_level=self._min_dim_level
        )
    
    # Hilfsmethoden für die einfache Verwendung häufiger Befehle
    
    async def turn_on(self) -> List[Dict[str, Any]]:
        """Schaltet die Lampe ein."""
        return await self.execute_command(TurnOnCommand())
    
    async def turn_off(self) -> List[Dict[str, Any]]:
        """Schaltet die Lampe aus."""
        return await self.execute_command(TurnOffCommand())
    
    async def set_brightness(self, brightness: int, transition_time: float = 0.0) -> List[Dict[str, Any]]:
        """Stellt die Helligkeit ein."""
        return await self.execute_command(SetBrightnessCommand(brightness, transition_time))
    
    async def set_color_rgb(self, red: int, green: int, blue: int, transition_time: float = 0.0) -> List[Dict[str, Any]]:
        """Stellt die RGB-Farbe ein."""
        return await self.execute_command(SetColorRGBCommand(red, green, blue, transition_time))
    
    async def set_color_preset(self, preset_name: str, transition_time: float = 0.0) -> List[Dict[str, Any]]:
        """Stellt eine vordefinierte Farbe ein."""
        return await self.execute_command(SetColorPresetCommand(preset_name, transition_time))
    
    async def set_color_temperature(self, temperature_k: int, transition_time: float = 0.0) -> List[Dict[str, Any]]:
        """Stellt die Farbtemperatur ein."""
        return await self.execute_command(SetColorTemperatureCommand(temperature_k, transition_time))
