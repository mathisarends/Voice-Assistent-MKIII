import asyncio
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.hue_light import HueLight


async def demonstrate_transitions():
    bridge = await Bridge.connect()
    
    strip = HueLight(bridge, "1", "LED-Strip")
    await strip.initialize()
    
    # Gerät einschalten
    await strip.turn_on()
    print(f"LED-Strip {strip.name} eingeschaltet")
    
    # 1. Einfache Übergänge zwischen Grundfarben
    print("\nDemo 1: Einfache Farbübergänge mit verschiedenen Übergangszeiten")
    transitions = [
        ("red", 1.0),       # Rot mit 1 Sekunde Übergang
    ]
    
    for color, transition_time in transitions:
        print(f"Wechsle zu '{color}' mit {transition_time} Sekunden Übergangszeit")
        await strip.set_color_preset(color, transition_time)
        
        await strip.set_brightness(70)

if __name__ == "__main__":
    asyncio.run(demonstrate_transitions())