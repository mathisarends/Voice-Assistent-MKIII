import asyncio
import time
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.led_rgb_strip import RGBLightStrip, ColorPresets


async def demonstrate_transitions():
    bridge = await Bridge.connect()
    
    strip = RGBLightStrip(bridge, "1", "LED-Strip")
    await strip.initialize()
    
    # Gerät einschalten
    await strip.turn_on()
    print(f"LED-Strip {strip.name} eingeschaltet")
    
    # 1. Einfache Übergänge zwischen Grundfarben
    print("\nDemo 1: Einfache Farbübergänge mit verschiedenen Übergangszeiten")
    transitions = [
        ("rot", 1.0),       # Rot mit 1 Sekunde Übergang
        ("grün", 2.0),      # Grün mit 2 Sekunden Übergang
        ("blau", 4.0),      # Blau mit 4 Sekunden Übergang
        ("weiß", 0.5)       # Weiß mit 0.5 Sekunden Übergang
    ]
    
    for color, transition_time in transitions:
        print(f"Wechsle zu '{color}' mit {transition_time} Sekunden Übergangszeit")
        await strip.set_color_preset(color, transition_time)
        # Warten Sie die Übergangszeit plus etwas extra
        await asyncio.sleep(transition_time + 0.5)
    
    # 2. Regenbogen-Effekt
    print("\nDemo 2: Regenbogen-Effekt")
    rainbow = ["rot", "orange", "gelb", "grün", "türkis", "blau", "lila"]
    
    for color in rainbow:
        print(f"Übergang zu '{color}'")
        await strip.set_color_preset(color, 1.0)
        await asyncio.sleep(1.5)  # 1 Sekunde Übergangszeit + 0.5 Sekunden Pause
    
    # 3. Stimmungswechsel
    print("\nDemo 3: Stimmungswechsel")
    moods = [
        ("entspannung", "Entspannungsmodus aktiviert"),
        ("konzentration", "Konzentrationsmodus aktiviert"),
        ("gemütlich", "Gemütlicher Modus aktiviert"),
        ("party", "Party-Modus aktiviert")
    ]
    
    for mood, message in moods:
        print(message)
        await strip.set_color_preset(mood, 3.0)  # Langsamer Übergang für Stimmungen
        await asyncio.sleep(4.0)  # 3 Sekunden Übergang + 1 Sekunde Pause
    
    # 4. Pulsierender Effekt mit einer Farbe
    print("\nDemo 4: Pulsierender Effekt")
    # Wir verwenden hier direkt RGB-Werte für verschiedene Helligkeitsstufen von Rot
    pulse_color = "rot"
    print(f"Pulsierender Effekt mit Farbe '{pulse_color}'")
    
    # Stelle sicher, dass wir mit der Basisfarbe starten
    await strip.set_color_preset(pulse_color, 0.0)
    await asyncio.sleep(1.0)
    
    # Durchlaufe verschiedene Helligkeitsstufen
    for _ in range(3):  # 3 Pulse
        # Reduziere die Helligkeit
        await strip.set_brightness(30)
        await asyncio.sleep(0.8)
        
        # Erhöhe die Helligkeit
        await strip.set_brightness(100)
        await asyncio.sleep(0.8)
    
    # 5. Automatische Farbrotation (könnte in einer realen Anwendung endlos laufen)
    print("\nDemo 5: Automatische Farbrotation")
    rotation_colors = ["rot", "grün", "blau", "gelb", "magenta", "cyan"]
    
    print("Starte automatische Farbrotation (5 Sekunden)...")
    start_time = time.time()
    
    # In einer realen Anwendung könnte dies in einer Schleife laufen, bis der Benutzer stoppt
    while time.time() - start_time < 5:
        for color in rotation_colors:
            await strip.set_color_preset(color, 0.5)
            await asyncio.sleep(0.7)  # 0.5 Sekunden Übergang + 0.2 Sekunden Pause
            
            # Prüfe, ob die Gesamtzeit überschritten wurde
            if time.time() - start_time >= 5:
                break
    
    print("\nDemo beendet.")
    # Zurück zu Weiß mit sanftem Übergang
    await strip.set_color_preset("weiß", 2.0)
    
    await strip.turn_off()


if __name__ == "__main__":
    asyncio.run(demonstrate_transitions())