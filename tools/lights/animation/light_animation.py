from __future__ import annotations

import asyncio
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, cast

from singleton_decorator import singleton

from tools.lights.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.loggin_mixin import LoggingMixin


class AnimationType(Enum):
    """Aufzählung der verfügbaren Animationstypen"""
    ERROR_FLASH = auto()
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
class WakeFlashConfig(AnimationConfig):
    """Konfiguration für die Wake-Flash-Animation"""
    brightness_increase: int = 40
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
    
    def get_wake_flash_animation(self) -> WakeFlashAnimation:
        """Gibt eine spezialisierte WakeFlashAnimation zurück"""
        animation = self.get_animation(AnimationType.WAKE_FLASH)
        return cast(WakeFlashAnimation, animation)


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

@singleton
class WakeFlashAnimation(LightAnimation):
    """Animation für kurzes Aufleuchten als visuelle Bestätigung bei Wake Word-Erkennung
    mit separater Kontrolle über Start und Stop der Animation"""

    def __init__(self, controller: LightController):
        super().__init__(controller)
        self._active_light_ids = []
        self._brightness_state = {}

    def _get_default_config(self) -> AnimationConfig:
        return WakeFlashConfig()

    async def start_flash(self, light_ids: List[str], config: Optional[WakeFlashConfig] = None) -> None:
        """Startet die Wake-Animation durch Erhöhen der Helligkeit.
        
        Args:
            light_ids: Liste der Lampen-IDs für die Animation
            config: Optional, spezifische Konfiguration für diese Animation
        """
        if not light_ids:
            self.logger.warning("Keine Lampen für die Animation angegeben")
            return
            
        if config is None:
            config = self._get_default_config()
            
        if not isinstance(config, WakeFlashConfig):
            config = WakeFlashConfig()
            
        try:
            config.validate()
        except ValueError as e:
            self.logger.error(f"Ungültige Konfiguration: {e}")
            return

        self._active_light_ids = light_ids
        
        self._brightness_state = await self._save_light_states(light_ids)
        
        # Berechne erhöhte Helligkeit für alle Lampen
        brighter_states = {}
        for light_id, state in self._brightness_state.items():
            current_bri = state.get("bri", 127) if state.get("on", False) else 127
            new_brightness = min(254, current_bri + config.brightness_increase)
            
            brighter_states[light_id] = {
                "on": True,
                "bri": new_brightness,
                "transitiontime": config.transition_time_up
            }

        # Führe die Helligkeitserhöhung durch
        brighten_tasks = []
        for light_id, bright_state in brighter_states.items():
            brighten_tasks.append(self.controller.set_light_state(light_id, bright_state))

        if brighten_tasks:
            await asyncio.gather(*brighten_tasks)
            
        self.logger.info(f"Wake-Animation gestartet für Lampen {light_ids}")

    async def stop_flash(self, transition_time: Optional[int] = None) -> None:
        """Beendet die Wake-Animation durch Zurücksetzen der Helligkeit.
        
        Args:
            transition_time: Optional, spezifische Übergangszeit für das Abblenden
        """
        if not self._active_light_ids or not self._brightness_state:
            return
            
        config = self._get_default_config()
        if not isinstance(config, WakeFlashConfig):
            config = WakeFlashConfig()
            
        transition_time_down = transition_time if transition_time is not None else config.transition_time_down
        
        try:
            await self._restore_light_states(self._brightness_state, transition_time_down)
            self.logger.info(f"Wake-Animation beendet für Lampen {self._active_light_ids}")
        except Exception as e:
            self.logger.error(f"Fehler beim Beenden der Wake-Animation: {e}")
        finally:
            self._active_light_ids = []
            self._brightness_state = {}

    async def _execute_once(self, light_ids: List[str], config: AnimationConfig) -> None:
        if not isinstance(config, WakeFlashConfig):
            config = WakeFlashConfig()
        
        await self.start_flash(light_ids, config)
        await asyncio.sleep(config.hold_time)
        await self.stop_flash(config.transition_time_down)


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
    wake_anim = typing.cast(WakeFlashAnimation, factory.get_animation(AnimationType.WAKE_FLASH))
    
    print("Teste normale execute() Methode (Kompletter Zyklus):")
    await wake_anim.execute(
        ["5", "6", "7"],
        config=WakeFlashConfig(
            brightness_increase=50,
            transition_time_up=1,
            transition_time_down=8,
            hold_time=0.5
        )
    )
    
    # Warte zwischen den Demonstrationen
    await asyncio.sleep(3)
    
    print("\nTeste separate start_flash() und stop_flash() Methoden:")
    print("1. Starte Aufblenden...")
    await wake_anim.start_flash(
        ["1", "5", "6", "7"],
        config=WakeFlashConfig(
            brightness_increase=70,  # Stärkere Helligkeitserhöhung
            transition_time_up=2     # Langsamer aufblenden
        )
    )
    
    # Simuliere einen Zeitraum für die Spracherkennung
    print("2. Lampen bleiben hell während Spracherkennung...")
    await asyncio.sleep(4)
    
    # Abblenden mit benutzerdefinierter Übergangszeit
    print("3. Starte Abblenden...")
    await wake_anim.stop_flash(transition_time=10)  # Langsames Abblenden
    
    print("Demo abgeschlossen!")

if __name__ == "__main__":
    asyncio.run(main())