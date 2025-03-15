from __future__ import annotations

import asyncio
import math
from typing import List, Dict, Any

from tools.lights.hue.group_controller import GroupController
from tools.lights.hue.light_controller import LightController

import asyncio
import signal
import sys
import argparse
from datetime import datetime, timedelta
from tools.lights.hue.bridge import HueBridge

class SunriseController:
    """Verantwortlich für Tageslichtwecker-Funktionalität"""
    
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
        self.light_controller = LightController(bridge)
        self.group_controller = GroupController(bridge)
        self.running_sunrise = None
        self.should_stop = False
    
    async def store_light_state(self, light_ids: List[str]) -> Dict[str, Any]:
        """Speichert den aktuellen Zustand mehrerer Lichter"""
        states = {}
        lights = await self.light_controller.get_all_lights()
        for light_id in light_ids:
            if light_id in lights:
                states[light_id] = lights[light_id]["state"]
        return states
    
    async def restore_light_state(self, light_states: Dict[str, Any]) -> None:
        """Stellt den gespeicherten Zustand mehrerer Lichter wieder her"""
        for light_id, state in light_states.items():
            # Wir entfernen Statusfelder, die wir nicht setzen können
            restore_state = {k: v for k, v in state.items() 
                            if k in ['on', 'bri', 'hue', 'sat', 'xy', 'ct', 'effect', 'colormode']}
            await self.light_controller.set_light_state(light_id, restore_state)
    
    def stop_sunrise(self) -> None:
        """Stoppt den laufenden Sonnenaufgang"""
        self.should_stop = True
        if self.running_sunrise and not self.running_sunrise.done():
            self.running_sunrise.cancel()
        self.running_sunrise = None
    
    async def start_sunrise(self, 
                            light_ids: List[str] = None, 
                            group_id: str = None,
                            duration: int = 540,  # 9 Minuten in Sekunden
                            start_ct: int = 500,  # Warmes, rötliches Licht
                            end_ct: int = 300,    # Neutrales, weißeres Licht
                            start_brightness: int = 1,
                            end_brightness: int = 254,
                            restore_original: bool = False) -> None:
        """
        Startet eine Sonnenaufgang-Simulation
        
        Args:
            light_ids: IDs der zu steuernden Lichter (entweder light_ids oder group_id angeben)
            group_id: ID der zu steuernden Gruppe (entweder light_ids oder group_id angeben)
            duration: Dauer in Sekunden (Standard: 540 = 9 Minuten)
            start_ct: Anfängliche Farbtemperatur (500 = sehr warm, 153 = sehr kühl)
            end_ct: Endgültige Farbtemperatur
            start_brightness: Anfängliche Helligkeit (1-254)
            end_brightness: Endgültige Helligkeit (1-254)
            restore_original: Ob der ursprüngliche Zustand nach dem Sonnenaufgang wiederhergestellt werden soll
        """
        # Stoppe eventuell laufenden Sonnenaufgang
        self.stop_sunrise()
        self.should_stop = False
        
        # Bestimme die zu steuernden Lichter
        target_lights = []
        original_states = {}
        
        if group_id:
            # Hole Lichter aus der Gruppe
            groups = await self.group_controller.get_all_groups()
            if group_id in groups and "lights" in groups[group_id]:
                target_lights = groups[group_id]["lights"]
        elif light_ids:
            target_lights = light_ids
        else:
            # Verwende Standardgruppe (alle Lichter)
            groups = await self.group_controller.get_all_groups()
            if "0" in groups and "lights" in groups["0"]:
                target_lights = groups["0"]["lights"]
        
        # Speichere ursprünglichen Zustand, falls gewünscht
        if restore_original:
            original_states = await self.store_light_state(target_lights)
        
        # Starte die Animation in einem separaten Task
        self.running_sunrise = asyncio.create_task(
            self._run_sunrise(target_lights, duration, start_ct, end_ct, 
                             start_brightness, end_brightness, original_states)
        )
    
    async def _run_sunrise(self, 
                          light_ids: List[str],
                          duration: int,
                          start_ct: int,
                          end_ct: int,
                          start_brightness: int,
                          end_brightness: int,
                          original_states: Dict[str, Any]) -> None:
        """
        Führt die eigentliche Sonnenaufgang-Animation durch
        
        Diese Methode erhöht schrittweise die Helligkeit und ändert die Farbtemperatur
        in einem exponentiellen Verlauf, der einem natürlichen Sonnenaufgang ähnelt.
        """
        try:
            print(f"Starte Sonnenaufgang für {len(light_ids)} Lichter über {duration} Sekunden...")
            
            # Schalte die Lichter initial ein mit minimaler Helligkeit
            for light_id in light_ids:
                await self.light_controller.set_light_state(light_id, {
                    "on": True,
                    "bri": start_brightness,
                    "ct": start_ct,
                    "transitiontime": 1  # Schneller Übergang (0.1s)
                })
            
            # Kurze Pause, um sicherzustellen, dass die Lichter an sind
            await asyncio.sleep(0.5)
            
            # Anzahl der Schritte basierend auf der Dauer
            # Ein Update etwa alle 3 Sekunden ist gut für flüssige Animation
            steps = min(180, max(30, duration // 3))
            step_duration = duration / steps
            
            for step in range(1, steps + 1):
                if self.should_stop:
                    break
                
                # Exponentieller Fortschritt für natürlicheren Sonnenaufgang
                # Zu Beginn langsamer, dann schneller zunehmend
                progress = math.pow(step / steps, 2)  # Quadratische Funktion für exponentielles Wachstum
                
                # Berechne aktuelle Helligkeit und Farbtemperatur
                current_brightness = int(start_brightness + (end_brightness - start_brightness) * progress)
                current_ct = int(start_ct - (start_ct - end_ct) * progress)
                
                # Stelle sicher, dass die Werte im gültigen Bereich liegen
                current_brightness = max(1, min(254, current_brightness))
                current_ct = max(153, min(500, current_ct))
                
                # Aktualisiere Lichter
                for light_id in light_ids:
                    await self.light_controller.set_light_state(light_id, {
                        "bri": current_brightness,
                        "ct": current_ct,
                        "transitiontime": int(step_duration * 10)  # In 0.1s Einheiten
                    })
                
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
                    print(f"Fehler bei der Wiederherstellung des Zustands: {restore_error}")


# wake_up_light.py



# Globale Variable für den Controller
sunrise_controller = None

def signal_handler(sig, frame):
    """Handler für Strg+C"""
    print("\nBreche Sonnenaufgang ab...")
    if sunrise_controller:
        sunrise_controller.stop_sunrise()
    sys.exit(0)

async def wait_until(target_time):
    """Wartet bis zur angegebenen Zeit"""
    now = datetime.now()
    if now.time() > target_time.time():
        # Zielzeit ist morgen
        target_time = datetime.combine(now.date() + timedelta(days=1), target_time.time())
    else:
        # Zielzeit ist heute
        target_time = datetime.combine(now.date(), target_time.time())
    
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        print(f"Warte auf Startzeit {target_time.strftime('%H:%M:%S')} ({wait_seconds:.1f} Sekunden)...")
        await asyncio.sleep(wait_seconds)

async def main():
    # Kommandozeilenargumente verarbeiten
    parser = argparse.ArgumentParser(description='Philips Hue Tageslichtwecker')
    parser.add_argument('--duration', type=int, default=30, help='Dauer in Sekunden (Standard: 540)')
    parser.add_argument('--group', type=str, help='Gruppen-ID')
    parser.add_argument('--lights', type=str, help='Komma-getrennte Liste von Licht-IDs')
    args = parser.parse_args()

    try:
        # Verbinde mit der Bridge
        bridge = HueBridge.connect_by_ip()
        
        # Erstelle den Sunrise-Controller
        sunrise_controller = SunriseController(bridge)
        
        # Bestimme die zu steuernden Lichter
        lights = None
        if args.lights:
            lights = args.lights.split(',')
        else:
            # Wenn keine Lichter angegeben wurden, verwende diese Standardliste
            lights = ["1", "5", "6", "7"]  # Deine gewünschten Standardlampen
        
        print(f"Starte Sonnenaufgang für folgende Lichter: {lights}")
        
        # Starte den Sonnenaufgang
        await sunrise_controller.start_sunrise(
            light_ids=lights,
            group_id=args.group,
            duration=args.duration
        )
        
        # Warte auf Abschluss
        while sunrise_controller.running_sunrise and not sunrise_controller.running_sunrise.done():
            await asyncio.sleep(1)
        
        print("Tageslichtwecker beendet.")
        
    except Exception as e:
        print(f"Fehler: {e}")
        if 'sunrise_controller' in locals():
            sunrise_controller.stop_sunrise()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())