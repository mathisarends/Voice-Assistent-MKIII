import asyncio
import time
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.led_rgb_strip import RGBLightStrip


async def demonstrate_presets():
    bridge = await Bridge.connect()
    
    strip = RGBLightStrip(bridge, "1", "LED-Strip")
    await strip.initialize()
    
    # Gerät einschalten
    await strip.turn_on()
    print(f"LED-Strip {strip.name} eingeschaltet")
    
    # Alle verfügbaren Farbpresets anzeigen
    presets = strip.get_available_color_presets()
    print(f"\nVerfügbare Farb-Presets ({len(presets)}):")
    for i, preset in enumerate(sorted(presets)):
        print(f"- {preset}")
    
    # Einige Presets demonstrieren
    demo_colors = ["rot", "grün", "blau", "gelb", "orange", "türkis", "lila", "warmweiß", "gemütlich", "party"]
    
    print("\nStarte Farbpresets-Demo:")
    for color in demo_colors:
        print(f"\nSetze Farbe auf '{color}'")
        await strip.set_color_preset(color)
        current_status = await strip.get_status()
        print(f"Aktueller Status: {current_status}")
        time.sleep(2)  # Zeitverzögerung für bessere Sichtbarkeit
    
    # Sprachsteuerung simulieren
    print("\n=== Sprachsteuerung-Simulation ===")
    
    # Beispiel-Sprachanfragen
    voice_commands = [
        "Schalte das Licht auf Rot",
        "Mache das Licht blau",
        "Stelle die Farbe auf gemütlich",
        "Ändere die Beleuchtung auf Party-Modus"
    ]
    
    for command in voice_commands:
        print(f"\nSprachbefehl: \"{command}\"")
        # Einfache Textverarbeitung zur Extraktion des Farbnamens
        words = command.lower().split()
        # Suche nach einem Farbwort im Befehl
        for word in words:
            if word in presets:
                color = word
                break
        else:
            # Wenn kein exakter Match, versuche andere Varianten zu finden
            for preset in presets:
                if preset in command.lower():
                    color = preset
                    break
            else:
                print("Keine erkennbare Farbe im Befehl gefunden.")
                continue
        
        print(f"Erkannte Farbe: {color}")
        await strip.set_color_preset(color)
        current_status = await strip.get_status()
        print(f"Aktueller Status: {current_status}")
        time.sleep(2)
    
    print("\nDemo beendet.")


if __name__ == "__main__":
    asyncio.run(demonstrate_presets())