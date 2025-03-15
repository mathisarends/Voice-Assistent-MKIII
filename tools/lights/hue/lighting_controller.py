from __future__ import annotations
import asyncio
import time

from tools.lights.hue.bridge import HueBridge
from tools.lights.hue.group_controller import GroupController
from tools.lights.hue.scene_controller import SceneController

class LightingController:
    """Höheres Abstraktionsniveau für typische Beleuchtungsaufgaben"""
    
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
        self.groups = GroupController(bridge)
        self.scenes = SceneController(bridge)
    
    async def adjust_brightness(self, percent_change: int) -> list:
        """Ändert die Helligkeit der aktuellen Szene/Lichter um den angegebenen Prozentsatz"""
        # Finde die aktive Gruppe
        target_group = await self.groups.get_active_group()
        
        # Helligkeit für die Zielgruppe ändern
        return await self.change_brightness_by_percent(target_group, percent_change)
    
    async def change_brightness_by_percent(self, group_id: str, percent_change: int) -> list:
        """Helligkeit für eine Gruppe um einen Prozentsatz ändern"""
        # Hole aktuellen Zustand der Gruppe
        group_data = await self.bridge.get_request(f"groups/{group_id}")
        
        # Hole aktuelle Helligkeit aus dem Zustand
        current_brightness = group_data.get('action', {}).get('bri', 0)
        
        # Berechne neue Helligkeit (0-254 ist der Helligkeitsbereich bei Philips Hue)
        max_brightness = 254
        brightness_change = int(max_brightness * (percent_change / 100))
        new_brightness = current_brightness + brightness_change
        
        # Begrenze auf gültigen Bereich
        new_brightness = max(0, min(254, new_brightness))
        
        # Setze die neue Helligkeit
        return await self.groups.set_group_brightness(group_id, new_brightness)


async def main():
    bridge = HueBridge.connect_by_ip()
    
    lighting = LightingController(bridge)
    
    await lighting.scenes.activate_scene_by_name("Majestätischer Morgen")
    
    # scene_names = await lighting.scenes.get_scene_names()

    # for scene_name in scene_names:
    #     await lighting.scenes.activate_scene_by_name(scene_name)
    #     print(f"Die Szene '{scene_name}' wurde aktiviert.")
    #     time.sleep(2)
    
    print("Szene 'Sternenlicht' wurde aktiviert und um 25% heller gemacht.")

if __name__ == "__main__":
    asyncio.run(main())