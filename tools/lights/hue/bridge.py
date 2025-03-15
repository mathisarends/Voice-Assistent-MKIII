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
            
    @staticmethod
    async def find_hue_bridge() -> str:
        bridges = await Bridge.discover()
        
        if not bridges:
            print("Keine Hue Bridge im Netzwerk gefunden!")
            return
        
        print(f"Gefundene Hue Bridges: {len(bridges)}")
        
        for i, bridge in enumerate(bridges, 1):
            print(f"Bridge {i}:")
            print(f"  IP-Adresse: {bridge['internalipaddress']}")
            if 'id' in bridge:
                print(f"  ID: {bridge['id']}")

async def main():
    bridge = Bridge.connect_by_ip()
    return await bridge.get_lights()

if __name__ == "__main__":
    lights = asyncio.run(main())
    print(lights)