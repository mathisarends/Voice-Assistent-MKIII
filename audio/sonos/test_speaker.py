#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path

from audio.sonos.sonos_manager import SonosAudioManager

# Füge das Projektverzeichnis zum Python-Pfad hinzu
project_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, str(project_dir))

from audio.sonos.sonos_http_server import start_http_server, stop_http_server

def main():
    print("=== Sonos Audio Manager Demo ===")
    
    # Pfad zum Audio-Verzeichnis relativ zum Projektverzeichnis
    audio_dir = "audio/sounds"
    
    # Starte den HTTP-Server auf dem Projektverzeichnis
    print("\n1. Starte HTTP-Server...")
    http_server = start_http_server(project_dir)
    
    # Wenn der Server nicht gestartet wurde, beenden
    if not http_server.is_running():
        print("Fehler beim Starten des HTTP-Servers. Beende...")
        return
    
    print("\n2. Initialisiere Sonos Audio Manager...")
    # Initialisiere den Sonos Audio Manager mit dem Audio-Verzeichnis
    try:
        # Übergebe die HTTP-Server-Konfiguration an den SonosAudioManager
        sonos_manager = SonosAudioManager(
            root_dir=audio_dir, 
            http_server_port=http_server.port
        )
    except Exception as e:
        print(f"Fehler beim Initialisieren des Sonos Audio Managers: {e}")
        stop_http_server()
        return
    
    # Suche nach verfügbaren Sonos-Lautsprechern
    print("\n3. Suche nach Sonos-Lautsprechern...")
    try:
        speakers = sonos_manager.get_all_sonos_speakers()
        print(f"\nGefundene Sonos-Lautsprecher: {len(speakers)}")
        for i, speaker in enumerate(speakers):
            print(f"   {i+1}. {speaker['name']} ({speaker['ip']})")
        
        if not speakers:
            print("Keine Sonos-Lautsprecher gefunden!")
            selection = input("\nMöchtest du trotzdem fortfahren? (j/n): ")
            if selection.lower() != 'j':
                print("Beende...")
                stop_http_server()
                return
        else:
            # Lasse den Benutzer einen Lautsprecher auswählen
            selection = input("\nWähle einen Lautsprecher (Nummer) oder drücke Enter für den ersten: ")
            if selection and selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(speakers):
                    speaker = speakers[idx]
                    print(f"Wähle Lautsprecher: {speaker['name']}")
                    sonos_manager.select_speaker(speaker_ip=speaker['ip'])
    except Exception as e:
        print(f"Fehler bei der Sonos-Suche: {e}")
    
    # Überprüfe, ob ein Sonos-Gerät verfügbar ist
    if not sonos_manager.sonos_device:
        print("\nKein Sonos-Lautsprecher ausgewählt oder verfügbar.")
        selection = input("Möchtest du trotzdem fortfahren und die Sounds auflisten? (j/n): ")
        if selection.lower() != 'j':
            print("Beende...")
            stop_http_server()
            return
    
    try:
        # Zeige alle verfügbaren Sounds
        print("\n4. Verfügbare Sounds:")
        if not sonos_manager.sound_map:
            print("Keine Sounds gefunden!")
            print(f"Überprüfe das Verzeichnis: {project_dir / audio_dir}")
            stop_http_server()
            return
        
        # Zeige alle verfügbaren Soundkategorien
        categories = set(info["category"] for info in sonos_manager.sound_map.values())
        for category in sorted(categories):
            sounds = sonos_manager.get_sounds_by_category(category)
            print(f"\nKategorie: {category} ({len(sounds)} Sounds)")
            
            # Zeige alle Sounds in dieser Kategorie
            for i, (sound_id, info) in enumerate(sounds.items()):
                print(f"   {i+1}. {sound_id} ({info['filename']})")
                # Zeige auch die URL an, um zu prüfen, ob sie korrekt ist
                print(f"      URL: {info['url']}")
        
        # Wenn kein Sonos-Gerät verfügbar ist, beenden
        if not sonos_manager.sonos_device:
            print("\nKein Sonos-Lautsprecher verfügbar zum Abspielen. Beende...")
            stop_http_server()
            return
        
        # Interaktive Schleife zum Abspielen von Sounds
        while True:
            print("\n5. Sound abspielen:")
            print("   a) Bestimmten Sound abspielen")
            print("   b) Sound im Loop abspielen")
            print("   c) Test-URL abspielen")
            print("   d) Beenden")
            
            choice = input("\nWähle eine Option (a/b/c/d): ").lower()
            
            if choice == 'd':
                break
            elif choice == 'a':
                sound_id = input("Gib die Sound-ID ein: ")
                if sound_id in sonos_manager.sound_map:
                    volume = float(input("Lautstärke (0.0-1.0): ") or "0.5")
                    print(f"Spiele '{sound_id}' mit Lautstärke {volume} ab...")
                    sonos_manager.play(sound_id, block=True, volume=volume)
                else:
                    print(f"Sound '{sound_id}' nicht gefunden!")
            elif choice == 'b':
                sound_id = input("Gib die Sound-ID ein: ")
                if sound_id in sonos_manager.sound_map:
                    duration = float(input("Dauer in Sekunden: ") or "10")
                    volume = float(input("Lautstärke (0.0-1.0): ") or "0.5")
                    print(f"Spiele '{sound_id}' im Loop für {duration} Sekunden mit Lautstärke {volume}...")
                    sonos_manager.play_loop(sound_id, duration=duration, volume=volume)
                    
                    # Warte, bis der Loop beendet ist oder der Benutzer abbricht
                    print("Drücke Enter, um den Loop vorzeitig zu beenden...")
                    input()
                    sonos_manager.stop_loop()
                else:
                    print(f"Sound '{sound_id}' nicht gefunden!")
            elif choice == 'c':
                # Teste mit einer bekannten funktionierenden URL
                test_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
                print(f"Teste Sonos mit URL: {test_url}")
                volume = float(input("Lautstärke (0.0-1.0): ") or "0.3")
                
                # Setze Lautstärke
                sonos_volume = int(min(100, max(0, volume * 100)))
                sonos_manager.sonos_device.volume = sonos_volume
                
                # Spiele die Test-URL
                try:
                    sonos_manager.sonos_device.play_uri(test_url)
                    print("✅ Test-URL wird abgespielt. Drücke Enter zum Stoppen...")
                    input()
                    sonos_manager.sonos_device.stop()
                except Exception as e:
                    print(f"❌ Fehler beim Abspielen der Test-URL: {e}")
            else:
                print("Ungültige Option!")
        
        print("\nDemo beendet!")
        
    except KeyboardInterrupt:
        print("\nProgramm wurde vom Benutzer beendet.")
    finally:
        # Stoppe den HTTP-Server am Ende
        stop_http_server()

if __name__ == "__main__":
    main()