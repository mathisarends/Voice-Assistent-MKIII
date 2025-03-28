from __future__ import annotations

import os
import aiohttp
from dotenv import load_dotenv


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
