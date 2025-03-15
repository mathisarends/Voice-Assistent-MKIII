# hue/animation.py
from __future__ import annotations

import asyncio
import random
from typing import List, Dict, Any

from tools.lights.hue.bridge import HueBridge
from tools.lights.hue.light_controller import LightController

class AnimationController:
    """Verantwortlich für Lichtanimationen"""
    
    def __init__(self, bridge: HueBridge) -> None:
        self.bridge = bridge
        self.light_controller = LightController(bridge)
        self.running_animations = {}
        
    async def store_light_state(self, light_ids: List[str]) -> Dict[str, Any]:
        """Speichert den aktuellen Zustand mehrerer Lichter"""
        states = {}
        for light_id in light_ids:
            lights = await self.light_controller.get_all_lights()
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
    
    def _stop_animation(self, animation_id: str) -> None:
        """Stoppt eine laufende Animation"""
        if animation_id in self.running_animations:
            task = self.running_animations[animation_id]
            if not task.done():
                task.cancel()
            del self.running_animations[animation_id]
    
    async def stop_all_animations(self) -> None:
        """Stoppt alle laufenden Animationen"""
        for animation_id in list(self.running_animations.keys()):
            self._stop_animation(animation_id)


class ThinkingAnimation(AnimationController):
    """Animation für den 'Nachdenken'-Modus"""
    
    def __init__(self, bridge: HueBridge, light_ids: List[str] = None) -> None:
        super().__init__(bridge)
        self.light_ids = light_ids or ["5", "6", "7"]  # Standard-Lichter für die Animation
        self.original_states = {}
        self.animation_task = None
        self.animation_id = "thinking"
    
    async def start(self) -> None:
        """Startet die Nachdenken-Animation"""
        # Stoppe die Animation, falls sie bereits läuft
        self._stop_animation(self.animation_id)
        
        # Speichere den aktuellen Zustand
        self.original_states = await self.store_light_state(self.light_ids)
        
        # Starte die Animation in einem separaten Task
        self.animation_task = asyncio.create_task(self._run_animation())
        self.running_animations[self.animation_id] = self.animation_task
    
    async def stop(self) -> None:
        """Stoppt die Animation und stellt den ursprünglichen Zustand wieder her"""
        self._stop_animation(self.animation_id)
        
        # Stelle den ursprünglichen Zustand wieder her
        if self.original_states:
            await self.restore_light_state(self.original_states)
            self.original_states = {}
    
    async def _run_animation(self) -> None:
        """Führt die eigentliche Animation aus"""
        try:
            # Hole den aktuellen Farbmodus und Farbwerte, um ähnliche Farben zu generieren
            base_colors = {}
            lights = await self.light_controller.get_all_lights()
            
            for light_id in self.light_ids:
                if light_id in lights:
                    state = lights[light_id]["state"]
                    if state.get("colormode") == "xy":
                        base_colors[light_id] = {
                            "mode": "xy",
                            "xy": state.get("xy", [0.5, 0.5]),
                            "bri": state.get("bri", 254)
                        }
                    elif state.get("colormode") == "hs":
                        base_colors[light_id] = {
                            "mode": "hs",
                            "hue": state.get("hue", 0),
                            "sat": state.get("sat", 254),
                            "bri": state.get("bri", 254)
                        }
                    elif state.get("colormode") == "ct":
                        base_colors[light_id] = {
                            "mode": "ct",
                            "ct": state.get("ct", 366),
                            "bri": state.get("bri", 254)
                        }
                    else:
                        base_colors[light_id] = {
                            "mode": "bri",
                            "bri": state.get("bri", 254)
                        }
            
            # Animation-Schleife
            while True:
                for light_id in self.light_ids:
                    if light_id in base_colors:
                        await self._animate_light(light_id, base_colors[light_id])
                
                # Kurze Pause zwischen Animationsschritten
                await asyncio.sleep(1.0)
        
        except asyncio.CancelledError:
            # Animation wurde abgebrochen
            pass
        except Exception as e:
            print(f"Fehler in der Animation: {e}")
    
    async def _animate_light(self, light_id: str, base_color: Dict[str, Any]) -> None:
        """Animiert ein einzelnes Licht basierend auf seinen Grundfarbwerten"""
        mode = base_color.get("mode", "bri")
        
        if mode == "xy":
            # XY-Farbmodus
            xy = base_color.get("xy", [0.5, 0.5])
            bri = base_color.get("bri", 254)
            
            # Kleine zufällige Änderung der Farbe
            new_xy = [
                max(0, min(1, xy[0] + random.uniform(-0.03, 0.03))),
                max(0, min(1, xy[1] + random.uniform(-0.03, 0.03)))
            ]
            
            # Kleine zufällige Änderung der Helligkeit
            new_bri = max(100, min(254, bri + random.randint(-15, 15)))
            
            # Wende neue Werte an
            await self.light_controller.set_light_state(light_id, {
                "xy": new_xy,
                "bri": new_bri,
                "transitiontime": 10  # Sanfter Übergang (1s)
            })
            
        elif mode == "hs":
            # Farbton/Sättigung-Modus
            hue = base_color.get("hue", 0)
            sat = base_color.get("sat", 254)
            bri = base_color.get("bri", 254)
            
            # Kleine zufällige Änderung des Farbtons
            new_hue = (hue + random.randint(-2000, 2000)) % 65535
            
            # Kleine zufällige Änderung der Sättigung
            new_sat = max(150, min(254, sat + random.randint(-20, 20)))
            
            # Kleine zufällige Änderung der Helligkeit
            new_bri = max(100, min(254, bri + random.randint(-15, 15)))
            
            # Wende neue Werte an
            await self.light_controller.set_light_state(light_id, {
                "hue": new_hue,
                "sat": new_sat,
                "bri": new_bri,
                "transitiontime": 10  # Sanfter Übergang (1s)
            })
            
        elif mode == "ct":
            # Farbtemperatur-Modus
            ct = base_color.get("ct", 366)
            bri = base_color.get("bri", 254)
            
            # Kleine zufällige Änderung der Farbtemperatur
            new_ct = max(153, min(500, ct + random.randint(-20, 20)))
            
            # Kleine zufällige Änderung der Helligkeit
            new_bri = max(100, min(254, bri + random.randint(-15, 15)))
            
            # Wende neue Werte an
            await self.light_controller.set_light_state(light_id, {
                "ct": new_ct,
                "bri": new_bri,
                "transitiontime": 10  # Sanfter Übergang (1s)
            })
            
        else:
            # Nur Helligkeit
            bri = base_color.get("bri", 254)
            
            # Kleine zufällige Änderung der Helligkeit
            new_bri = max(100, min(254, bri + random.randint(-20, 20)))
            
            # Wende neue Werte an
            await self.light_controller.set_light_state(light_id, {
                "bri": new_bri,
                "transitiontime": 10  # Sanfter Übergang (1s)
            })


