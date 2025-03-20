from __future__ import annotations

import asyncio
import threading
from typing import Any, List, Dict, Protocol, Optional, Callable, Awaitable
from abc import ABC, abstractmethod
from tools.lights.bridge.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.loggin_mixin import LoggingMixin

# Basisklasse für Animationen mit erweiterter Funktionalität
class LightAnimation(ABC, LoggingMixin):
    """Basisklasse für alle Lichtanimationen"""
    
    def __init__(self, controller: LightController):
        self.controller = controller
        self._stop_event = asyncio.Event()
        self._running_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def _execute_once(self, light_ids: List[str], **kwargs) -> None:
        """Führt die Animation einmal aus"""
        pass
    
    async def execute(self, light_ids: List[str], continuous: bool = False, interval: float = 1.0, **kwargs) -> None:
        """
        Führt die Animation aus
        
        Args:
            light_ids: Liste der Lampen-IDs
            continuous: Wenn True, läuft die Animation kontinuierlich,
                        bis stop() aufgerufen wird
            interval: Zeit in Sekunden zwischen Wiederholungen bei kontinuierlicher Ausführung
            **kwargs: Weitere Parameter für die Animation
        """
        await self.stop()
        
        self._stop_event.clear()
        
        if continuous:
            self._running_task = asyncio.create_task(
                self._run_continuous(light_ids, interval, **kwargs)
            )
        else:
            # Führe die Animation einmal aus
            await self._execute_once(light_ids, **kwargs)
    
    async def _run_continuous(self, light_ids: List[str], interval: float, **kwargs) -> None:
        """Interne Methode für kontinuierliche Animationsausführung"""
        try:
            while not self._stop_event.is_set():
                # Führe eine einzelne Animation aus
                await self._execute_once(light_ids, **kwargs)
                
                # Warte auf das nächste Intervall oder bis zum Stopp
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=interval
                    )
                except asyncio.TimeoutError:
                    # Timeout bedeutet, das Intervall ist abgelaufen, aber das Stop-Event
                    # wurde nicht gesetzt, also machen wir weiter
                    pass
        finally:
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


