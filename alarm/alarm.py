import time
import threading
import datetime
from typing import Optional, List, Dict, Callable
import random

from audio.audio_manager import stop, play_loop, stop_loop, get_mapper

class Alarm:
    """Eine Alarmklasse, die zu einem bestimmten Zeitpunkt Sounds abspielt."""
    
    def __init__(self):
        self.alarms: List[Dict] = []
        self.running = False
        self.alarm_thread = None
        
        self.audio_manager = get_mapper()
        
        # Standarddauer für die verschiedenen Phasen (in Sekunden)
        self.wake_up_duration = 30
        self.get_up_duration = 40
        
        # Pause zwischen Wake-Up und Get-Up (in Sekunden)
        self.snooze_duration = 540  # 9 Minuten
    
    def set_alarm(self, alarm_time: datetime.datetime, 
                  wake_sound_id: str, 
                  get_up_sound_id: str,
                  callback: Optional[Callable] = None) -> int:
        alarm_id = len(self.alarms)
        
        alarm = {
            "id": alarm_id,
            "time": alarm_time,
            "wake_sound_id": wake_sound_id,
            "get_up_sound_id": get_up_sound_id,
            "callback": callback,
            "triggered": False
        }
        
        self.alarms.append(alarm)
        
        print(f"⏰ Alarm #{alarm_id} gesetzt für {alarm_time.strftime('%H:%M:%S')} "
              f"(Wake: {wake_sound_id}, Get-up: {get_up_sound_id})")
        
        # Starte den Überwachungsthread, falls er noch nicht läuft
        if not self.running:
            self._start_monitoring()
            
        return alarm_id
    
    def set_alarm_in(self, seconds: int, 
                     wake_sound_id: Optional[str] = None, 
                     get_up_sound_id: Optional[str] = None,
                     callback: Optional[Callable] = None) -> int:
        """Setzt einen Alarm, der in X Sekunden ausgelöst wird."""
        alarm_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        return self.set_alarm(alarm_time, wake_sound_id, get_up_sound_id, callback)
    
    def cancel_alarm(self, alarm_id: int) -> bool:
        """Bricht einen Alarm ab."""
        for i, alarm in enumerate(self.alarms):
            if alarm["id"] == alarm_id and not alarm["triggered"]:
                self.alarms.pop(i)
                print(f"⏰ Alarm #{alarm_id} abgebrochen")
                return True
        return False
    
    def _get_random_sound(self, category: str) -> str:
        """Wählt einen zufälligen Sound aus der angegebenen Kategorie."""
        sounds = self.audio_manager.get_sounds_by_category(category)
        
        if not sounds:
            # Fallback, falls keine Sounds der Kategorie gefunden wurden
            print(f"⚠️ Keine Sounds in Kategorie '{category}' gefunden, verwende Standardsound")
            return "get-up-aurora" if category == "get_up_sounds" else "wake-up-bells"
        
        # Wähle einen zufälligen Sound aus
        sound_id = random.choice(list(sounds.keys()))
        return sound_id
    
    def _start_monitoring(self):
        """Startet den Überwachungsthread für Alarme."""
        self.running = True
        self.alarm_thread = threading.Thread(target=self._monitor_alarms, daemon=True)
        self.alarm_thread.start()
        print("⏰ Alarm-Überwachung gestartet")
    
    def _monitor_alarms(self):
        """Überwacht kontinuierlich die Alarme und löst sie zum richtigen Zeitpunkt aus."""
        while self.running:
            now = datetime.datetime.now()
            triggered_indices = []
            
            # Prüfe alle Alarme
            for i, alarm in enumerate(self.alarms):
                if not alarm["triggered"] and now >= alarm["time"]:
                    # Alarm in separatem Thread auslösen
                    threading.Thread(
                        target=self._trigger_alarm,
                        args=(alarm,),
                        daemon=True
                    ).start()
                    
                    alarm["triggered"] = True
                    triggered_indices.append(i)
            
            # Entferne getriggerte Alarme (in umgekehrter Reihenfolge)
            for i in sorted(triggered_indices, reverse=True):
                self.alarms.pop(i)
            
            # Kurz warten, um CPU-Last zu reduzieren
            time.sleep(0.5)
    
    def _trigger_alarm(self, alarm: Dict):
        """Löst einen Alarm aus und spielt die konfigurierten Sounds ab."""
        alarm_id = alarm["id"]
        wake_sound_id = alarm["wake_sound_id"]
        get_up_sound_id = alarm["get_up_sound_id"]
        
        print(f"⏰ ALARM #{alarm_id} wird ausgelöst!")
        
        try:
            # Phase 1: Wake-Up Sound für konfigurierte Dauer im Loop
            print(f"🔊 Spiele Wake-Up Sound '{wake_sound_id}' für {self.wake_up_duration} Sekunden...")
            play_loop(wake_sound_id, self.wake_up_duration)
            
            # Warte die Snooze-Zeit ab (9 Minuten)
            print(f"💤 Snooze für {self.snooze_duration} Sekunden...")
            time.sleep(self.snooze_duration)
            
            # Phase 2: Get-Up Sound für konfigurierte Dauer im Loop
            # Bei der Get-Up-Phase kann es auch eine "endlose" Schleife sein, die nur manuell beendet wird
            print(f"🔊 Spiele Get-Up Sound '{get_up_sound_id}' für {self.get_up_duration} Sekunden...")
            play_loop(get_up_sound_id, self.get_up_duration)
            
            print(f"⏰ Alarm #{alarm_id} abgeschlossen")
            
            # Callback aufrufen, falls konfiguriert
            if alarm["callback"]:
                alarm["callback"]()
                
        except Exception as e:
            print(f"❌ Fehler bei Alarm #{alarm_id}: {e}")
            stop_loop()  # Stelle sicher, dass alle Sound-Loops gestoppt werden
    
    def shutdown(self):
        """Beendet den Alarm-Manager und stoppt alle laufenden Sounds."""
        self.running = False
        if self.alarm_thread:
            self.alarm_thread.join(timeout=1.0)
        stop_loop()  # Stoppe alle Sound-Loops
        stop()       # Stoppe alle normalen Sounds
        print("⏰ Alarm-System heruntergefahren")


# Demo-Funktion
def demo_alarm():
    """Demonstriert das Alarm-System mit verschiedenen Funktionen."""
    alarm_manager = Alarm()
    
    print("\n⏰ Demo: Setze Alarm für 5 Sekunden von jetzt an...")
    alarm_id = alarm_manager.set_alarm_in(
        seconds=5,
        wake_sound_id="wake-up-focus",
        get_up_sound_id="get-up-blossom"
    )
    
    print(f"Alarm wurde gesetzt. ID: {alarm_id}")
    print("Warten auf Alarm...")
    
    # Warte lange genug, um beide Sound-Phasen zu hören
    total_time = 5 + alarm_manager.wake_up_duration + alarm_manager.snooze_duration + alarm_manager.get_up_duration + 2
    time.sleep(total_time)
    
    # System herunterfahren
    alarm_manager.shutdown()


if __name__ == "__main__":
    demo_alarm()