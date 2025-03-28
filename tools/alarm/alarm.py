import time
import threading
import asyncio
import datetime
from typing import Optional, Callable, Tuple
from dataclasses import dataclass

from audio.strategy.audio_manager import AudioManager
from tools.alarm.alarm_config import DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND
from tools.alarm.alarm_item import AlarmItem

from tools.lights.animation.sunrise_controller import SceneBasedSunriseController
from tools.lights.bridge.bridge import HueBridge
from util.loggin_mixin import LoggingMixin

from singleton_decorator import singleton


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


@singleton
class Alarm(LoggingMixin):
    def __init__(self, config: Optional[AlarmConfig] = None):
        self.current_alarm: Optional[AlarmItem] = None
        self.running: bool = False
        self.alarm_thread: Optional[threading.Thread] = None
        self.audio_manager = AudioManager()

        self.config = config or AlarmConfig()

        self.light_controller: Optional[SceneBasedSunriseController] = None
        self.bridge: Optional[HueBridge] = None

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
        callback: Optional[Callable] = None,
    ) -> int:
        wake_sound_id = wake_sound_id or self.config.default_wake_up_sound
        get_up_sound_id = get_up_sound_id or self.config.default_get_up_sound

        now = datetime.datetime.now()
        get_up_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if get_up_time <= now:
            get_up_time += datetime.timedelta(days=1)

        wake_up_time = get_up_time - datetime.timedelta(
            seconds=self.config.snooze_duration
        )

        # Erstelle Einstellungen für den Alarm
        extra_settings = {
            "use_light": use_light and self.config.use_light_alarm,
            "light_scene": light_scene or self.config.light_scene_name,
        }

        # Setze den Alarm
        alarm = AlarmItem(
            id=0,  # Immer ID 0, da nur ein Alarm
            time=wake_up_time,
            wake_sound_id=wake_sound_id,
            get_up_sound_id=get_up_sound_id,
            callback=callback,
            extra=extra_settings,
        )

        # Speichere den Alarm
        self.current_alarm = alarm

        get_up_time = wake_up_time + datetime.timedelta(
            seconds=self.config.snooze_duration
        )

        # Protokolliere Details
        self._log_alarm_details(alarm, get_up_time)

        # Starte die Überwachung, falls noch nicht aktiv
        if not self.running:
            self._start_monitoring()

        return 0  # Immer ID 0 zurückgeben

    def _log_alarm_details(
        self, alarm: AlarmItem, get_up_time: datetime.datetime
    ) -> None:
        """Protokolliert Details zu einem gesetzten Alarm."""
        self.logger.info(f"⏰ Alarm gesetzt:")
        self.logger.info(
            "   Wake-Up: %s (Sound: %s)",
            alarm.time.strftime("%H:%M:%S"),
            alarm.wake_sound_id,
        )
        self.logger.info(
            f"   Get-Up: {get_up_time.strftime('%H:%M:%S')} (Sound: {alarm.get_up_sound_id})"
        )

        if alarm.extra.get("use_light", False):
            self.logger.info(
                f"   Lichtwecker: Aktiv (Szene: {alarm.extra.get('light_scene', self.config.light_scene_name)})"
            )

    def set_alarm_in(
        self,
        seconds: int,
        wake_sound_id: str = DEFAULT_WAKE_SOUND,
        get_up_sound_id: str = DEFAULT_GET_UP_SOUND,
        callback: Optional[Callable] = None,
        use_light: bool = True,
        light_scene: Optional[str] = None,
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
            int: ID des Alarms (immer 0)
        """
        # Berechne die Alarmzeit
        now = datetime.datetime.now()
        wake_time = now + datetime.timedelta(seconds=seconds)

        # Setze den Alarm (mit Standard-Sounds, falls nicht angegeben)
        alarm = AlarmItem(
            id=0,  # Immer ID 0
            time=wake_time,
            wake_sound_id=wake_sound_id,
            get_up_sound_id=get_up_sound_id,
            callback=callback,
            extra={
                "use_light": use_light and self.config.use_light_alarm,
                "light_scene": light_scene or self.config.light_scene_name,
            },
        )

        # Speichere den Alarm
        self.current_alarm = alarm

        get_up_time = wake_time + datetime.timedelta(
            seconds=self.config.snooze_duration
        )

        # Protokolliere Details
        self._log_alarm_details(alarm, get_up_time)

        # Starte die Überwachung, falls noch nicht aktiv
        if not self.running:
            self._start_monitoring()

        return 0  # Immer ID 0 zurückgeben

    def get_next_alarm_info(
        self,
    ) -> Optional[Tuple[int, datetime.datetime, datetime.datetime]]:
        """
        Gibt Informationen zum anstehenden Alarm zurück.

        Returns:
            Optional[Tuple[int, datetime.datetime, datetime.datetime]]:
                (alarm_id, wake_up_time, get_up_time) oder None, wenn kein Alarm gesetzt ist
        """
        if not self.current_alarm or self.current_alarm.triggered:
            return None

        get_up_time = self.current_alarm.time + datetime.timedelta(
            seconds=self.config.snooze_duration
        )
        return (0, self.current_alarm.time, get_up_time)  # ID ist immer 0

    def cancel_alarm(self, alarm_id: int = 0) -> bool:
        """
        Bricht den aktuellen Alarm ab.

        Args:
            alarm_id: Wird ignoriert, da es nur einen Alarm gibt

        Returns:
            bool: True, wenn der Alarm abgebrochen wurde, False sonst
        """
        if self.current_alarm and not self.current_alarm.triggered:
            self.current_alarm = None
            self.logger.info("⏰ Alarm abgebrochen")
            return True

        self.logger.info("⏰ Kein aktiver Alarm zum Abbrechen vorhanden")
        return False

    def _start_monitoring(self) -> None:
        """Startet den Überwachungsthread für den Alarm."""
        self.running = True
        self.alarm_thread = threading.Thread(target=self._monitor_alarm, daemon=True)
        self.alarm_thread.start()
        self.logger.info("⏰ Alarm-Überwachung gestartet")

    def _monitor_alarm(self) -> None:
        """Überwacht den Alarm und löst ihn aus, wenn der Zeitpunkt erreicht ist."""
        while self.running:
            # Prüfe, ob ein Alarm gesetzt ist
            if self.current_alarm and not self.current_alarm.triggered:
                now = datetime.datetime.now()

                # Prüfe, ob der Alarm ausgelöst werden soll
                if now >= self.current_alarm.time:
                    alarm = self.current_alarm
                    self.current_alarm.triggered = True
                    self._start_alarm_thread(alarm)

                    # Warte bis zum nächsten Check
                    time.sleep(60)  # Prüfe regelmäßig, ob ein neuer Alarm gesetzt wurde
                else:
                    # Berechne Wartezeit bis zum Alarm
                    wait_seconds = (self.current_alarm.time - now).total_seconds()
                    sleep_time = min(wait_seconds, 60)  # Maximal 1 Minute warten
                    time.sleep(max(1, sleep_time))  # Mindestens 1 Sekunde warten
            else:
                # Kein Alarm gesetzt, prüfe gelegentlich wieder
                time.sleep(60)

    def _start_alarm_thread(self, alarm: AlarmItem) -> None:
        """Startet einen Thread zur Alarmauslösung."""
        threading.Thread(target=self._trigger_alarm, args=(alarm,), daemon=True).start()

    def _run_async_in_thread(self, coro) -> None:
        """Führt eine asyncio-Coroutine in einem separaten Thread aus."""
        asyncio.run(coro)

    def _trigger_alarm(self, alarm: AlarmItem) -> None:
        """
        Löst einen Alarm aus und führt die entsprechenden Aktionen aus.

        Args:
            alarm: Der auszulösende Alarm
        """
        self.logger.info("⏰ ALARM wird ausgelöst!")

        try:
            # Starte Lichtwecker, falls konfiguriert
            light_thread = self._start_light_alarm_if_enabled(alarm)

            # Phase 1: Wake-Up Sound
            self._play_wake_up_phase(alarm.wake_sound_id)

            # Warte die Snooze-Zeit ab
            self._handle_snooze_phase(light_thread)

            # Phase 2: Get-Up Sound
            self._play_get_up_phase(alarm.get_up_sound_id)

            self.logger.info("⏰ Alarm abgeschlossen")

            # Führe Callback aus, falls vorhanden
            if alarm.callback:
                alarm.callback()

        except Exception as e:
            self.logger.error(f"❌ Fehler beim Alarm: {e}")
            self._handle_alarm_error()

        # Setze alarm auf None, da er erledigt ist
        if self.current_alarm and self.current_alarm.triggered:
            self.current_alarm = None

    def _start_light_alarm_if_enabled(
        self, alarm: AlarmItem
    ) -> Optional[threading.Thread]:
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
                args=(
                    self._start_light_alarm(light_scene, self.config.snooze_duration),
                ),
                daemon=True,
            )
            light_thread.start()
            return light_thread

        return None

    def _play_wake_up_phase(self, sound_id: str) -> None:
        """Spielt den Wake-Up Sound ab."""
        duration = self.config.wake_up_duration
        fade_duration = self.config.fade_out_duration

        self.logger.info(
            f"🔊 Spiele Wake-Up Sound '{sound_id}' für {duration} Sekunden..."
        )
        self.audio_manager.play_loop(sound_id, duration - fade_duration)

        self._handle_fade_out_if_playing()

    def _play_get_up_phase(self, sound_id: str) -> None:
        """Spielt den Get-Up Sound ab."""
        duration = self.config.get_up_duration
        fade_duration = self.config.fade_out_duration

        self.logger.info(
            f"🔊 Spiele Get-Up Sound '{sound_id}' für {duration} Sekunden..."
        )
        self.audio_manager.play_loop(sound_id, duration - fade_duration)

        self._handle_fade_out_if_playing()

    def _handle_fade_out_if_playing(self) -> None:
        """Führt Fade-Out durch, wenn Sound noch abgespielt wird."""
        fade_duration = self.config.fade_out_duration

        if self.audio_manager.is_playing():
            self.audio_manager.fade_out(fade_duration)
            time.sleep(fade_duration)

    def _handle_snooze_phase(self, light_thread: Optional[threading.Thread]) -> None:
        """Behandelt die Snooze-Phase zwischen Wake-Up und Get-Up."""
        snooze_duration = self.config.snooze_duration
        self.logger.info(f"💤 Snooze für {snooze_duration} Sekunden...")

        if light_thread:
            self._wait_for_light_thread(light_thread, snooze_duration)
        else:
            time.sleep(snooze_duration)

    def _wait_for_light_thread(
        self, light_thread: threading.Thread, max_wait_time: int
    ) -> None:
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
        try:
            if self.light_controller:
                await self.light_controller.start_scene_based_sunrise(
                    scene_name=scene_name,
                    duration=duration,
                    start_brightness_percent=0.01,  # 1% der Zielhelligkeit
                )

                # Warte, bis der Sonnenaufgang abgeschlossen ist
                while (
                    self.light_controller.running_sunrise
                    and not self.light_controller.running_sunrise.done()
                ):
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


if __name__ == "__main__":
    import logging

    # Konfiguriere das Logging
    logging.basicConfig(level=logging.INFO)

    # Erstelle eine Alarm-Konfiguration
    config = AlarmConfig(
        wake_up_duration=10,
        get_up_duration=20,
        snooze_duration=40,
        fade_out_duration=2.0,
        use_light_alarm=True,
        light_scene_name="Majestätischer Morgen",
    )

    # Initialisiere den Alarm-Manager
    alarm_manager = Alarm(config=config)

    # Setze einen Alarm für 1 Minute in der Zukunft
    now = datetime.datetime.now()
    alarm_manager.set_alarm_for_time(
        hour=now.hour,
        minute=(now.minute + 1) % 60,
        wake_sound_id="wake-up-focus",
        get_up_sound_id="get-up-blossom",
        use_light=True,
        light_scene="Majestätischer Morgen",
    )

    # Halte das Skript am Laufen, um den Alarm zu testen
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        alarm_manager.shutdown()
