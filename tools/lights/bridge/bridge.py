from __future__ import annotations
import aiohttp
from typing import Any, Optional

from tools.lights.bridge.bridge_discovery import BridgeDiscovery

class HueBridge:
    """Basisklasse für die Kommunikation mit der Hue Bridge"""

    def __init__(self, ip: str, user: str) -> None:
        self.ip = ip
        self.user = user
    
    def __repr__(self) -> str:
        return f"<HueBridge {self.ip}>"

    @property
    def url(self) -> str:
        return f"http://{self.ip}/api/{self.user}"
    
    @classmethod
    async def connect(cls) -> HueBridge:
        """Verbindet mit der ersten gefundenen Bridge"""
        bridges = await BridgeDiscovery.discover_bridges()
        if not bridges:
            raise ValueError("Keine Hue Bridge gefunden")
        
        ip, user_id = BridgeDiscovery.get_credentials()
        return cls(ip=bridges[0]["internalipaddress"], user=user_id)
    
    @classmethod
    def connect_by_ip(cls, ip: Optional[str] = None, user_id: Optional[str] = None) -> HueBridge:
        """Verbindet mit einer Bridge über IP-Adresse"""
        if ip is None or user_id is None:
            fallback_ip, fallback_user = BridgeDiscovery.get_credentials()
            ip = ip or fallback_ip
            user_id = user_id or fallback_user
            
        return cls(ip=ip, user=user_id)
    
    async def get_request(self, endpoint: str) -> Any:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/{endpoint}") as response:
                return await response.json()
    
    async def put_request(self, endpoint: str, data: dict) -> Any:
        async with aiohttp.ClientSession() as session:
            async with session.put(f"{self.url}/{endpoint}", json=data) as response:
                return await response.json()