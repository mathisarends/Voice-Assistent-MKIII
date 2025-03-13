import asyncio
import time
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.led_rgb_strip import RGBLightStrip


async def main():
    bridge = await Bridge.connect()
    
    strip = RGBLightStrip(bridge, "1", "LED-Strip")
    await strip.initialize()
    
    # Die Properties nutzen
    print(f"Status: {strip.is_on}")
    print(f"Farbe: {strip.color}")
    print(f"Helligkeit: {strip.brightness}%")
    
    # Status als typisiertes Dictionary erhalten
    status = await strip.get_status()
    print(status.color_rgb)  # Typsichere Verwendung
    
    await strip.turn_on()
    
    # Farbe setzen
    await strip.set_color_rgb(255, 100, 50)  # Rot
    
    time.sleep(10)
    
    # Helligkeit ändern
    await strip.set_brightness(75)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())