class RotateColorsAnimation(LightAnimation):
    """Animation zum Rotieren von Farben zwischen Lampen"""
    
    async def _execute_once(self, light_ids: List[str], transition_time: int = 15, 
                          dim_percentage: float = 0.0) -> None:
        """
        Führt eine einmalige Farbrotation aus
        
        Args:
            light_ids: Liste der Lampen-IDs
            transition_time: Übergangszeit in Zehntelsekunden
            dim_percentage: Prozentsatz der Helligkeitsreduzierung (0.0 = keine Reduzierung)
        """
        if len(light_ids) < 2:
            self.logger.warning("Mindestens zwei Lampen für die Rotation erforderlich")
            return
        
        # Speichere aktuelle Farbzustände
        color_states: Dict[str, Dict[str, Any]] = {}
        for light_id in light_ids:
            state = await self.controller.get_light_state(light_id)
            color_info = {}
            for key in ["on", "hue", "sat", "bri", "xy", "ct"]:
                if key in state:
                    color_info[key] = state[key]
            color_states[light_id] = color_info
        
        # Optional: Reduziere die Helligkeit, falls gewünscht
        if dim_percentage > 0:
            dim_transition = max(1, transition_time // 2)
            dim_tasks = []
            
            for light_id, state in color_states.items():
                if "bri" in state:
                    dim_state = {
                        "bri": int(state["bri"] * (1 - dim_percentage)),
                        "transitiontime": dim_transition
                    }
                    dim_tasks.append(self.controller.set_light_state(light_id, dim_state))
            
            if dim_tasks:
                await asyncio.gather(*dim_tasks)
                await asyncio.sleep(dim_transition / 10)
        
        # Berechne die rotierten Zustände
        rotated_states = {}
        for i, light_id in enumerate(light_ids):
            next_index = (i + 1) % len(light_ids)
            next_light_id = light_ids[next_index]
            rotated_states[light_id] = color_states[next_light_id].copy()
            rotated_states[light_id]["transitiontime"] = transition_time
        
        # Setze die rotierten Zustände
        tasks = []
        for light_id, state in rotated_states.items():
            tasks.append(self.controller.set_light_state(light_id, state))
        
        await asyncio.gather(*tasks)
        self.logger.info(f"Farben zwischen {light_ids} rotiert" + 
                         (f" mit {dim_percentage*100}% Helligkeitsreduzierung" if dim_percentage > 0 else ""))


class ErrorFlashAnimation(LightAnimation):
    """Animation für kurze Fehleranimation mit rotem Blitz"""
    
    async def _execute_once(self, light_ids: List[str], transition_time: int = 2, 
                          hold_time: float = 0.05) -> None:
        """
        Führt eine einmalige Fehleranimation aus
        
        Args:
            light_ids: Liste der Lampen-IDs
            transition_time: Übergangszeit in Zehntelsekunden
            hold_time: Zeit in Sekunden, die im roten Zustand gehalten wird
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
        
        # Heller roter Zustand
        red_state = {
            "on": True,
            "hue": 0,          # Rot
            "sat": 254,        # Volle Sättigung
            "bri": 200,        # Mittlere Helligkeit
            "transitiontime": transition_time
        }
        
        try:
            # Alle Lampen auf Rot setzen
            red_tasks = []
            for light_id in light_ids:
                red_tasks.append(self.controller.set_light_state(light_id, red_state))
            
            if red_tasks:
                await asyncio.gather(*red_tasks)
                
            # Warte im roten Zustand
            await asyncio.sleep(hold_time)
            
            # Zurück zum Originalzustand
            restore_tasks = []
            for light_id, original_state in original_states.items():
                restore_state = {}
                for key in ["on", "hue", "sat", "bri", "xy", "ct"]:
                    if key in original_state:
                        restore_state[key] = original_state[key]
                
                restore_state["transitiontime"] = transition_time
                restore_tasks.append(self.controller.set_light_state(light_id, restore_state))
            
            if restore_tasks:
                await asyncio.gather(*restore_tasks)
            
            self.logger.info(f"Fehleranimation für Lampen {light_ids} abgeschlossen")
        
        except Exception as e:
            self.logger.error(f"Fehler während der Fehleranimation: {e}")
            
    async def execute(self, light_ids: List[str], continuous: bool = False, 
                    flash_interval: float = 1.0, **kwargs) -> None:
        """
        Überschreibt die Standard-execute-Methode, um flash_interval als speziellen Parameter zu nutzen
        
        Args:
            light_ids: Liste der Lampen-IDs
            continuous: Wenn True, läuft die Animation kontinuierlich, bis stop() aufgerufen wird
            flash_interval: Zeit in Sekunden zwischen Blitzen (nur für kontinuierliche Ausführung)
            **kwargs: Weitere Parameter für die Animation
        """
        # Stoppe eine eventuell laufende Animation
        await self.stop()
        
        # Setze das Stop-Event zurück
        self._stop_event.clear()
        
        if continuous:
            # Starte eine kontinuierliche Animation
            self._running_task = asyncio.create_task(
                self._execute_continuous(light_ids, flash_interval=flash_interval, **kwargs)
            )
        else:
            # Führe die Animation einmal aus
            await self._execute_once(light_ids, **kwargs)
            
    async def _execute_continuous(self, light_ids: List[str], transition_time: int = 2, 
                                hold_time: float = 0.05, flash_interval: float = 1.0) -> None:
        """
        Führt eine kontinuierliche Fehleranimation aus
        
        Args:
            light_ids: Liste der Lampen-IDs
            transition_time: Übergangszeit in Zehntelsekunden
            hold_time: Zeit in Sekunden, die im roten Zustand gehalten wird
            flash_interval: Zeit in Sekunden zwischen Blitzen
        """
        try:
            while not self._stop_event.is_set():
                # Führe einen einzelnen Blitz aus
                await self._execute_once(light_ids, transition_time, hold_time)
                
                # Warte auf das nächste Intervall oder bis zum Stopp
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=flash_interval
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            self.logger.info(f"Kontinuierliche Fehleranimation für {light_ids} beendet")


class PulseAnimation(LightAnimation):
    """Animation zum Pulsieren der Helligkeit einer Lampe"""
    
    async def _execute_once(self, light_ids: List[str], max_increase_pct: float = 10.0, 
                          steps: int = 10, step_time: float = 0.1) -> None:
        """
        Führt eine einmalige Pulsanimation aus
        
        Args:
            light_ids: Liste der Lampen-IDs
            max_increase_pct: Maximale prozentuale Erhöhung der aktuellen Helligkeit (z.B. 10.0 für 10%)
            steps: Anzahl der Schritte für einen Zyklus
            step_time: Zeit in Sekunden zwischen einzelnen Schritten
        """
        if not light_ids:
            self.logger.warning("Keine Lampen für die Pulsanimation angegeben")
            return
        
        # Speichere den aktuellen Zustand aller Lampen und bestimme die aktuellen Helligkeiten
        original_states = {}
        current_brightness = {}
        
        for light_id in light_ids:
            try:
                state = await self.controller.get_light_state(light_id)
                original_states[light_id] = state.copy()
                
                # Bestimme aktuelle Helligkeit
                if "bri" in state and state.get("on", False):
                    current_brightness[light_id] = state["bri"]
                else:
                    # Standardwert, falls die Lampe aus ist oder keine Helligkeitsinformation hat
                    current_brightness[light_id] = 127
                    
            except Exception as e:
                self.logger.error(f"Fehler beim Abrufen des Zustands für Lampe {light_id}: {e}")
                current_brightness[light_id] = 127  # Standardwert bei Fehler
        
        try:
            # Für jede Lampe die min/max Helligkeiten basierend auf der aktuellen Helligkeit berechnen
            min_brightness = {}
            max_brightness = {}
            
            for light_id, current_bri in current_brightness.items():
                # Maximale Helligkeit: aktuelle Helligkeit + max_increase_pct%, aber nicht mehr als 254
                max_increase = int(current_bri * max_increase_pct / 100)
                max_brightness[light_id] = min(254, current_bri + max_increase)
                
                # Minimale Helligkeit: aktuelle Helligkeit
                min_brightness[light_id] = current_bri
            
            # Helligkeit von min zu max
            for i in range(steps):
                if self._stop_event.is_set():
                    break
                
                tasks = []
                for light_id in light_ids:
                    # Berechne Helligkeit für diese Lampe
                    min_bri = min_brightness[light_id]
                    max_bri = max_brightness[light_id]
                    brightness = min_bri + int((max_bri - min_bri) * (i / (steps - 1)))
                    
                    state = {"bri": brightness, "transitiontime": 1}  # Kurze Übergangszeit
                    tasks.append(self.controller.set_light_state(light_id, state))
                
                if tasks:
                    await asyncio.gather(*tasks)
                
                await asyncio.sleep(step_time)
            
            # Helligkeit von max zu min
            for i in range(steps):
                if self._stop_event.is_set():
                    break
                
                tasks = []
                for light_id in light_ids:
                    # Berechne Helligkeit für diese Lampe
                    min_bri = min_brightness[light_id]
                    max_bri = max_brightness[light_id]
                    brightness = max_bri - int((max_bri - min_bri) * (i / (steps - 1)))
                    
                    state = {"bri": brightness, "transitiontime": 1}
                    tasks.append(self.controller.set_light_state(light_id, state))
                
                if tasks:
                    await asyncio.gather(*tasks)
                
                await asyncio.sleep(step_time)
            
            # Originalzustand wiederherstellen
            if not self._stop_event.is_set():
                restore_tasks = []
                for light_id, original_state in original_states.items():
                    restore_state = {}
                    for key in ["on", "hue", "sat", "bri", "xy", "ct"]:
                        if key in original_state:
                            restore_state[key] = original_state[key]
                    
                    restore_state["transitiontime"] = 5  # Sanfter Übergang zurück
                    restore_tasks.append(self.controller.set_light_state(light_id, restore_state))
                
                if restore_tasks:
                    await asyncio.gather(*restore_tasks)
            
            self.logger.info(f"Pulsanimation für Lampen {light_ids} abgeschlossen")
        
        except Exception as e:
            self.logger.error(f"Fehler während der Pulsanimation: {e}")


# Beispiel für die Verwendung
async def main() -> None:
    bridge = HueBridge.connect_by_ip()
    controller = LightController(bridge)
    
    # Initialisiere die Animationen direkt
    rotate_anim = RotateColorsAnimation(controller)
    error_anim = ErrorFlashAnimation(controller)
    pulse_anim = PulseAnimation(controller)
    
    # Beispiel 1: Einmalige Farbrotation
    print("Starte einmalige Farbrotation...")
    await rotate_anim.execute(
        ["5", "6", "7"], 
        transition_time=15,
        dim_percentage=0.0
    )
    
    # Beispiel 2: Kontinuierliche Pulsanimation, die nach 10 Sekunden gestoppt wird
    print("Starte kontinuierliche Pulsanimation...")
    await pulse_anim.execute(
        ["5", "6", "7"], 
        continuous=True,
        interval=2.0,  # Intervall zwischen vollständigen Pulszyklen
        max_increase_pct=10.0,  # Maximal 10% Helligkeitserhöhung
        steps=15,
        step_time=0.1
    )
    
    # Warte 10 Sekunden
    print("Warte 10 Sekunden...")
    await asyncio.sleep(10)
    
    # Stoppe die Animation
    print("Stoppe Pulsanimation...")
    await pulse_anim.stop()
    
    # Beispiel 3: Fehleranimation
    print("Starte Fehleranimation...")
    await error_anim.execute(
        ["5", "6", "7"],
        transition_time=2,
        hold_time=0.5
    )

if __name__ == "__main__":
    asyncio.run(main())