from __future__ import annotations

import threading
from typing import Any, List, Dict
import asyncio
from tools.lights.bridge.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.loggin_mixin import LoggingMixin  # Importiere den LightController
from audio.audio_manager import get_mapper, play

get_mapper()

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
        
    async def quick_error_flash(self, light_ids: List[str], transition_time: int = 2) -> None:
        """
        Erzeugt eine sehr kurze rote Fehleranimation für kurze Sounds.
        Die Animation blendet schnell zu Rot und direkt wieder zurück - 
        perfekt für 'ding-dong' artige kurze Fehlertöne.
        
        Args:
            light_ids: Liste der Lampen-IDs, die blinken sollen
            transition_time: Übergangszeit in Zehntelsekunden (0,1 Sekunden)
        """
        if not light_ids:
            self.logger.warning("Keine Lampen für die Fehleranimation angegeben")
            return
        
        # Speichere den aktuellen Zustand aller Lampen
        original_states = {}
        for light_id in light_ids:
            try:
                state = await self.controller.get_light_state(light_id)
                original_states[light_id] = state.copy()
            except Exception as e:
                self.logger.error(f"Fehler beim Abrufen des Zustands für Lampe {light_id}: {e}")
        
        # Heller roter Zustand mit sehr kurzer Übergangszeit
        red_state = {
            "on": True,
            "hue": 0,          # Rot in Hue-Farbsystem
            "sat": 254,        # Volle Sättigung
            "bri": 200,        # Mittlere Helligkeit (~78%)
            "transitiontime": transition_time
        }
        
        try:
            # Alle Lampen auf Rot setzen
            red_tasks = []
            for light_id in light_ids:
                red_tasks.append(self.controller.set_light_state(light_id, red_state))
            
            if red_tasks:
                await asyncio.gather(*red_tasks)
                
            # Warte nur minimal
            await asyncio.sleep(0.05)  # 50 Millisekunden
            
            # Sofort zurück zum Originalzustand
            restore_tasks = []
            for light_id, original_state in original_states.items():
                # Nur relevante Farbinformationen übernehmen und Übergangszeit hinzufügen
                restore_state = {}
                for key in ["on", "hue", "sat", "bri", "xy", "ct"]:
                    if key in original_state:
                        restore_state[key] = original_state[key]
                
                restore_state["transitiontime"] = transition_time
                restore_tasks.append(self.controller.set_light_state(light_id, restore_state))
            
            if restore_tasks:
                await asyncio.gather(*restore_tasks)
            
            self.logger.info(f"Kurze Fehleranimation für Lampen {light_ids} abgeschlossen")
        
        except Exception as e:
            self.logger.error(f"Fehler während der kurzen Fehleranimation: {e}")

    async def quick_error_with_sound(self, light_ids: List[str], sound_name: str = "error", 
                                    transition_time: int = 2) -> None:
        """
        Erzeugt einen schnellen roten Flash mit synchronem Sound - optimiert
        für sehr kurze Sounds wie Ding-Dong.
        
        Args:
            light_ids: Liste der Lampen-IDs, die blinken sollen
            sound_name: Name des abzuspielenden Sounds (Standard: "error")
            transition_time: Übergangszeit in Zehntelsekunden (0,1 Sekunden)
        """
        import threading
        
        # Sound parallel starten
        sound_thread = threading.Thread(target=play, args=(sound_name,))
        sound_thread.daemon = True
        sound_thread.start()
        
        # Kurze Lichtanimation ausführen
        await self.quick_error_flash(light_ids, transition_time)

async def main() -> None:
    bridge = HueBridge.connect_by_ip()
    controller = LightController(bridge)
    animation_service = LightAnimationService(controller)

    # Rotiere die Farben zwischen den Lampen 5, 6 und 7
    await animation_service.quick_error_with_sound(["5", "6", "7"], sound_name="error-1")
    
    import time
    await time.sleep(5)
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())