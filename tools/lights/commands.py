from dataclasses import dataclass
from typing import Any, Dict, List
from tools.lights.color_presets import ColorPresets
from tools.lights.core.light_command import LightCommand
from tools.lights.core.light_receiver import LightReceiver
from tools.lights.utils.hue_color_utils import HueColorUtils


class TurnOnCommand(LightCommand):
    """Befehl zum Einschalten des Lichts."""
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        return await light.bridge.set_light_state(light.device_id, {"on": True})
    
    def get_description(self) -> str:
        return "Licht einschalten"
    
    
class TurnOffCommand(LightCommand):
    """Befehl zum Ausschalten des Lichts."""
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        return await light.bridge.set_light_state(light.device_id, {"on": False})
    
    def get_description(self) -> str:
        return "Licht ausschalten"
    
# Konkreter SetBrightness-Befehl
@dataclass
class SetBrightnessCommand(LightCommand):
    """Befehl zum Einstellen der Helligkeit."""
    brightness: int
    transition_time: float = 0.0
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        if not 0 <= self.brightness <= 100:
            raise ValueError("Helligkeit muss zwischen 0 und 100 liegen")
        
        # Umrechnung in Hue-Helligkeit (0-254)
        hue_brightness = round(self.brightness / 100 * 254)
        
        state = {"bri": hue_brightness}
        if self.transition_time > 0:
            state["transitiontime"] = int(self.transition_time * 10)
        
        return await light.bridge.set_light_state(light.device_id, state)
    
    def get_description(self) -> str:
        return f"Helligkeit auf {self.brightness}% setzen"


# Konkreter SetColorRGB-Befehl
@dataclass
class SetColorRGBCommand(LightCommand):
    """Befehl zum Einstellen der Farbe über RGB-Werte."""
    red: int
    green: int
    blue: int
    transition_time: float = 0.0
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        if not all(0 <= c <= 255 for c in (self.red, self.green, self.blue)):
            raise ValueError("RGB-Werte müssen zwischen 0 und 255 liegen")
        
        xy = HueColorUtils.rgb_to_xy(self.red, self.green, self.blue)
        
        state = {"xy": xy}
        if self.transition_time > 0:
            state["transitiontime"] = int(self.transition_time * 10)
        
        return await light.bridge.set_light_state(light.device_id, state)
    
    def get_description(self) -> str:
        return f"Farbe auf RGB({self.red}, {self.green}, {self.blue}) setzen"


# Konkreter SetColorPreset-Befehl
@dataclass
class SetColorPresetCommand(LightCommand):
    """Befehl zum Einstellen einer vordefinierten Farbe."""
    preset_name: str
    transition_time: float = 0.0
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        rgb = ColorPresets.get_color(self.preset_name)
        if rgb is None:
            available_colors = ", ".join(ColorPresets.list_colors())
            raise ValueError(f"Unbekannte Farbe: '{self.preset_name}'. Verfügbare Farben: {available_colors}")
        
        r, g, b = rgb
        xy = HueColorUtils.rgb_to_xy(r, g, b)
        
        state = {"xy": xy}
        if self.transition_time > 0:
            state["transitiontime"] = int(self.transition_time * 10)
        
        return await light.bridge.set_light_state(light.device_id, state)
    
    def get_description(self) -> str:
        return f"Farbe auf Preset '{self.preset_name}' setzen"


# Konkreter SetColorTemperature-Befehl
@dataclass
class SetColorTemperatureCommand(LightCommand):
    """Befehl zum Einstellen der Farbtemperatur."""
    temperature_k: int
    transition_time: float = 0.0
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        if not 2000 <= self.temperature_k <= 6500:
            raise ValueError("Farbtemperatur muss zwischen 2000K und 6500K liegen")
        
        # Umrechnung von Kelvin in Mired (1000000/K)
        mired = int(1000000 / self.temperature_k)
        
        # Sicherstellen, dass der Mired-Wert innerhalb des zulässigen Bereichs liegt (153-500)
        mired = max(153, min(500, mired))
        
        state = {"ct": mired}
        if self.transition_time > 0:
            state["transitiontime"] = int(self.transition_time * 10)
        
        return await light.bridge.set_light_state(light.device_id, state)
    
    def get_description(self) -> str:
        return f"Farbtemperatur auf {self.temperature_k}K setzen"


# Konkreter SetSceneCommand
@dataclass
class SetSceneCommand(LightCommand):
    """Befehl zum Aktivieren einer vordefinierten Szene."""
    scene_id: str
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        # Hier müsste die Szene über einen anderen API-Endpunkt aktiviert werden
        # Dies ist nur ein Platzhalter für die Implementierung
        return await light.bridge.set_light_state(light.device_id, {"scene": self.scene_id})
    
    def get_description(self) -> str:
        return f"Szene '{self.scene_id}' aktivieren"


# Gruppe von Befehlen, die als ein einziger Befehl ausgeführt werden
class LightCommandGroup(LightCommand):
    """Eine Gruppe von Befehlen, die als ein einziger Befehl ausgeführt werden."""
    
    def __init__(self, commands: List[LightCommand]):
        self.commands = commands
    
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        results = []
        for command in self.commands:
            result = await command.execute(light)
            results.extend(result)
        return results
    
    def get_description(self) -> str:
        return "; ".join(cmd.get_description() for cmd in self.commands)