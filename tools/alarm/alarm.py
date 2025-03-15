import time
import threading
import asyncio
import datetime
from typing import Optional, List, Callable, Tuple, Dict, Any
from tools.alarm.alarm_config import DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND
from tools.alarm.alarm_item import AlarmItem
from audio.audio_manager import stop, play_loop, fade_out, get_mapper

from tools.lights.bridge import HueBridge
from tools.lights.hue.animation.sunrise_controller import SceneBasedSunriseController

class Alarm:
    def __init__(self):
        self.alarms: List[AlarmItem] = []
        self.running: bool = False
        self.alarm_thread: Optional[threading.Thread] = None
        
        self.audio_manager = get_mapper()
        
        self.wake_up_duration: int = 30
        self.get_up_duration: int = 40
        
        self.snooze_duration: int = 540
        
        self.fade_out_duration: float = 2.0
        
        # Lichtwecker-Einstellungen
        self.use_light_alarm: bool = True
        self.light_scene_name: str = "Majestätischer Morgen"
        self.light_controller: Optional[SceneBasedSunriseController] = None
        self.bridge: Optional[HueBridge] = None
        
        # Initialisiere den Lichtwecker, wenn gewünscht
        if self.use_light_alarm:
            self._init_light_controller()
    
    # TOOD: Das hier dürfte nicht mehr unbedingt notwendig sein wenn ich hier einen singleton draus mache:
    def _init_light_controller(self) -> None:
        try:
            threading.Thread(target=self._connect_bridge, daemon=True).start()
        except Exception as e:
            print(f"❌ Fehler beim Initialisieren des Lichtweckers: {e}")
    
    def _connect_bridge(self) -> None:
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.light_controller = SceneBasedSunriseController(self.bridge)
            print("💡 Lichtwecker erfolgreich initialisiert")
        except Exception as e:
            print(f"❌ Fehler beim Verbinden mit der Hue Bridge: {e}")
            self.use_light_alarm = False
    
    def set_alarm_for_time(
        self,
        hour: int,
        minute: int,
        wake_sound_id = DEFAULT_WAKE_SOUND,
        get_up_sound_id = DEFAULT_GET_UP_SOUND,
        use_light: bool = True,
        light_scene: str = None,
        callback: Optional[Callable] = None
    ) -> int:
        now = datetime.datetime.now()
        get_up_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if get_up_time <= now:
            get_up_time += datetime.timedelta(days=1)
        
        wake_up_time = get_up_time - datetime.timedelta(seconds=self.snooze_duration)
        
        # Erstelle zusätzliche Einstellungen für den Alarm
        extra_settings = {
            "use_light": use_light and self.use_light_alarm,
            "light_scene": light_scene or self.light_scene_name
        }
        
        return self.set_alarm(wake_up_time, wake_sound_id, get_up_sound_id, callback, extra_settings)
    
    def set_alarm(
        self, 
        alarm_time: datetime.datetime, 
        wake_sound_id: str, 
        get_up_sound_id: str,
        callback: Optional[Callable] = None,
        extra_settings: Optional[Dict[str, Any]] = None
    ) -> int:
        alarm_id = len(self.alarms)
        
        alarm = AlarmItem(
            id=alarm_id,
            time=alarm_time,
            wake_sound_id=wake_sound_id,
            get_up_sound_id=get_up_sound_id,
            callback=callback,
            extra=extra_settings or {}
        )
        
        self.alarms.append(alarm)
        
        get_up_time = alarm_time + datetime.timedelta(seconds=self.snooze_duration)
        
        print(f"⏰ Alarm #{alarm_id} gesetzt:")
        print(f"   Wake-Up: {alarm_time.strftime('%H:%M:%S')} (Sound: {wake_sound_id})")
        print(f"   Get-Up: {get_up_time.strftime('%H:%M:%S')} (Sound: {get_up_sound_id})")
        
        if alarm.extra.get("use_light", False):
            print(f"   Lichtwecker: Aktiv (Szene: {alarm.extra.get('light_scene', self.light_scene_name)})")
        
        if not self.running:
            self._start_monitoring()
            
        return alarm_id
    
    def set_alarm_in(
        self, 
        seconds: int, 
        wake_sound_id: str, 
        get_up_sound_id: str,
        callback: Optional[Callable] = None,
        use_light: bool = True,
        light_scene: str = None
    ) -> int:
        """
        Setzt einen Alarm, der in X Sekunden ausgelöst wird.
        
        Args:
            seconds: Zeit in Sekunden, bis der Alarm ausgelöst wird
            wake_sound_id: ID des Wake-Up-Sounds
            get_up_sound_id: ID des Get-Up-Sounds
            callback: Optionale Funktion, die nach dem Alarm aufgerufen wird
            use_light: Ob der Lichtwecker verwendet werden soll
            light_scene: Name der zu verwendenden Lichtszene (oder None für Standard)
            
        Returns:
            ID des Alarms (zur späteren Referenz)
        """
        alarm_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        
        extra_settings = {
            "use_light": use_light and self.use_light_alarm,
            "light_scene": light_scene or self.light_scene_name
        }
        
        return self.set_alarm(alarm_time, wake_sound_id, get_up_sound_id, callback, extra_settings)
    
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
            
            next_alarm_time: Optional[datetime.datetime] = None
            for i, alarm in enumerate(self.alarms):
                if not alarm.triggered:
                    if now >= alarm.time:
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
    
    def _run_async_in_thread(self, coro):
        """Führt eine asyncio-Coroutine in einem separaten Thread aus"""
        asyncio.run(coro)
            
    def _trigger_alarm(self, alarm: AlarmItem) -> None:
        alarm_id = alarm.id
        wake_sound_id = alarm.wake_sound_id
        get_up_sound_id = alarm.get_up_sound_id
        use_light = alarm.extra.get("use_light", False)
        light_scene = alarm.extra.get("light_scene", self.light_scene_name)
        
        print(f"⏰ ALARM #{alarm_id} wird ausgelöst!")
        
        light_thread = None
        
        try:
            # Starte den Lichtwecker, wenn aktiviert und verfügbar
            if use_light and self.light_controller:
                print(f"💡 Starte Lichtwecker mit Szene '{light_scene}'...")
                light_thread = threading.Thread(
                    target=self._run_async_in_thread,
                    args=(self._start_light_alarm(light_scene, self.snooze_duration),),
                    daemon=True
                )
                light_thread.start()
            
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
            
            # Warte auf den Abschluss des Lichtweckers, falls aktiv
            if light_thread:
                remaining_time = self.snooze_duration
                while light_thread.is_alive() and remaining_time > 0:
                    sleep_time = min(remaining_time, 1)
                    time.sleep(sleep_time)
                    remaining_time -= sleep_time
            else:
                time.sleep(self.snooze_duration)
            
            print(f"🔊 Spiele Get-Up Sound '{get_up_sound_id}' für {self.get_up_duration} Sekunden...")
            
            play_loop(get_up_sound_id, self.get_up_duration - self.fade_out_duration)
            
            if self.audio_manager.is_playing():
                fade_out(self.fade_out_duration)
                
                time.sleep(self.fade_out_duration)
            
            print(f"⏰ Alarm #{alarm_id} abgeschlossen")
            
            if alarm.callback:
                alarm.callback()
                
        except Exception as e:
            print(f"❌ Fehler bei Alarm #{alarm_id}: {e}")
            
            fade_out(self.fade_out_duration)
            time.sleep(self.fade_out_duration)
            stop()
    
    async def _start_light_alarm(self, scene_name: str, duration: int) -> None:
        """Startet den Lichtwecker mit der angegebenen Szene"""
        try:
            if self.light_controller:
                await self.light_controller.start_scene_based_sunrise(
                    scene_name=scene_name,
                    duration=duration,
                    start_brightness_percent=0.01  # 1% der Zielhelligkeit
                )
                
                # Warte, bis der Sonnenaufgang abgeschlossen ist
                while (self.light_controller.running_sunrise and 
                       not self.light_controller.running_sunrise.done()):
                    await asyncio.sleep(1)
                    
                print("💡 Lichtwecker abgeschlossen")
        except Exception as e:
            print(f"❌ Fehler beim Lichtwecker: {e}")
    
    def shutdown(self) -> None:
        """Beendet den Alarm-Manager und stoppt alle laufenden Sounds."""
        self.running = False
        if self.alarm_thread:
            self.alarm_thread.join(timeout=1.0)
        
        fade_out(self.fade_out_duration)
        
        time.sleep(self.fade_out_duration + 0.5)
        
        stop()
        
        # Stoppe auch den Lichtwecker, falls aktiv
        if self.light_controller and self.light_controller.running_sunrise:
            asyncio.run(self.light_controller.stop_sunrise())
            
        print("⏰ Alarm-System heruntergefahren")


def demo():
    # Erstelle eine Alarm-Instanz
    alarm_manager = Alarm()
    
    print("\n⏰ Demo: Setze Alarm in der nächsten Minute...")
    
    # Hole die aktuelle Zeit
    now = datetime.datetime.now()
    
    # Setze den Alarm für die nächste Minute
    hour = now.hour
    minute = now.minute + 1
    
    # Wenn es die letzte Minute der Stunde ist, gehe zur nächsten Stunde über
    if minute == 60:
        minute = 0
        hour = (hour + 1) % 24
    
    alarm_id = alarm_manager.set_alarm_for_time(
        hour=hour,
        minute=minute,
        use_light=True,
        light_scene="Majestätischer Morgen"
    )
    
    # Zeige Informationen zum nächsten Alarm an
    next_alarm_info = alarm_manager.get_next_alarm_info()
    if next_alarm_info:
        alarm_id, wake_time, get_time = next_alarm_info
        print(f"Nächster Alarm (#{alarm_id}):")
        print(f"  Wake-Up-Phase: {wake_time.strftime('%H:%M:%S')}")
        print(f"  Get-Up-Phase: {get_time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    demo()
    
    try:
        # Warte auf Beendigung durch Strg+C
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBeende Demo...")