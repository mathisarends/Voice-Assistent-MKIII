from __future__ import annotations

from typing import Any
from tools.lights.bridge import HueBridge

class LightController:
    """Verantwortlich für die Steuerung einzelner Lichter"""
    
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
    
    async def get_all_lights(self) -> dict[str, Any]:
        """Alle Lampen abrufen"""
        return await self.bridge.get_request("lights")
    
    async def set_light_state(self, light_id: str, state: dict) -> list:
        """Zustand einer Lampe ändern"""
        return await self.bridge.put_request(f"lights/{light_id}/state", state)
    
async def main() -> None:
    bridge = HueBridge.connect_by_ip()
    controller = LightController(bridge)
    
    lights = await controller.get_all_lights()
    print(lights)
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())