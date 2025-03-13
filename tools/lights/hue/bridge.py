from __future__ import annotations

import asyncio
import os
from typing import Any
import aiohttp
from dotenv import load_dotenv


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
