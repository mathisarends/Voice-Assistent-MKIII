from __future__ import annotations
import asyncio
from typing import Any, Optional

from tools.lights.hue.bridge import HueBridge
from tools.lights.hue.group_controller import GroupController
from tools.lights.hue.scene_controller import SceneController

class LightingController:
    """Höheres Abstraktionsniveau für typische Beleuchtungsaufgaben"""
    
    # Name der temporären Szene zur Zustandsspeicherung
    TEMP_SCENE_NAME = "_saved_state_scene"
    
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
        self.groups = GroupController(bridge)
        self.scenes = SceneController(bridge)
        self._active_scene_before_off: Optional[str] = None
        self._active_group_before_off: Optional[str] = None
    
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
    
    async def get_all_lights(self) -> dict[str, Any]:
        """Alle Lichter und ihre Zustände abrufen"""
        return await self.bridge.get_request("lights")
    
    async def turn_off(self) -> None:
        """Alle Lichter ausschalten und den aktuellen Zustand in der Bridge speichern
        
        Anstatt den Zustand intern zu speichern, merken wir uns die aktive Szene
        und schalten dann alle Lichter aus.
        """
        # Aktive Gruppe und Szene speichern
        self._active_group_before_off = await self.groups.get_active_group()
        self._active_scene_before_off = await self.scenes.get_active_scene(self._active_group_before_off)
        
        # Alle Lichter ausschalten (gruppenweit)
        groups = await self.groups.get_all_groups()
        for group_id in groups.keys():
            await self.groups.set_group_state(group_id, {"on": False})
    
    async def turn_on(self) -> None:
        """Alle Lichter wieder mit dem gespeicherten Zustand einschalten
        
        Aktiviert die gespeicherte Szene wieder, falls vorhanden.
        """
        if self._active_group_before_off and self._active_scene_before_off:
            # Szene in der gespeicherten Gruppe aktivieren
            await self.scenes.activate_scene(
                self._active_group_before_off, 
                self._active_scene_before_off
            )
        else:
            # Falls keine Szene gespeichert war, einfach die Lichter einschalten
            groups = await self.groups.get_all_groups()
            for group_id in groups.keys():
                await self.groups.set_group_state(group_id, {"on": True})
        
        # Gespeicherten Zustand zurücksetzen
        self._active_scene_before_off = None
        self._active_group_before_off = None


async def main():
    bridge = HueBridge.connect_by_ip()
    
    lighting = LightingController(bridge)
    
    # Test des neuen Ansatzes
    await lighting.scenes.activate_scene_by_name("Majestätischer Morgen")
    print("Szene aktiviert. Schalte alle Lichter aus...")
    await lighting.turn_off()
    
    import time
    time.sleep(5)
    
    print("Schalte alle Lichter wieder ein mit vorherigem Zustand...")
    await lighting.turn_on()
    
    print("Test abgeschlossen.")

if __name__ == "__main__":
    asyncio.run(main())