# assistant_thinking_animation.py
import asyncio
import signal
import sys

# Globale Variable für die Animation
thinking_animation = None

async def start_thinking():
    """Startet die Denkanimation"""
    global thinking_animation
    
    print("Starte 'Nachdenken'-Animation...")
    bridge = HueBridge.connect_by_ip()
    thinking_animation = ThinkingAnimation(bridge)
    await thinking_animation.start()
    
    return thinking_animation

async def stop_thinking():
    """Stoppt die Denkanimation"""
    global thinking_animation
    
    if thinking_animation:
        print("Stoppe 'Nachdenken'-Animation...")
        await thinking_animation.stop()
        thinking_animation = None

def signal_handler(sig, frame):
    """Handler für Strg+C"""
    print("\nBeende Animation...")
    asyncio.run(stop_thinking())
    sys.exit(0)

async def main():
    # Registriere Signal-Handler für sauberes Beenden
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Starte die Animation
        animation = await start_thinking()
        
        print("Animation läuft. Drücke Strg+C zum Beenden...")
        
        # Warte auf Benutzerunterbrechung oder eine bestimmte Zeit
        try:
            # Hier könnten wir auf ein Ereignis warten oder einfach für eine bestimmte Zeit laufen
            await asyncio.sleep(60)  # Animation für 60 Sekunden laufen lassen
        except asyncio.CancelledError:
            pass
        
        # Stoppe die Animation
        await stop_thinking()
        
    except Exception as e:
        print(f"Fehler: {e}")
        if thinking_animation:
            await stop_thinking()

if __name__ == "__main__":
    asyncio.run(main())