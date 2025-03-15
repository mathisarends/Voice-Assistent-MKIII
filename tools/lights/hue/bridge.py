# aktiviere_sternenlicht.py
from __future__ import annotations

import asyncio
import os
from typing import Any, Optional
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class Bridge:
    """Einfacher Hue Bridge Client"""

    def __init__(self, *, ip: str, user: str) -> None:
        self.ip = ip
        self.user = user
        self.info = {}

    def __repr__(self) -> str:
        return f"<Bridge {self.ip}>"

    @property
    def url(self) -> str:
        return f"http://{self.ip}/api/{self.user}"

    @staticmethod
    async def discover() -> list[dict[str, str]]:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discovery.meethue.com/") as response:
                return await response.json()

    @classmethod
    async def connect(cls) -> Bridge:
        load_dotenv()
        user_id = os.getenv("HUE_USER_ID")
        
        bridges = await cls.discover()
        if not bridges:
            raise ValueError("Keine Hue Bridge gefunden")
        
        return cls(ip=bridges[0]["internalipaddress"], user=user_id)
    
    @classmethod
    def connect_by_ip(cls, ip: Optional[str] = None, user_id: Optional[str] = None) -> Bridge:
        if ip is None:
            ip = os.getenv("HUE_BRIDGE_IP")
        
        if user_id is None:
            load_dotenv()
            user_id = os.getenv("HUE_USER_ID")
            if not user_id:
                raise ValueError("Kein HUE_USER_ID in .env gefunden und kein user_id angegeben")
        
        return cls(ip=ip, user=user_id)
    
    async def get_lights(self) -> dict[str, Any]:
        """Alle Lampen abrufen"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/lights") as response:
                return await response.json()
    
    async def set_light_state(self, light_id: str, state: dict) -> list:
        """Zustand einer Lampe ändern"""
        async with aiohttp.ClientSession() as session:
            async with session.put(f"{self.url}/lights/{light_id}/state", json=state) as response:
                return await response.json()
            
    async def get_scenes(self) -> dict[str, Any]:
        """Alle Szenen abrufen"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/scenes") as response:
                return await response.json()
            
    async def activate_scene(self, group_id: str, scene_id: str) -> list:
        """Eine Szene für eine Gruppe aktivieren"""
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.url}/groups/{group_id}/action", 
                json={"scene": scene_id}
            ) as response:
                return await response.json()
            
    async def activate_scene_by_name(self, scene_name: str) -> list:
        """Eine Szene anhand ihres Namens aktivieren"""
        # Hole alle Szenen
        scenes = await self.get_scenes()
        
        # Finde die Szene mit dem angegebenen Namen
        scene_id = None
        group_id = None
        
        for sid, scene_data in scenes.items():
            if scene_data.get('name') == scene_name:
                scene_id = sid
                group_id = scene_data.get('group')
                break
        
        if not scene_id or not group_id:
            raise ValueError(f"Szene mit Namen '{scene_name}' nicht gefunden")
        
        # Aktiviere die Szene
        return await self.activate_scene(group_id, scene_id)
    
    async def set_group_brightness(self, group_id: str, brightness: int) -> list:
        """Helligkeit für eine Gruppe von Lichtern ändern (0-254)"""
        # Stelle sicher, dass die Helligkeit im gültigen Bereich liegt
        brightness = max(0, min(254, brightness))
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.url}/groups/{group_id}/action", 
                json={"bri": brightness}
            ) as response:
                return await response.json()
            
            
    async def get_groups(self) -> dict[str, Any]:
        """Alle Gruppen/Räume abrufen"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/groups") as response:
                return await response.json()
    
    async def adjust_brightness(self, percent_change: int) -> list:
        """Ändert die Helligkeit der aktuellen Szene/Lichter um den angegebenen Prozentsatz
        
        Args:
            percent_change: Prozentuale Änderung (-100 bis +100)
        """
        # Hole alle Gruppen
        groups = await self.get_groups()
        
        # Wir suchen die Gruppe 0 (alle Lichter) oder eine aktive Gruppe
        target_group = "0"  # Standard: Gruppe 0 (alle Lichter)
        
        # Wenn es spezifische aktive Gruppen gibt, verwenden wir die erste
        for group_id, group_data in groups.items():
            if group_data.get('state', {}).get('any_on', False):
                target_group = group_id
                break
        
        # Helligkeit für die Zielgruppe ändern
        result = await self.change_brightness_by_percent(target_group, percent_change)
        
        return result
        
    async def change_brightness_by_percent(self, group_id: str, percent_change: int) -> list:
        """Helligkeit für eine Gruppe um einen Prozentsatz ändern
        
        Args:
            group_id: Die ID der Lichtergruppe
            percent_change: Prozentuale Änderung (-100 bis +100)
        """
        # Hole aktuellen Zustand der Gruppe
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/groups/{group_id}") as response:
                group_data = await response.json()
        
        # Hole aktuelle Helligkeit aus dem Zustand
        current_brightness = group_data.get('action', {}).get('bri', 0)
        
        # Berechne neue Helligkeit (0-254 ist der Helligkeitsbereich bei Philips Hue)
        max_brightness = 254
        brightness_change = int(max_brightness * (percent_change / 100))
        new_brightness = current_brightness + brightness_change
        
        # Begrenze auf gültigen Bereich
        new_brightness = max(0, min(254, new_brightness))
        
        # Setze die neue Helligkeit
        return await self.set_group_brightness(group_id, new_brightness)

async def main():
    bridge = Bridge.connect_by_ip()
    
    # Sternenlicht aktivieren und 15% heller machen, alles in einem Aufruf
    result = await bridge.activate_scene_by_name("Sternenlicht")
    
    import time
    time.sleep(10)
    
    await bridge.adjust_brightness(25)
    
    print(f"Szene 'Sternenlicht' wurde aktiviert und um 15% heller gemacht.")
    
    return result

if __name__ == "__main__":
    result = asyncio.run(main())