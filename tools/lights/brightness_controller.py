from __future__ import annotations
from typing import Any
import math

from tools.lights.bridge.bridge import HueBridge
from tools.lights.group_controller import GroupController


class BrightnessController:
    """Höheres Abstraktionsniveau für typische Beleuchtungsaufgaben"""

    # Name der temporären Szene zur Zustandsspeicherung
    TEMP_SCENE_NAME = "_saved_state_scene"

    # Konstanten für Helligkeitswerte
    MAX_BRIGHTNESS = 254

    def __init__(self, bridge: HueBridge, group_controller: GroupController) -> None:
        self.bridge = bridge
        self.groups = group_controller

    async def adjust_brightness(self, percent_change: int) -> list:
        """Ändert die Helligkeit der aktuellen Szene/Lichter um den angegebenen Prozentsatz"""
        # Finde die aktive Gruppe
        active_group = await self.groups.get_active_group()

        # Verwende die aktive Gruppe für die Helligkeitsänderung
        return await self._change_brightness_by_percent(active_group, percent_change)

    async def _change_brightness_by_percent(
        self, group_id: str, percent_change: int
    ) -> list:
        # Aktuelle Helligkeit in Prozent abrufen
        current_percent = await self.get_current_brightness(group_id)

        new_percent = current_percent + percent_change

        new_percent = max(0, min(100, new_percent))

        new_brightness = int(self.MAX_BRIGHTNESS * (new_percent / 100))

        return await self.groups.set_group_brightness(group_id, new_brightness)

    async def get_current_brightness(self, group_id: str) -> int:
        """Aktuelle Helligkeit einer Gruppe als Prozentsatz abrufen (aufgerundet auf 5%-Schritte)"""
        group_data = await self.bridge.get_request(f"groups/{group_id}")

        raw_brightness = group_data.get("action", {}).get("bri", 0)

        percent = (raw_brightness / self.MAX_BRIGHTNESS) * 100

        rounded_percent = math.ceil(percent / 5) * 5

        return rounded_percent

    async def get_all_lights(self) -> dict[str, Any]:
        """Alle Lichter und ihre Zustände abrufen"""
        return await self.bridge.get_request("lights")
