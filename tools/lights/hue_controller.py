import asyncio
from typing import Any, Dict, List, Optional

from tools.lights.bridge import HueBridge
from tools.lights.brightness_controller import BrightnessController
from tools.lights.group_controller import GroupController
from tools.lights.scene_controller import SceneController


class HueController:
    """Facade für alle Philips Hue Funktionalitäten

    Bietet eine vereinfachte, einheitliche Oberfläche für die am häufigsten
    verwendeten Funktionalitäten, ohne dass der Benutzer mit verschiedenen
    Controller-Klassen interagieren muss.
    """

    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
        # Interne Controller - als private Attribute
        self._group_controller = GroupController(bridge)
        self._scene_controller = SceneController(bridge)
        self._lighting_controller = BrightnessController(bridge, self._group_controller)

        self._active_scene_before_off: Optional[str] = None
        self._active_group_before_off: Optional[str] = None

    # ---- Szenen-bezogene Methoden ----

    async def get_all_scenes(self) -> Dict[str, Any]:
        return await self._scene_controller.get_all_scenes()

    async def get_scene_names(self) -> List[str]:
        return await self._scene_controller.get_scene_names()

    async def activate_scene(self, scene_name: str) -> None:
        await self._scene_controller.activate_scene_by_name(scene_name)

    async def next_scene(self) -> None:
        await self._scene_controller.activate_next_scene()

    async def previous_scene(self) -> None:
        await self._scene_controller.activate_previous_scene()

    # ---- Gruppen-bezogene Methoden ----

    async def get_all_groups(self) -> Dict[str, Any]:
        return await self._group_controller.get_all_groups()

    async def get_group_names(self) -> Dict[str, str]:
        return await self._group_controller.get_all_groups()

    # ---- Licht-bezogene Methoden ----

    async def adjust_brightness(self, percent_change: int) -> None:
        """Helligkeit der aktuellen Gruppe/Szene anpassen"""
        await self._lighting_controller.adjust_brightness(percent_change)

    async def get_current_brightness(self) -> int:
        """Aktuelle Helligkeit der aktiven Gruppe abrufen"""
        group_id = await self._group_controller.get_active_group()
        return await self._lighting_controller.get_current_brightness(group_id)

    async def set_brightness(self, percent: int) -> None:
        """Helligkeit auf einen bestimmten Prozentwert setzen (0-100%)"""
        group_id = await self._group_controller.get_active_group()

        # Konvertiere Prozent (0-100) in Hue-Wert (0-254)
        bri = int((percent / 100) * 254)
        bri = max(0, min(254, bri))  # Begrenze auf gültigen Bereich

        await self._group_controller.set_group_brightness(group_id, bri)

    async def turn_off(self) -> None:
        """Alle Lichter ausschalten und den aktuellen Status speichern"""
        # Speichere aktive Gruppe und Szene
        self._active_group_before_off = await self._group_controller.get_active_group()
        self._active_scene_before_off = await self._scene_controller.get_active_scene(
            self._active_group_before_off
        )

        # Schalte alle Gruppen aus
        groups = await self._group_controller.get_all_groups()
        for group_id in groups.keys():
            await self._group_controller.set_group_state(group_id, {"on": False})

    async def turn_on(self) -> None:
        """Alle Lichter mit dem gespeicherten Zustand wieder einschalten"""
        if self._active_group_before_off and self._active_scene_before_off:
            # Aktiviere die gespeicherte Szene
            await self._scene_controller.activate_scene(
                self._active_group_before_off, self._active_scene_before_off
            )
        else:
            # Falls keine Szene gespeichert war, schalte einfach alle Lichter ein
            groups = await self._group_controller.get_all_groups()
            for group_id in groups.keys():
                await self._group_controller.set_group_state(group_id, {"on": True})

        # Zurücksetzen des gespeicherten Zustands
        self._active_scene_before_off = None
        self._active_group_before_off = None


async def main():
    bridge = HueBridge.connect_by_ip()

    # Mit dem Facade-Muster ist die API einfacher zu benutzen
    hue = HueController(bridge)

    scenes = await hue.get_scene_names()

    print(f"Verfügbare Szenen: {scenes}")

    current_brightness = await hue.get_current_brightness()
    print(f"Aktuelle Helligkeit: {current_brightness}")


if __name__ == "__main__":
    asyncio.run(main())
