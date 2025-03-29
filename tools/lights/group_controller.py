from __future__ import annotations

from typing import Any

from tools.lights.bridge import HueBridge


class GroupController:
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge

    async def get_all_groups(self) -> dict[str, Any]:
        return await self.bridge.get_request("groups")

    async def set_group_state(self, group_id: str, state: dict) -> list:
        return await self.bridge.put_request(f"groups/{group_id}/action", state)

    async def set_group_brightness(self, group_id: str, brightness: int) -> list:
        brightness = max(0, min(254, brightness))
        return await self.set_group_state(group_id, {"bri": brightness})

    async def get_active_group(self) -> str:
        groups = await self.get_all_groups()

        target_group = "0"

        for group_id, group_data in groups.items():
            if group_data.get("state", {}).get("any_on", False):
                target_group = group_id
                break

        return target_group
