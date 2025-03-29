from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type

from tools.lights.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.loggin_mixin import LoggingMixin


class AnimationType(Enum):
    """Aufzählung der verfügbaren Animationstypen"""
    ROTATE = auto()
    ERROR_FLASH = auto()
    PULSE = auto()
    WAKE_FLASH = auto() 


@dataclass
class AnimationConfig:
    """Basis-Konfigurationsklasse für alle Animationen"""
    transition_time: int = 10
    hold_time: float = 0.1
    interval: float = 1.0
    
    def validate(self) -> None:
        """Validiert die Konfigurationswerte"""
        if self.transition_time < 0:
            raise ValueError("Übergangszeit muss positiv sein")
        if self.hold_time < 0:
            raise ValueError("Haltezeit muss positiv sein")
        if self.interval <= 0:
            raise ValueError("Intervall muss größer als 0 sein")


@dataclass
class RotateConfig(AnimationConfig):
    """Konfiguration für die Farbrotation"""
    dim_percentage: float = 0.0
    
    def validate(self) -> None:
        super().validate()
        if not 0 <= self.dim_percentage <= 1:
            raise ValueError("Dimmfaktor muss zwischen 0 und 1 liegen")


@dataclass
class ErrorFlashConfig(AnimationConfig):
    """Konfiguration für die Fehler-Blitz-Animation"""
    flash_interval: float = 1.0
    hue: int = 0
    saturation: int = 254
    brightness: int = 200

    def validate(self) -> None:
        super().validate()
        if self.flash_interval <= 0:
            raise ValueError("Blitzintervall muss größer als 0 sein")
        if not 0 <= self.hue <= 65535:
            raise ValueError("Farbton muss zwischen 0 und 65535 liegen")
        if not 0 <= self.saturation <= 254:
            raise ValueError("Sättigung muss zwischen 0 und 254 liegen")
        if not 0 <= self.brightness <= 254:
            raise ValueError("Helligkeit muss zwischen 0 und 254 liegen")


@dataclass
class PulseConfig(AnimationConfig):
    """Konfiguration für die Pulsanimation"""
    max_increase_pct: float = 10.0
    steps: int = 10
    step_time: float = 0.1

    def validate(self) -> None:
        super().validate()
        if self.max_increase_pct <= 0:
            raise ValueError("Maximale Erhöhung muss größer als 0 sein")
        if self.steps <= 0:
            raise ValueError("Anzahl der Schritte muss größer als 0 sein")
        if self.step_time <= 0:
            raise ValueError("Zeit zwischen Schritten muss größer als 0 sein")


@dataclass
class WakeFlashConfig(AnimationConfig):
    """Konfiguration für die Wake-Flash-Animation"""
    brightness_increase: int = 50
    transition_time_up: int = 1
    transition_time_down: int = 8
    
    def validate(self) -> None:
        super().validate()
        if self.brightness_increase <= 0:
            raise ValueError("Helligkeitserhöhung muss größer als 0 sein")
        if self.transition_time_up < 0:
            raise ValueError("Übergangszeit nach oben muss positiv sein")
        if self.transition_time_down < 0:
            raise ValueError("Übergangszeit nach unten muss positiv sein")


class LightAnimationFactory:
    """Fabrik zur Erzeugung von Lichtanimationen"""

    def __init__(self, controller: LightController):
        self.controller = controller
        
        self._animation_classes: Dict[AnimationType, Type[LightAnimation]] = {
            AnimationType.ERROR_FLASH: ErrorFlashAnimation,
            AnimationType.WAKE_FLASH: WakeFlashAnimation,
        }
        
        self._animation_instances: Dict[AnimationType, LightAnimation] = {}

    def get_animation(self, animation_type: AnimationType) -> LightAnimation:
        """Erzeugt oder gibt eine bestehende Animation des angegebenen Typs zurück"""
        if animation_type not in self._animation_classes:
            raise ValueError(f"Nicht unterstützter Animationstyp: {animation_type}")
        
        if animation_type not in self._animation_instances:
            animation_class = self._animation_classes[animation_type]
            self._animation_instances[animation_type] = animation_class(self.controller)
            
        return self._animation_instances[animation_type]


