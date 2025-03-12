import time
import threading
import datetime
from typing import Optional, List, Dict, Callable

from audio.audio_manager import stop, play_loop, fade_out, get_mapper

class Alarm:
    """Eine Alarmklasse, die zu einem bestimmten Zeitpunkt Sounds abspielt."""
    
    def __init__(self):
        self.alarms: List[Dict] = []
        self.running = False
        self.alarm_thread = None
        
        # Initialisiere AudioManager
        self.audio_manager = get_mapper()
        
        # Standarddauer für die verschiedenen Phasen (in Sekunden)
        self.wake_up_duration = 30
        self.get_up_duration = 40
        
        # Pause zwischen Wake-Up und Get-Up (in Sekunden)
        self.snooze_duration = 540  # 9 Minuten
        
        # Fade-Out-Dauer in Sekunden
        self.fade_out_duration = 2.0
    
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
        for i, alarm in enumerate(self.alarms):
            if alarm["id"] == alarm_id and not alarm["triggered"]:
                self.alarms.pop(i)
                print(f"⏰ Alarm #{alarm_id} abgebrochen")
                return True
        return False
    
    def _start_monitoring(self):
        """Startet den Überwachungsthread für Alarme."""
        self.running = True
        self.alarm_thread = threading.Thread(target=self._monitor_alarms, daemon=True)
        self.alarm_thread.start()
        print("⏰ Alarm-Überwachung gestartet")
    
    def _monitor_alarms(self):
        while self.running:
            now = datetime.datetime.now()
            triggered_indices = []
            
            # Find next alarm time
            next_alarm_time = None
            for i, alarm in enumerate(self.alarms):
                if not alarm["triggered"]:
                    if now >= alarm["time"]:
                        # Trigger immediately
                        threading.Thread(
                            target=self._trigger_alarm,
                            args=(alarm,),
                            daemon=True
                        ).start()
                        
                        alarm["triggered"] = True
                        triggered_indices.append(i)
                    elif next_alarm_time is None or alarm["time"] < next_alarm_time:
                        next_alarm_time = alarm["time"]
            
            # Remove triggered alarms
            for i in sorted(triggered_indices, reverse=True):
                self.alarms.pop(i)
            
            if next_alarm_time:
                sleep_seconds = (next_alarm_time - now).total_seconds()
                sleep_seconds = max(1, min(sleep_seconds, 300))
            else:
                sleep_seconds = 60
                
            time.sleep(sleep_seconds)
            
    def _trigger_alarm(self, alarm: Dict):
        """Löst einen Alarm aus und spielt die konfigurierten Sounds ab."""
        alarm_id = alarm["id"]
        wake_sound_id = alarm["wake_sound_id"]
        get_up_sound_id = alarm["get_up_sound_id"]
        
        print(f"⏰ ALARM #{alarm_id} wird ausgelöst!")
        
        try:
            print(f"🔊 Spiele Wake-Up Sound '{wake_sound_id}' für {self.wake_up_duration} Sekunden...")
            
            play_loop(wake_sound_id, self.wake_up_duration - self.fade_out_duration)
            
            if self.audio_manager.is_playing():
                fade_out(self.fade_out_duration)
                
                time.sleep(self.fade_out_duration)
            
            print(f"💤 Snooze für {self.snooze_duration} Sekunden...")
            time.sleep(self.snooze_duration)
            
            print(f"🔊 Spiele Get-Up Sound '{get_up_sound_id}' für {self.get_up_duration} Sekunden...")
            
            play_loop(get_up_sound_id, self.get_up_duration - self.fade_out_duration)
            
            if self.audio_manager.is_playing():
                fade_out(self.fade_out_duration)
                
                time.sleep(self.fade_out_duration)
            
            print(f"⏰ Alarm #{alarm_id} abgeschlossen")
            
            if alarm["callback"]:
                alarm["callback"]()
                
        except Exception as e:
            print(f"❌ Fehler bei Alarm #{alarm_id}: {e}")
            
            fade_out(self.fade_out_duration)
            time.sleep(self.fade_out_duration)
            stop()
    
    def shutdown(self):
        """Beendet den Alarm-Manager und stoppt alle laufenden Sounds."""
        self.running = False
        if self.alarm_thread:
            self.alarm_thread.join(timeout=1.0)
        
        fade_out(self.fade_out_duration)
        
        time.sleep(self.fade_out_duration + 0.5)
        
        stop()
        print("⏰ Alarm-System heruntergefahren")


def demo_alarm():
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
    # Beachte, dass das Fade-Out in der Dauer inbegriffen ist
    total_time = 5 + alarm_manager.wake_up_duration + alarm_manager.snooze_duration + alarm_manager.get_up_duration + 5
    time.sleep(total_time)
    
    alarm_manager.shutdown()


if __name__ == "__main__":
    demo_alarm()