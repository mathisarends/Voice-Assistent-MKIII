from __future__ import annotations

from tools.lights.bridge.bridge import HueBridge

class LightController:
    """Verantwortlich für die Steuerung einzelner Lichter"""
    
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
    
    async def get_all_lights(self) -> dict[str, Any]:
        return await self.bridge.get_request("lights")
    
    async def set_light_state(self, light_id: str, state: dict) -> list:
        return await self.bridge.put_request(f"lights/{light_id}/state", state)
    
    async def get_light_state(self, light_id: str) -> dict[str, Any]:
        light_data = await self.bridge.get_request(f"lights/{light_id}")
        return light_data.get("state", {})