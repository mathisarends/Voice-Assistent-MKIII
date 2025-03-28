from __future__ import annotations

from typing import Any
from tools.lights.bridge.bridge import HueBridge
from tools.lights.group_controller import GroupController


class SceneController:
    """Verantwortlich für die Verwaltung von Szenen"""

    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge

    async def get_all_scenes(self) -> dict[str, Any]:
        """Alle Szenen abrufen"""
        return await self.bridge.get_request("scenes")

    async def get_scene_names(self) -> list[str]:
        """Gibt eine Liste aller verfügbaren Szenennamen zurück"""
        scenes = await self.get_all_scenes()
        return [
            scene_data.get("name")
            for scene_id, scene_data in scenes.items()
            if scene_data.get("name")
        ]

    async def get_active_scene(self, group_id: str = None) -> str:
        """Ermittelt die aktuell aktive Szene in einer Gruppe

        Falls keine Gruppe angegeben ist, wird die erste aktive Gruppe verwendet.
        Falls keine aktive Szene gefunden wird, wird None zurückgegeben.
        """

        # Falls keine Gruppe angegeben, finde aktive Gruppe
        if group_id is None:
            group_controller = GroupController(self.bridge)
            group_id = await group_controller.get_active_group()

        # Hole Gruppeninformationen
        group_info = await self.bridge.get_request(f"groups/{group_id}")

        # Prüfe, ob eine Szene aktiv ist
        return group_info.get("action", {}).get("scene")

    async def activate_scene(self, group_id: str, scene_id: str) -> list:
        """Eine Szene für eine Gruppe aktivieren"""
        return await self.bridge.put_request(
            f"groups/{group_id}/action", {"scene": scene_id}
        )

    async def find_scene_by_name(self, scene_name: str) -> tuple[str, str]:
        """Findet eine Szene anhand ihres Namens und gibt (scene_id, group_id) zurück"""
        scenes = await self.get_all_scenes()

        for scene_id, scene_data in scenes.items():
            if scene_data.get("name") == scene_name:
                group_id = scene_data.get("group")
                if group_id:
                    return scene_id, group_id

        raise ValueError(f"Szene mit Namen '{scene_name}' nicht gefunden")

    async def activate_scene_by_name(self, scene_name: str) -> list:
        """Eine Szene anhand ihres Namens aktivieren"""
        scene_id, group_id = await self.find_scene_by_name(scene_name)
        return await self.activate_scene(group_id, scene_id)

    async def get_group_scenes(self, group_id: str) -> list[tuple[str, str]]:
        """Gibt alle Szenen zurück, die zu einer bestimmten Gruppe gehören

        Returns:
            list[tuple[str, str]]: Liste von (scene_id, scene_name) Tupeln
        """
        scenes = await self.get_all_scenes()

        # Filtere Szenen, die zur angegebenen Gruppe gehören
        group_scenes = []
        for scene_id, scene_data in scenes.items():
            if scene_data.get("group") == group_id and scene_data.get("name"):
                group_scenes.append((scene_id, scene_data.get("name")))

        # Sortiere nach Namen (kann bei Bedarf angepasst werden)
        return sorted(group_scenes, key=lambda x: x[1])

    async def _get_adjacent_scene(self, direction: int) -> tuple[str, str, str]:
        """Hilfsmethode: Ermittelt die benachbarte Szene (vorherige oder nächste)

        Args:
            direction: 1 für nächste Szene, -1 für vorherige Szene

        Returns:
            tuple[str, str, str]: (active_group, scene_id, scene_name)
        """
        # Hole aktive Gruppe
        group_controller = GroupController(self.bridge)
        active_group = await group_controller.get_active_group()

        # Hole aktive Szene
        active_scene_id = await self.get_active_scene(active_group)

        # Hole alle Szenen für diese Gruppe
        group_scenes = await self.get_group_scenes(active_group)

        if not group_scenes:
            raise ValueError(f"Keine Szenen für Gruppe {active_group} gefunden")

        # Finde den Index der aktuellen Szene
        current_index = -1
        for i, (scene_id, _) in enumerate(group_scenes):
            if scene_id == active_scene_id:
                current_index = i
                break

        # Wenn keine aktive Szene gefunden wurde oder die aktive Szene nicht in der Liste ist,
        # starte mit der ersten/letzten Szene
        if current_index == -1:
            next_index = 0 if direction > 0 else len(group_scenes) - 1
        else:
            # Berechne den nächsten Index mit Rundumschlag
            next_index = (current_index + direction) % len(group_scenes)

        # Bestimme die Zielszene
        next_scene_id, next_scene_name = group_scenes[next_index]

        return active_group, next_scene_id, next_scene_name

    async def activate_next_scene(self) -> list:
        """Aktiviert die nächste Szene in der aktuellen Gruppe

        Returns:
            list: Antwort der Bridge API
        """
        active_group, next_scene_id, next_scene_name = await self._get_adjacent_scene(
            direction=1
        )
        return await self.activate_scene(active_group, next_scene_id)

    async def activate_previous_scene(self) -> list:
        """Aktiviert die vorherige Szene in der aktuellen Gruppe

        Returns:
            list: Antwort der Bridge API
        """
        active_group, prev_scene_id, prev_scene_name = await self._get_adjacent_scene(
            direction=-1
        )
        return await self.activate_scene(active_group, prev_scene_id)