class LightAnimation(ABC, LoggingMixin):
    """Basisklasse für alle Lichtanimationen"""

    def __init__(self, controller: LightController):
        self.controller = controller
        self._stop_event = asyncio.Event()
        self._running_task: Optional[asyncio.Task] = None
        self._original_states: Dict[str, Dict[str, Any]] = {}

    @abstractmethod
    async def _execute_once(self, light_ids: List[str], config: AnimationConfig) -> None:
        """Führt die Animation einmal aus"""
        pass
    
    async def _save_light_states(self, light_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Speichert den aktuellen Zustand aller angegebenen Lampen"""
        states = {}
        for light_id in light_ids:
            try:
                state = await self.controller.get_light_state(light_id)
                states[light_id] = state.copy()
            except Exception as e:
                self.logger.error(f"Fehler beim Abrufen des Zustands für Lampe {light_id}: {e}")
                states[light_id] = {"on": True, "bri": 127}
        return states
    
    async def _restore_light_states(self, states: Dict[str, Dict[str, Any]], transition_time: int = 10) -> None:
        """Stellt die gespeicherten Zustände der Lampen wieder her"""
        restore_tasks = []
        for light_id, original_state in states.items():
            restore_state = {}
            for key in ["on", "hue", "sat", "bri", "xy", "ct"]:
                if key in original_state:
                    restore_state[key] = original_state[key]

            restore_state["transitiontime"] = transition_time
            restore_tasks.append(self.controller.set_light_state(light_id, restore_state))

        if restore_tasks:
            await asyncio.gather(*restore_tasks)

    async def execute(
        self,
        light_ids: List[str],
        continuous: bool = False,
        config: Optional[AnimationConfig] = None,
    ) -> None:
        """
        Führt die Animation aus

        Args:
            light_ids: Liste der Lampen-IDs
            continuous: Wenn True, läuft die Animation kontinuierlich,
                       bis stop() aufgerufen wird
            config: Konfiguration für die Animation
        """
        if not light_ids:
            self.logger.warning("Keine Lampen für die Animation angegeben")
            return
        
        if config is None:
            config = self._get_default_config()
        
        try:
            config.validate()
        except ValueError as e:
            self.logger.error(f"Ungültige Konfiguration: {e}")
            return
            
        await self.stop()
        self._stop_event.clear()

        self._original_states = await self._save_light_states(light_ids)

        if continuous:
            self._running_task = asyncio.create_task(
                self._run_continuous(light_ids, config)
            )
        else:
            await self._execute_once(light_ids, config)

    @abstractmethod
    def _get_default_config(self) -> AnimationConfig:
        """Gibt die Standardkonfiguration für diese Animation zurück"""
        pass

    async def _run_continuous(
        self, light_ids: List[str], config: AnimationConfig
    ) -> None:
        """Interne Methode für kontinuierliche Animationsausführung"""
        try:
            while not self._stop_event.is_set():
                await self._execute_once(light_ids, config)

                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=config.interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            if not self._stop_event.is_set():
                await self._restore_light_states(self._original_states)
            self.logger.info(f"Kontinuierliche Animation für {light_ids} beendet")

    async def stop(self) -> None:
        """Stoppt eine laufende Animation"""
        if self._running_task and not self._running_task.done():
            self._stop_event.set()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
            self._running_task = None


class WakeFlashAnimation(LightAnimation):
    """Animation für kurzes Aufleuchten als visuelle Bestätigung bei Wake Word-Erkennung"""

    def _get_default_config(self) -> AnimationConfig:
        return WakeFlashConfig()

    async def _execute_once(self, light_ids: List[str], config: AnimationConfig) -> None:
        """Führt eine einmalige Wake-Animation aus - kurzes Aufleuchten der Lampen"""
        if not isinstance(config, WakeFlashConfig):
            config = WakeFlashConfig()
            
        states = await self._save_light_states(light_ids)
        
        current_brightness = {}
        for light_id, state in states.items():
            if "bri" in state and state.get("on", False):
                current_brightness[light_id] = state["bri"]
            else:
                current_brightness[light_id] = 127

        try:
            brighter_states = {}
            for light_id, current_bri in current_brightness.items():
                new_brightness = min(254, current_bri + config.brightness_increase)
                
                brighter_states[light_id] = {
                    "on": True,
                    "bri": new_brightness,
                    "transitiontime": config.transition_time_up
                }

            brighten_tasks = []
            for light_id, bright_state in brighter_states.items():
                brighten_tasks.append(self.controller.set_light_state(light_id, bright_state))

            if brighten_tasks:
                await asyncio.gather(*brighten_tasks)
                
            await asyncio.sleep(config.hold_time)

            await self._restore_light_states(states, config.transition_time_down)

            self.logger.info(f"Wake-Animation für Lampen {light_ids} abgeschlossen")

        except Exception as e:
            self.logger.error(f"Fehler während der Wake-Animation: {e}")
            await self._restore_light_states(states)


class ErrorFlashAnimation(LightAnimation):
    """Animation für kurze Fehleranimation mit rotem Blitz"""

    def _get_default_config(self) -> AnimationConfig:
        return ErrorFlashConfig()

    async def _execute_once(self, light_ids: List[str], config: AnimationConfig) -> None:
        """Führt eine einmalige Fehleranimation aus"""
        if not isinstance(config, ErrorFlashConfig):
            config = ErrorFlashConfig()

        states = await self._save_light_states(light_ids)

        color_state = {
            "on": True,
            "hue": config.hue,
            "sat": config.saturation,
            "bri": config.brightness,
            "transitiontime": config.transition_time,
        }

        try:
            flash_tasks = []
            for light_id in light_ids:
                flash_tasks.append(self.controller.set_light_state(light_id, color_state))

            if flash_tasks:
                await asyncio.gather(*flash_tasks)

            await asyncio.sleep(config.hold_time)

            await self._restore_light_states(states, config.transition_time)

            self.logger.info(f"Fehler-Blitz-Animation für Lampen {light_ids} abgeschlossen")

        except Exception as e:
            self.logger.error(f"Fehler während der Fehler-Blitz-Animation: {e}")
            await self._restore_light_states(states)


async def main() -> None:
    bridge = HueBridge.connect_by_ip()
    controller = LightController(bridge)

    factory = LightAnimationFactory(controller)
    error_anim = factory.get_animation(AnimationType.ERROR_FLASH)
    wake_anim = factory.get_animation(AnimationType.WAKE_FLASH)
    
    await wake_anim.execute(
        ["5", "6", "7"],
        config=WakeFlashConfig(
            brightness_increase=50,
            transition_time_up=1,
            transition_time_down=8,
            hold_time=0.5
        )
    )
    
    await asyncio.sleep(5)

    await error_anim.execute(
        ["5", "6", "7"],
        config=ErrorFlashConfig(transition_time=2, hold_time=0.5)
    )


if __name__ == "__main__":
    asyncio.run(main())