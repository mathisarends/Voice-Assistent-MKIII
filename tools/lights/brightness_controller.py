from __future__ import annotations
from typing import Any

from tools.lights.bridge import HueBridge
from tools.lights.group_controller import GroupController

class BrightnessController:
    """Höheres Abstraktionsniveau für typische Beleuchtungsaufgaben"""
    
    # Name der temporären Szene zur Zustandsspeicherung
    TEMP_SCENE_NAME = "_saved_state_scene"
    
    def __init__(self,  bridge: HueBridge, group_controller: GroupController) -> None:
        self.bridge = bridge
        self.groups = group_controller
    
    async def adjust_brightness(self, percent_change: int) -> list:
        """Ändert die Helligkeit der aktuellen Szene/Lichter um den angegebenen Prozentsatz"""
        # Finde die aktive Gruppe
        target_group = await self.groups.get_active_group()
        
        return await self._change_brightness_by_percent(target_group, percent_change)
    
    async def _change_brightness_by_percent(self, group_id: str, percent_change: int) -> list:
        group_data = await self.bridge.get_request(f"groups/{group_id}")
        
        current_brightness = group_data.get('action', {}).get('bri', 0)
        
        # Berechne neue Helligkeit (0-254 ist der Helligkeitsbereich bei Philips Hue)
        max_brightness = 254
        brightness_change = int(max_brightness * (percent_change / 100))
        new_brightness = current_brightness + brightness_change
        
        # Begrenze auf gültigen Bereich
        new_brightness = max(0, min(254, new_brightness))
        
        # Setze die neue Helligkeit
        return await self.groups.set_group_brightness(group_id, new_brightness)
    
    async def get_all_lights(self) -> dict[str, Any]:
        """Alle Lichter und ihre Zustände abrufen"""
        return await self.bridge.get_request("lights")