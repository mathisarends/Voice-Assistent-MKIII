import asyncio
from tools.lights.hue.bridge import Bridge

async def get_user_id():
    bridges = await Bridge.discover()
    if not bridges:
        print("Keine Hue Bridge gefunden!")
        return
    
    bridge_ip = bridges[0]["internalipaddress"]
    print(f"Bridge gefunden: {bridge_ip}")
    
    print("WICHTIG: Drücken Sie jetzt den Link-Button auf Ihrer Hue Bridge!")
    print("Sie haben 30 Sekunden Zeit...")
    await asyncio.sleep(20)
    
    try:
        user_id = await Bridge.create_user(bridge_ip, "meine_hue_app")
        print(f"Erfolg! Ihre User-ID lautet: {user_id}")
        print("SPEICHERN SIE DIESE ID! Sie benötigen sie für alle zukünftigen Anfragen.")
        return user_id
    except RuntimeError as e:
        print(f"Fehler: {e}")
        print("Haben Sie den Link-Button gedrückt?")
        return None

if __name__ == "__main__":
    user_id = asyncio.run(get_user_id())