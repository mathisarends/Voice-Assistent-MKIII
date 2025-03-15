from __future__ import annotations

from typing import Any
from tools.lights.hue.bridge import HueBridge

class SceneController:
    """Verantwortlich für die Verwaltung von Szenen"""
    
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
        
    async def get_all_scenes(self) -> dict[str, Any]:
        """Alle Szenen abrufen"""
        return await self.bridge.get_request("scenes")
    
    async def activate_scene(self, group_id: str, scene_id: str) -> list:
        """Eine Szene für eine Gruppe aktivieren"""
        return await self.bridge.put_request(f"groups/{group_id}/action", {"scene": scene_id})
    
    async def find_scene_by_name(self, scene_name: str) -> tuple[str, str]:
        """Findet eine Szene anhand ihres Namens und gibt (scene_id, group_id) zurück"""
        scenes = await self.get_all_scenes()
        
        for scene_id, scene_data in scenes.items():
            if scene_data.get('name') == scene_name:
                group_id = scene_data.get('group')
                if group_id:
                    return scene_id, group_id
        
        raise ValueError(f"Szene mit Namen '{scene_name}' nicht gefunden")
    
    async def activate_scene_by_name(self, scene_name: str) -> list:
        """Eine Szene anhand ihres Namens aktivieren"""
        scene_id, group_id = await self.find_scene_by_name(scene_name)
        return await self.activate_scene(group_id, scene_id)
