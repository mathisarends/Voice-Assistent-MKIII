import time
import threading
import datetime
from typing import Optional, List, Callable, Tuple
from alarm.alarm_config import DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND
from alarm.alarm_item import AlarmItem
from audio.audio_manager import stop, play_loop, fade_out, get_mapper

class Alarm:
    def __init__(self):
        self.alarms: List[AlarmItem] = []
        self.running: bool = False
        self.alarm_thread: Optional[threading.Thread] = None
        
        # Initialisiere AudioManager
        self.audio_manager = get_mapper()
        
        # Standarddauer für die verschiedenen Phasen (in Sekunden)
        self.wake_up_duration: int = 30
        self.get_up_duration: int = 40
        
        # Pause zwischen Wake-Up und Get-Up (in Sekunden)
        self.snooze_duration: int = 540  # 9 Minuten
        
        # Fade-Out-Dauer in Sekunden
        self.fade_out_duration: float = 2.0
    
    def set_alarm_for_time(
        self,
        hour: int,
        minute: int,
        wake_sound_id = DEFAULT_WAKE_SOUND,
        get_up_sound_id = DEFAULT_GET_UP_SOUND,
        callback: Optional[Callable] = None
    ) -> int:
        # Aktuelle Zeit
        now = datetime.datetime.now()
        
        # Zielzeit für die Get-Up-Phase erstellen
        get_up_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Wenn die Zeit bereits heute vorbei ist, setze auf morgen
        if get_up_time <= now:
            get_up_time += datetime.timedelta(days=1)
        
        # Wake-Up-Zeit berechnen (Get-Up-Zeit minus snooze_duration)
        wake_up_time = get_up_time - datetime.timedelta(seconds=self.snooze_duration)
        
        # Alarm mit der Wake-Up-Zeit setzen
        return self.set_alarm(wake_up_time, wake_sound_id, get_up_sound_id, callback)
    
    def set_alarm(
        self, 
        alarm_time: datetime.datetime, 
        wake_sound_id: str, 
        get_up_sound_id: str,
        callback: Optional[Callable] = None
    ) -> int:
        alarm_id = len(self.alarms)
        
        alarm = AlarmItem(
            id=alarm_id,
            time=alarm_time,
            wake_sound_id=wake_sound_id,
            get_up_sound_id=get_up_sound_id,
            callback=callback
        )
        
        self.alarms.append(alarm)
        
        get_up_time = alarm_time + datetime.timedelta(seconds=self.snooze_duration)
        
        print(f"⏰ Alarm #{alarm_id} gesetzt:")
        print(f"   Wake-Up: {alarm_time.strftime('%H:%M:%S')} (Sound: {wake_sound_id})")
        print(f"   Get-Up: {get_up_time.strftime('%H:%M:%S')} (Sound: {get_up_sound_id})")
        
        if not self.running:
            self._start_monitoring()
            
        return alarm_id
    
    def set_alarm_in(
        self, 
        seconds: int, 
        wake_sound_id: str, 
        get_up_sound_id: str,
        callback: Optional[Callable] = None
    ) -> int:
        """
        Setzt einen Alarm, der in X Sekunden ausgelöst wird.
        
        Args:
            seconds: Zeit in Sekunden, bis der Alarm ausgelöst wird
            wake_sound_id: ID des Wake-Up-Sounds
            get_up_sound_id: ID des Get-Up-Sounds
            callback: Optionale Funktion, die nach dem Alarm aufgerufen wird
            
        Returns:
            ID des Alarms (zur späteren Referenz)
        """
        alarm_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        return self.set_alarm(alarm_time, wake_sound_id, get_up_sound_id, callback)
    
    def get_next_alarm_info(self) -> Optional[Tuple[int, datetime.datetime, datetime.datetime]]:
        """
        Gibt Informationen zum nächsten anstehenden Alarm zurück.
        
        Returns:
            Optional[Tuple[int, datetime.datetime, datetime.datetime]]: 
                (alarm_id, wake_up_time, get_up_time) oder None, wenn kein Alarm gesetzt ist
        """
        if not self.alarms:
            return None
        
        # Finde den nächsten anstehenden Alarm
        next_alarm = min(
            [alarm for alarm in self.alarms if not alarm.triggered],
            key=lambda a: a.time,
            default=None
        )
        
        if not next_alarm:
            return None
        
        get_up_time = next_alarm.time + datetime.timedelta(seconds=self.snooze_duration)
        return (next_alarm.id, next_alarm.time, get_up_time)
    
    def cancel_alarm(self, alarm_id: int) -> bool:
        for i, alarm in enumerate(self.alarms):
            if alarm.id == alarm_id and not alarm.triggered:
                self.alarms.pop(i)
                print(f"⏰ Alarm #{alarm_id} abgebrochen")
                return True
        return False
    
    def _start_monitoring(self) -> None:
        """Startet den Überwachungsthread für Alarme."""
        self.running = True
        self.alarm_thread = threading.Thread(target=self._monitor_alarms, daemon=True)
        self.alarm_thread.start()
        print("⏰ Alarm-Überwachung gestartet")
    
    def _monitor_alarms(self) -> None:
        while self.running:
            now = datetime.datetime.now()
            triggered_indices: List[int] = []
            
            # Find next alarm time
            next_alarm_time: Optional[datetime.datetime] = None
            for i, alarm in enumerate(self.alarms):
                if not alarm.triggered:
                    if now >= alarm.time:
                        # Trigger immediately
                        threading.Thread(
                            target=self._trigger_alarm,
                            args=(alarm,),
                            daemon=True
                        ).start()
                        
                        alarm.triggered = True
                        triggered_indices.append(i)
                    elif next_alarm_time is None or alarm.time < next_alarm_time:
                        next_alarm_time = alarm.time
            
            # Remove triggered alarms
            for i in sorted(triggered_indices, reverse=True):
                self.alarms.pop(i)
            
            # Calculate sleep duration until next alarm (or default to longer sleep)
            if next_alarm_time:
                sleep_seconds = (next_alarm_time - now).total_seconds()
                sleep_seconds = max(1, min(sleep_seconds, 300))
            else:
                sleep_seconds = 60  # No alarms scheduled, check less frequently
                
            time.sleep(sleep_seconds)
            
    def _trigger_alarm(self, alarm: AlarmItem) -> None:
        alarm_id = alarm.id
        wake_sound_id = alarm.wake_sound_id
        get_up_sound_id = alarm.get_up_sound_id
        
        print(f"⏰ ALARM #{alarm_id} wird ausgelöst!")
        
        try:
            # Phase 1: Wake-Up Sound für konfigurierte Dauer im Loop
            print(f"🔊 Spiele Wake-Up Sound '{wake_sound_id}' für {self.wake_up_duration} Sekunden...")
            
            # Starte den Loop
            play_loop(wake_sound_id, self.wake_up_duration - self.fade_out_duration)
            
            # Führe Fade-Out durch, wenn der Sound nicht vorzeitig beendet wurde
            if self.audio_manager.is_playing():
                fade_out(self.fade_out_duration)
                
                # Warte, bis der Fade-Out abgeschlossen ist
                time.sleep(self.fade_out_duration)
            
            # Warte die Snooze-Zeit ab (9 Minuten)
            print(f"💤 Snooze für {self.snooze_duration} Sekunden...")
            time.sleep(self.snooze_duration)
            
            # Phase 2: Get-Up Sound für konfigurierte Dauer im Loop
            print(f"🔊 Spiele Get-Up Sound '{get_up_sound_id}' für {self.get_up_duration} Sekunden...")
            
            # Starte den Loop
            play_loop(get_up_sound_id, self.get_up_duration - self.fade_out_duration)
            
            # Führe Fade-Out durch, wenn der Sound nicht vorzeitig beendet wurde
            if self.audio_manager.is_playing():
                fade_out(self.fade_out_duration)
                
                # Warte, bis der Fade-Out abgeschlossen ist
                time.sleep(self.fade_out_duration)
            
            print(f"⏰ Alarm #{alarm_id} abgeschlossen")
            
            # Callback aufrufen, falls konfiguriert
            if alarm.callback:
                alarm.callback()
                
        except Exception as e:
            print(f"❌ Fehler bei Alarm #{alarm_id}: {e}")
            
            # Stelle sicher, dass alle Sounds gestoppt werden, auch im Fehlerfall
            fade_out(self.fade_out_duration)
            time.sleep(self.fade_out_duration)
            stop()
    
    def shutdown(self) -> None:
        """Beendet den Alarm-Manager und stoppt alle laufenden Sounds."""
        self.running = False
        if self.alarm_thread:
            self.alarm_thread.join(timeout=1.0)
        
        # Stoppe Sounds mit einem Fade-Out
        fade_out(self.fade_out_duration)
        
        # Warte auf das Ende des Fade-Outs
        time.sleep(self.fade_out_duration + 0.5)
        
        # Stelle sicher, dass wirklich alle Sounds gestoppt sind
        stop()
        print("⏰ Alarm-System heruntergefahren")


if __name__ == "__main__":
    alarm_manager = Alarm()
    
    # Beispiel: Setze einen Alarm für 6:30 Uhr (Get-Up-Phase)
    # Das bedeutet, dass die Wake-Up-Phase um 6:21 Uhr beginnt (9 Minuten früher)
    print("\n⏰ Demo: Setze Alarm für 6:30 Uhr (Get-Up-Phase)...")
    alarm_id = alarm_manager.set_alarm_for_time(
        hour=7,
        minute=20,
    )
    
    # Zeige Informationen zum nächsten Alarm an
    next_alarm_info = alarm_manager.get_next_alarm_info()
    if next_alarm_info:
        alarm_id, wake_time, get_time = next_alarm_info
        print(f"Nächster Alarm (#{alarm_id}):")
        print(f"  Wake-Up-Phase: {wake_time.strftime('%H:%M:%S')}")
        print(f"  Get-Up-Phase: {get_time.strftime('%H:%M:%S')}")
    

    
    time.sleep(1000)