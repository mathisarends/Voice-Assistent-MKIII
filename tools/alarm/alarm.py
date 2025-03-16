import time
import threading
import asyncio
import datetime
from typing import Optional, List, Callable, Tuple, Dict, Any
from dataclasses import dataclass

from tools.alarm.alarm_config import DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND
from tools.alarm.alarm_item import AlarmItem
from audio.audio_manager import stop, play_loop, fade_out, get_mapper

from tools.lights.animation.sunrise_controller import SceneBasedSunriseController
from tools.lights.bridge import HueBridge
from util.loggin_mixin import LoggingMixin

@dataclass
class AlarmConfig:
    """Konfiguration für den Alarm-Manager."""
    wake_up_duration: int = 30
    get_up_duration: int = 40
    snooze_duration: int = 540
    fade_out_duration: float = 2.0
    use_light_alarm: bool = True
    light_scene_name: str = "Majestätischer Morgen"
    default_wake_up_sound = "wake-up-focus"
    default_get_up_sound = "get-up-blossom"


class Alarm(LoggingMixin):
    def __init__(self, config: Optional[AlarmConfig] = None):
        self.alarms: List[AlarmItem] = []
        self.running: bool = False
        self.alarm_thread: Optional[threading.Thread] = None
        self.audio_manager = get_mapper()
        
        # Konfiguration
        self.config = config or AlarmConfig()
        
        # Lichtwecker-Komponenten
        self.light_controller: Optional[SceneBasedSunriseController] = None
        self.bridge: Optional[HueBridge] = None
        
        # Initialisiere den Lichtwecker, wenn gewünscht
        if self.config.use_light_alarm:
            self._init_light_controller()
    
    def _init_light_controller(self) -> None:
        """Initialisiert den Lichtwecker asynchron."""
        try:
            threading.Thread(target=self._connect_bridge, daemon=True).start()
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Initialisieren des Lichtweckers: {e}")
    
    def _connect_bridge(self) -> None:
        """Stellt eine Verbindung zur Hue Bridge her."""
        try:
            self.bridge = HueBridge.connect_by_ip()
            self.light_controller = SceneBasedSunriseController(self.bridge)
            self.logger.info("💡 Lichtwecker erfolgreich initialisiert")
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Verbinden mit der Hue Bridge: {e}")
            self.config.use_light_alarm = False
    
    def set_alarm_for_time(
        self,
        hour: int,
        minute: int,
        wake_sound_id: Optional[str] = None,
        get_up_sound_id: Optional[str] = None,
        use_light: bool = True,
        light_scene: Optional[str] = None,
        callback: Optional[Callable] = None
    ) -> int:
        """
        Setzt einen Alarm für eine bestimmte Uhrzeit.
        
        Args:
            hour: Stunde (0-23)
            minute: Minute (0-59)
            wake_sound_id: ID des Wake-Up-Sounds
            get_up_sound_id: ID des Get-Up-Sounds
            use_light: Ob der Lichtwecker verwendet werden soll
            light_scene: Name der zu verwendenden Lichtszene
            callback: Funktion, die nach dem Alarm aufgerufen wird
            
        Returns:
            int: ID des Alarms
        """
        
        wake_sound_id = self.config.default_wake_up_sound
        get_up_sound_id = self.config.default_get_up_sound
        
        now = datetime.datetime.now()
        get_up_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if get_up_time <= now:
            get_up_time += datetime.timedelta(days=1)
        
        wake_up_time = get_up_time - datetime.timedelta(seconds=self.config.snooze_duration)
        
        # Erstelle Einstellungen für den Alarm
        extra_settings = {
            "use_light": use_light and self.config.use_light_alarm,
            "light_scene": light_scene or self.config.light_scene_name
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
        """
        Setzt einen Alarm für einen bestimmten Zeitpunkt.
        
        Args:
            alarm_time: Zeitpunkt für den Alarm
            wake_sound_id: ID des Wake-Up-Sounds
            get_up_sound_id: ID des Get-Up-Sounds
            callback: Funktion, die nach dem Alarm aufgerufen wird
            extra_settings: Zusätzliche Einstellungen
            
        Returns:
            int: ID des Alarms
        """
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
        
        get_up_time = alarm_time + datetime.timedelta(seconds=self.config.snooze_duration)
        
        self._log_alarm_details(alarm, get_up_time)
        
        if not self.running:
            self._start_monitoring()
            
        return alarm_id
    
    def _log_alarm_details(self, alarm: AlarmItem, get_up_time: datetime.datetime) -> None:
        """Protokolliert Details zu einem gesetzten Alarm."""
        self.logger.info(f"⏰ Alarm #{alarm.id} gesetzt:")
        self.logger.info("   Wake-Up: %s (Sound: %s)", 
                        alarm.time.strftime('%H:%M:%S'), 
                        alarm.wake_sound_id)
        self.logger.info(f"   Get-Up: {get_up_time.strftime('%H:%M:%S')} (Sound: {alarm.get_up_sound_id})")
        
        if alarm.extra.get("use_light", False):
            self.logger.info(f"   Lichtwecker: Aktiv (Szene: {alarm.extra.get('light_scene', self.config.light_scene_name)})")
    
    def set_alarm_in(
        self, 
        seconds: int, 
        wake_sound_id: str = DEFAULT_WAKE_SOUND, 
        get_up_sound_id: str = DEFAULT_GET_UP_SOUND,
        callback: Optional[Callable] = None,
        use_light: bool = True,
        light_scene: Optional[str] = None
    ) -> int:
        """
        Setzt einen Alarm, der in X Sekunden ausgelöst wird.
        
        Args:
            seconds: Zeit in Sekunden, bis der Alarm ausgelöst wird
            wake_sound_id: ID des Wake-Up-Sounds
            get_up_sound_id: ID des Get-Up-Sounds
            callback: Optionale Funktion, die nach dem Alarm aufgerufen wird
            use_light: Ob der Lichtwecker verwendet werden soll
            light_scene: Name der zu verwendenden Lichtszene
            
        Returns:
            ID des Alarms
        """
        alarm_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        
        extra_settings = {
            "use_light": use_light and self.config.use_light_alarm,
            "light_scene": light_scene or self.config.light_scene_name
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
        next_alarm = self._find_next_alarm()
        if not next_alarm:
            return None
        
        get_up_time = next_alarm.time + datetime.timedelta(seconds=self.config.snooze_duration)
        return (next_alarm.id, next_alarm.time, get_up_time)
    
    def _find_next_alarm(self) -> Optional[AlarmItem]:
        """Findet den nächsten anstehenden, nicht ausgelösten Alarm."""
        return min(
            [alarm for alarm in self.alarms if not alarm.triggered],
            key=lambda a: a.time,
            default=None
        )
    
    def cancel_alarm(self, alarm_id: int) -> bool:
        """
        Bricht einen Alarm ab.
        
        Args:
            alarm_id: ID des abzubrechenden Alarms
            
        Returns:
            bool: True, wenn der Alarm abgebrochen wurde, False sonst
        """
        for i, alarm in enumerate(self.alarms):
            if alarm.id == alarm_id and not alarm.triggered:
                self.alarms.pop(i)
                self.logger.info(f"⏰ Alarm #{alarm_id} abgebrochen")
                return True
        return False
    
    def _start_monitoring(self) -> None:
        """Startet den Überwachungsthread für Alarme."""
        self.running = True
        self.alarm_thread = threading.Thread(target=self._monitor_alarms, daemon=True)
        self.alarm_thread.start()
        self.logger.info("⏰ Alarm-Überwachung gestartet")
    
    def _monitor_alarms(self) -> None:
        """Überwacht die Alarme und löst sie aus, wenn der Zeitpunkt erreicht ist."""
        while self.running:
            now = datetime.datetime.now()
            triggered_indices = []
            
            next_alarm_time = None
            for i, alarm in enumerate(self.alarms):
                if not alarm.triggered:
                    if now >= alarm.time:
                        self._start_alarm_thread(alarm)
                        alarm.triggered = True
                        triggered_indices.append(i)
                    elif next_alarm_time is None or alarm.time < next_alarm_time:
                        next_alarm_time = alarm.time
            
            # Entferne ausgelöste Alarme
            for i in sorted(triggered_indices, reverse=True):
                self.alarms.pop(i)
            
            # Berechne Schlafzeit bis zum nächsten Alarm
            sleep_seconds = self._calculate_sleep_duration(now, next_alarm_time)
            time.sleep(sleep_seconds)
    
    def _start_alarm_thread(self, alarm: AlarmItem) -> None:
        """Startet einen Thread zur Alarmauslösung."""
        threading.Thread(
            target=self._trigger_alarm,
            args=(alarm,),
            daemon=True
        ).start()
    
    def _calculate_sleep_duration(self, now: datetime.datetime, next_alarm_time: Optional[datetime.datetime]) -> float:
        """Berechnet die Schlafzeit bis zum nächsten Alarm."""
        if next_alarm_time:
            sleep_seconds = (next_alarm_time - now).total_seconds()
            return max(1, min(sleep_seconds, 300))
        return 60  # Kein Alarm geplant, prüfe weniger häufig
    
    def _run_async_in_thread(self, coro) -> None:
        """Führt eine asyncio-Coroutine in einem separaten Thread aus."""
        asyncio.run(coro)
            
    def _trigger_alarm(self, alarm: AlarmItem) -> None:
        """
        Löst einen Alarm aus und führt die entsprechenden Aktionen aus.
        
        Args:
            alarm: Der auszulösende Alarm
        """
        alarm_id = alarm.id
        self.logger.info(f"⏰ ALARM #{alarm_id} wird ausgelöst!")
        
        try:
            # Starte Lichtwecker, falls konfiguriert
            light_thread = self._start_light_alarm_if_enabled(alarm)
            
            # Phase 1: Wake-Up Sound
            self._play_wake_up_phase(alarm.wake_sound_id)
            
            # Warte die Snooze-Zeit ab
            self._handle_snooze_phase(light_thread)
            
            # Phase 2: Get-Up Sound
            self._play_get_up_phase(alarm.get_up_sound_id)
            
            self.logger.info(f"⏰ Alarm #{alarm_id} abgeschlossen")
            
            # Führe Callback aus, falls vorhanden
            if alarm.callback:
                alarm.callback()
                
        except Exception as e:
            self.logger.error(f"❌ Fehler bei Alarm #{alarm_id}: {e}")
            self._handle_alarm_error()
    
    def _start_light_alarm_if_enabled(self, alarm: AlarmItem) -> Optional[threading.Thread]:
        """
        Startet den Lichtwecker, falls konfiguriert.
        
        Returns:
            Optional[threading.Thread]: Der Thread des Lichtweckers oder None
        """
        use_light = alarm.extra.get("use_light", False)
        light_scene = alarm.extra.get("light_scene", self.config.light_scene_name)
        
        if use_light and self.light_controller:
            self.logger.info(f"💡 Starte Lichtwecker mit Szene '{light_scene}'...")
            light_thread = threading.Thread(
                target=self._run_async_in_thread,
                args=(self._start_light_alarm(light_scene, self.config.snooze_duration),),
                daemon=True
            )
            light_thread.start()
            return light_thread
        
        return None
    
    def _play_wake_up_phase(self, sound_id: str) -> None:
        """Spielt den Wake-Up Sound ab."""
        duration = self.config.wake_up_duration
        fade_duration = self.config.fade_out_duration
        
        self.logger.info(f"🔊 Spiele Wake-Up Sound '{sound_id}' für {duration} Sekunden...")
        play_loop(sound_id, duration - fade_duration)
        
        self._handle_fade_out_if_playing()
    
    def _play_get_up_phase(self, sound_id: str) -> None:
        """Spielt den Get-Up Sound ab."""
        duration = self.config.get_up_duration
        fade_duration = self.config.fade_out_duration
        
        self.logger.info(f"🔊 Spiele Get-Up Sound '{sound_id}' für {duration} Sekunden...")
        play_loop(sound_id, duration - fade_duration)
        
        self._handle_fade_out_if_playing()
    
    def _handle_fade_out_if_playing(self) -> None:
        """Führt Fade-Out durch, wenn Sound noch abgespielt wird."""
        fade_duration = self.config.fade_out_duration
        
        if self.audio_manager.is_playing():
            fade_out(fade_duration)
            time.sleep(fade_duration)
    
    def _handle_snooze_phase(self, light_thread: Optional[threading.Thread]) -> None:
        """Behandelt die Snooze-Phase zwischen Wake-Up und Get-Up."""
        snooze_duration = self.config.snooze_duration
        self.logger.info(f"💤 Snooze für {snooze_duration} Sekunden...")
        
        if light_thread:
            self._wait_for_light_thread(light_thread, snooze_duration)
        else:
            time.sleep(snooze_duration)
    
    def _wait_for_light_thread(self, light_thread: threading.Thread, max_wait_time: int) -> None:
        """Wartet auf den Lichtwecker-Thread mit Timeout."""
        remaining_time = max_wait_time
        while light_thread.is_alive() and remaining_time > 0:
            sleep_time = min(remaining_time, 1)
            time.sleep(sleep_time)
            remaining_time -= sleep_time
    
    def _handle_alarm_error(self) -> None:
        """Behandelt Fehler bei der Alarmauslösung."""
        fade_out(self.config.fade_out_duration)
        time.sleep(self.config.fade_out_duration)
        stop()
    
    async def _start_light_alarm(self, scene_name: str, duration: int) -> None:
        """
        Startet den Lichtwecker mit der angegebenen Szene.
        
        Args:
            scene_name: Name der zu verwendenden Lichtszene
            duration: Dauer des Sonnenaufgangs in Sekunden
        """
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
                    
                self.logger.info("💡 Lichtwecker abgeschlossen")
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Lichtwecker: {e}")
    
    def shutdown(self) -> None:
        """Beendet den Alarm-Manager und stoppt alle laufenden Sounds."""
        self.running = False
        if self.alarm_thread:
            self.alarm_thread.join(timeout=1.0)
        
        fade_out(self.config.fade_out_duration)
        time.sleep(self.config.fade_out_duration + 0.5)
        stop()
        
        # Stoppe auch den Lichtwecker, falls aktiv
        if self.light_controller and self.light_controller.running_sunrise:
            asyncio.run(self.light_controller.stop_sunrise())
            
        self.logger.info("⏰ Alarm-System heruntergefahren")


def demo():
    """Demo-Funktion zum Testen des Alarm-Managers."""
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