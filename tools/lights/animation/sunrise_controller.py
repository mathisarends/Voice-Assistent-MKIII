from __future__ import annotations

import asyncio
import math
from typing import List, Dict, Any, Tuple

from tools.lights.group_controller import GroupController
from tools.lights.light_controller import LightController
from tools.lights.scene_controller import SceneController

import asyncio
from tools.lights.bridge.bridge import HueBridge


class SceneBasedSunriseController:
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
        self.light_controller = LightController(bridge)
        self.group_controller = GroupController(bridge)
        self.scene_controller = SceneController(bridge)
        self.running_sunrise = None
        self.should_stop = False

    async def store_light_state(self, light_ids: List[str]) -> Dict[str, Any]:
        states = {}
        lights = await self.light_controller.get_all_lights()
        for light_id in light_ids:
            if light_id in lights:
                states[light_id] = lights[light_id]["state"]
        return states

    async def restore_light_state(self, light_states: Dict[str, Any]) -> None:
        for light_id, state in light_states.items():
            # Wir entfernen Statusfelder, die wir nicht setzen können
            restore_state = {
                k: v
                for k, v in state.items()
                if k in ["on", "bri", "hue", "sat", "xy", "ct", "effect", "colormode"]
            }
            await self.light_controller.set_light_state(light_id, restore_state)

    def stop_sunrise(self) -> None:
        self.should_stop = True
        if self.running_sunrise and not self.running_sunrise.done():
            self.running_sunrise.cancel()
        self.running_sunrise = None

    async def get_scene_light_states(
        self, scene_name: str
    ) -> Tuple[str, Dict[str, Dict[str, Any]]]:
        """
        Ermittelt die Zielzustände der Lichter in einer Szene

        Returns:
            Tuple[str, Dict[str, Dict[str, Any]]]: (group_id, {light_id: target_state, ...})
        """
        # Finde die Szene anhand des Namens
        scenes = await self.scene_controller.get_all_scenes()
        scene_id = None
        group_id = None

        for sid, scene_data in scenes.items():
            if scene_data.get("name") == scene_name:
                scene_id = sid
                group_id = scene_data.get("group")
                break

        if not scene_id or not group_id:
            raise ValueError(f"Szene mit Namen '{scene_name}' nicht gefunden")

        scene_details = await self.bridge.get_request(f"scenes/{scene_id}")

        target_states = {}
        if "lightstates" in scene_details:
            target_states = scene_details["lightstates"]

        return group_id, target_states

    async def start_scene_based_sunrise(
        self,
        scene_name: str = "Majestätischer Morgen",
        duration: int = 540,
        start_brightness_percent: float = 0.01,
        restore_original: bool = False,
    ) -> None:
        """
        Startet eine Sonnenaufgang-Simulation basierend auf einer bestehenden Szene

        Die Lichter werden mit der Farbkonfiguration der Szene gestartet, aber mit
        sehr geringer Helligkeit, die dann über die angegebene Dauer hinweg auf
        den in der Szene konfigurierten Wert erhöht wird.

        Args:
            scene_name: Name der zu verwendenden Szene
            duration: Dauer in Sekunden (Standard: 540 = 9 Minuten)
            start_brightness_percent: Anfängliche Helligkeit als Prozentsatz der Ziel-Helligkeit
            restore_original: Ob der ursprüngliche Zustand nach dem Sonnenaufgang wiederhergestellt werden soll
        """
        self.stop_sunrise()
        self.should_stop = False

        try:
            group_id, target_states = await self.get_scene_light_states(scene_name)
            target_light_ids = list(target_states.keys())

            print(
                f"Szene '{scene_name}' gefunden mit Gruppe {group_id} und {len(target_light_ids)} Lichtern"
            )

            original_states = {}
            if restore_original:
                original_states = await self.store_light_state(target_light_ids)

            # Starte die Animation in einem separaten Task
            self.running_sunrise = asyncio.create_task(
                self._run_scene_based_sunrise(
                    target_light_ids,
                    target_states,
                    duration,
                    start_brightness_percent,
                    original_states,
                )
            )

        except Exception as e:
            print(f"Fehler beim Starten des Szenen-basierten Sonnenaufgangs: {e}")
            raise

    async def _run_scene_based_sunrise(
        self,
        light_ids: List[str],
        target_states: Dict[str, Dict[str, Any]],
        duration: int,
        start_brightness_percent: float,
        original_states: Dict[str, Any],
    ) -> None:
        """
        Führt die eigentliche Szenen-basierte Sonnenaufgang-Animation durch
        """
        try:
            print(
                f"Starte Szenen-basierten Sonnenaufgang für {len(light_ids)} Lichter über {duration} Sekunden..."
            )

            # Schalte die Lichter initial ein mit der Szenen-Farbe aber minimaler Helligkeit
            for light_id in light_ids:
                if light_id in target_states:
                    target_state = target_states[light_id]

                    # Bestimme die Anfangshelligkeit basierend auf der Zielhelligkeit
                    target_brightness = target_state.get("bri", 254)
                    initial_brightness = max(
                        1, int(target_brightness * start_brightness_percent)
                    )

                    # Erstelle eine Kopie des Zielzustands mit reduzierter Helligkeit
                    initial_state = target_state.copy()
                    initial_state["bri"] = initial_brightness

                    # Wende den initialen Zustand an
                    await self.light_controller.set_light_state(light_id, initial_state)

            # Kurze Pause, um sicherzustellen, dass die Lichter an sind
            await asyncio.sleep(0.5)

            # Anzahl der Schritte basierend auf der Dauer
            steps = min(180, max(30, duration // 3))
            step_duration = duration / steps

            for step in range(1, steps + 1):
                if self.should_stop:
                    break

                # Exponentieller Fortschritt für natürlicheren Sonnenaufgang
                progress = math.pow(
                    step / steps, 2
                )  # Quadratische Funktion für exponentielles Wachstum

                # Aktualisiere die Helligkeit jedes Lichts
                for light_id in light_ids:
                    if light_id in target_states:
                        target_state = target_states[light_id]
                        target_brightness = target_state.get("bri", 254)
                        initial_brightness = max(
                            1, int(target_brightness * start_brightness_percent)
                        )

                        # Berechne aktuelle Helligkeit
                        current_brightness = int(
                            initial_brightness
                            + (target_brightness - initial_brightness) * progress
                        )
                        current_brightness = max(1, min(254, current_brightness))

                        # Setze nur die Helligkeit, behalte alle anderen Werte bei
                        await self.light_controller.set_light_state(
                            light_id,
                            {
                                "bri": current_brightness,
                                "transitiontime": int(
                                    step_duration * 10
                                ),  # In 0.1s Einheiten
                            },
                        )

                # Warte bis zum nächsten Schritt
                await asyncio.sleep(step_duration)

            print("Sonnenaufgang abgeschlossen!")

            # Stelle den ursprünglichen Zustand wieder her, falls gewünscht
            if original_states and not self.should_stop:
                await self.restore_light_state(original_states)

        except asyncio.CancelledError:
            print("Sonnenaufgang wurde abgebrochen.")
        except Exception as e:
            print(f"Fehler im Sonnenaufgang: {e}")

            # Versuche im Fehlerfall den ursprünglichen Zustand wiederherzustellen
            if original_states:
                try:
                    await self.restore_light_state(original_states)
                except Exception as restore_error:
                    print(
                        f"Fehler bei der Wiederherstellung des Zustands: {restore_error}"
                    )
