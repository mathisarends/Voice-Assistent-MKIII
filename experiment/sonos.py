import soco
import time

# Mit dem Sonos-Speaker verbinden
sonos_ip = "192.168.178.68"  # Ihre gefundene IP-Adresse
speaker = soco.SoCo(sonos_ip)

# Grundlegende Informationen anzeigen
print(f"Verbunden mit: {speaker.player_name}")
print(f"Aktuelle Lautstärke: {speaker.volume}")
print(f"Ist stumm geschaltet: {speaker.mute}")
print(f"Aktueller Status: {speaker.get_current_transport_info()['current_transport_state']}")

# Lautstärke ändern
speaker.volume = 20  # Lautstärke auf 20% setzen
print(f"Neue Lautstärke: {speaker.volume}")

# Einen Song abspielen
print("Spiele einen Song von TuneIn ab...")
speaker.play_uri('x-sonosapi-stream:s24861?sid=254&flags=32', title="Radio 1")

# Warten, damit der Song anfangen kann zu spielen
time.sleep(20)

speaker.pause()