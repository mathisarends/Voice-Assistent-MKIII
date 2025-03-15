from typing import Dict
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.hue_light import HueLight
from tools.lights.core.light_command_builder import LightCommandBuilder
from tools.lights.commands import LightCommandGroup, SetBrightnessCommand, TurnOnCommand


async def setup_lights(bridge: Bridge) -> Dict[str, HueLight]:
    """
    Richtet alle verfügbaren Lampen ein und gibt sie in einem Dictionary zurück.
    
    Args:
        bridge: Eine verbundene Bridge-Instanz
        
    Returns:
        Dictionary mit Lampen-IDs als Schlüssel und HueLight-Instanzen als Werte
    """
    light_data = await bridge.get_lights()
    lights = {}
    
    for light_id, data in light_data.items():
        light = HueLight(bridge, light_id, data.get("name", f"Lampe {light_id}"))
        await light.initialize()
        lights[light_id] = light
        
        print(f"Lampe initialisiert: {light.name} (ID: {light_id}, Typ: {light.device_type}, Modell: {light.model_id})")
    
    return lights


# Beispiele für die Verwendung
async def example_usage():
    # Bridge initialisieren (mit eigener IP-Adresse)
    bridge = Bridge.connect_by_ip("192.168.1.100")
    
    # Alle Lampen einrichten
    lights = await setup_lights(bridge)
    
    # Beispiel 1: Einfacher Befehl für eine Lampe
    lightstrip = lights.get("1")  # Hue Lightstrip
    if lightstrip:
        # Direkter Aufruf von Methoden (intern werden Commands erstellt)
        await lightstrip.turn_on()
        await lightstrip.set_color_preset("blau")
        
        # Oder explizite Erstellung von Commands
        await lightstrip.execute_command(SetBrightnessCommand(80))
    
    # Beispiel 2: Komplexes Szenario mit CommandBuilder
    candle_light = lights.get("5")  # E14 Kerzenlampe
    if candle_light:
        # Kerzenlicht-Effekt aktivieren
        candle_command = LightCommandBuilder.create_candlelight_command()
        await candle_light.execute_command(candle_command)
    
    # Beispiel 3: Synchronisiere mehrere Lampen
    sync_command = LightCommandBuilder.create_sync_group_command("gemütlich", 70)
    for light in lights.values():
        await light.execute_command(sync_command)
    
    custom_group = LightCommandGroup([
        TurnOnCommand(),
        SetBrightnessCommand(90),
        SetColorTemperatureCommand(2700)
    ])
    
    for light_id in ["5", "6", "7"]:  # Alle E14 Kerzenlampen
        if light_id in lights:
            await lights[light_id].execute_command(custom_group)
            
            
if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())