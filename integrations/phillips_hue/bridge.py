from __future__ import annotations

import os
from typing import Any, Optional

import aiohttp
from dotenv import load_dotenv


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
    def connect_by_ip(
        cls, ip: Optional[str] = None, user_id: Optional[str] = None
    ) -> HueBridge:
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



class BridgeDiscovery:
    """Verantwortlich für das Auffinden und Konfigurieren von Hue Bridges"""

    @staticmethod
    async def discover_bridges() -> list[dict[str, str]]:
        """Findet alle verfügbaren Hue Bridges im Netzwerk"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discovery.meethue.com/") as response:
                return await response.json()

    @staticmethod
    def get_credentials() -> tuple[str, str]:
        """Lädt die Bridge-IP und User-ID aus Umgebungsvariablen"""
        load_dotenv()
        bridge_ip = os.getenv("HUE_BRIDGE_IP")
        user_id = os.getenv("HUE_USER_ID")

        if not user_id:
            raise ValueError("Kein HUE_USER_ID in .env gefunden")

        return bridge_ip, user_id
