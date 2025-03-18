from __future__ import annotations

from typing import Any, List, Dict
import asyncio
from tools.lights.bridge.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.loggin_mixin import LoggingMixin  # Importiere den LightController

class LightAnimationService(LoggingMixin):
    def __init__(self, controller: LightController) -> None:
        """
        Initialisiert den AnimationsService mit einem LightController
        
        Args:
            controller: Eine Instanz des LightControllers für Lampenzugriff
        """
        self.controller = controller
    
    async def rotate_colors(self, light_ids: List[str], transition_time: int = 15, dim_percentage: float = 0.7) -> None:
        if len(light_ids) < 2:
            print("Mindestens zwei Lampen für die Rotation erforderlich")
            return
        
        color_states: Dict[str, Dict[str, Any]] = {}
        for light_id in light_ids:
            state = await self.controller.get_light_state(light_id)
            color_info = {}
            for key in ["on", "hue", "sat", "bri", "xy", "ct"]:
                if key in state:
                    color_info[key] = state[key]
            color_states[light_id] = color_info
        
        # Schneller Übergang für die Abdunkelung
        dim_transition = max(1, transition_time // 2)
        
        # Schritt 1: Reduziere die Helligkeit bei allen Lampen
        dim_tasks = []
        for light_id, state in color_states.items():
            if "bri" in state:
                dim_state = {
                    "bri": int(state["bri"] * dim_percentage),
                    "transitiontime": dim_transition
                }
                dim_tasks.append(self.controller.set_light_state(light_id, dim_state))
        
        if dim_tasks:
            await asyncio.gather(*dim_tasks)
            await asyncio.sleep(dim_transition / 10)
        
        rotated_states = {}
        for i, light_id in enumerate(light_ids):
            next_index = (i + 1) % len(light_ids)
            next_light_id = light_ids[next_index]
            rotated_states[light_id] = color_states[next_light_id].copy()
        
        for light_id, state in rotated_states.items():
            state["transitiontime"] = transition_time
        
        tasks = []
        for light_id, state in rotated_states.items():
            tasks.append(self.controller.set_light_state(light_id, state))
        
        await asyncio.gather(*tasks)
        print(f"Farben zwischen {light_ids} rotiert mit kurzzeitiger Helligkeitsreduzierung")

async def main() -> None:
    bridge = HueBridge.connect_by_ip()
    controller = LightController(bridge)
    animation_service = LightAnimationService(controller)
    
    # Rotiere die Farben zwischen den Lampen 5, 6 und 7
    await animation_service.rotate_colors(["5", "6", "7"])

    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())