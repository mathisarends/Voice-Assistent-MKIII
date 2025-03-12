import unittest
from unittest.mock import patch, MagicMock, call
import datetime
import time
from freezegun import freeze_time
from alarm.alarm import Alarm
from alarm.alarm_config import DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND

class TestAlarm(unittest.TestCase):
    """Tests für die Alarm-Klasse."""
    
    def setUp(self):
        """Wird vor jedem Test ausgeführt."""
        # Mocke den AudioManager
        self.audio_manager_mock = MagicMock()
        self.audio_manager_mock.is_playing.return_value = True
        
        # Patches für die verschiedenen Funktionen
        self.get_mapper_patch = patch('alarm.alarm.get_mapper', return_value=self.audio_manager_mock)
        self.play_loop_patch = patch('alarm.alarm.play_loop')
        self.fade_out_patch = patch('alarm.alarm.fade_out')
        self.stop_patch = patch('alarm.alarm.stop')
        self.time_sleep_patch = patch('time.sleep')  # Verhindert Wartezeiten in Tests
        
        # Patches starten
        self.get_mapper_mock = self.get_mapper_patch.start()
        self.play_loop_mock = self.play_loop_patch.start()
        self.fade_out_mock = self.fade_out_patch.start()
        self.stop_mock = self.stop_patch.start()
        self.time_sleep_mock = self.time_sleep_patch.start()
        
        # Alarm-Instanz erstellen
        self.alarm = Alarm()
        
        # Konfiguriere kürzere Dauern für schnelleres Testen
        self.alarm.wake_up_duration = 3
        self.alarm.get_up_duration = 3
        self.alarm.snooze_duration = 3
        self.alarm.fade_out_duration = 1
    
    def tearDown(self):
        """Wird nach jedem Test ausgeführt."""
        # Patches stoppen
        self.get_mapper_patch.stop()
        self.play_loop_patch.stop()
        self.fade_out_patch.stop()
        self.stop_patch.stop()
        self.time_sleep_patch.stop()
        
        # Alarm-System herunterfahren
        self.alarm.shutdown()
    
    def test_set_alarm_for_time(self):
        """Testet, ob ein Alarm für eine bestimmte Uhrzeit korrekt gesetzt wird."""
        with freeze_time("2023-01-01 12:00:00"):
            # Setze Alarm für 13:30 Uhr (heute)
            alarm_id = self.alarm.set_alarm_for_time(hour=13, minute=30)
            
            # Überprüfe, ob der Alarm korrekt gesetzt wurde
            self.assertEqual(len(self.alarm.alarms), 1)
            self.assertEqual(self.alarm.alarms[0].id, alarm_id)
            
            # Die Wake-Up-Zeit sollte 9 Minuten vor der Get-Up-Zeit sein
            expected_wake_time = datetime.datetime(2023, 1, 1, 13, 30) - datetime.timedelta(seconds=540)
            self.assertEqual(self.alarm.alarms[0].time, expected_wake_time)
    
    def test_set_alarm_for_past_time(self):
        """Testet, ob ein Alarm für eine vergangene Uhrzeit auf den nächsten Tag gesetzt wird."""
        with freeze_time("2023-01-01 14:00:00"):
            # Setze Alarm für 13:30 Uhr (bereits vergangen)
            alarm_id = self.alarm.set_alarm_for_time(hour=13, minute=30)
            
            # Überprüfe, ob der Alarm auf morgen gesetzt wurde
            expected_get_up_time = datetime.datetime(2023, 1, 2, 13, 30)
            expected_wake_time = expected_get_up_time - datetime.timedelta(seconds=540)
            
            self.assertEqual(self.alarm.alarms[0].time, expected_wake_time)
    
    def test_cancel_alarm(self):
        """Testet, ob ein Alarm erfolgreich abgebrochen werden kann."""
        # Setze einen Alarm
        alarm_id = self.alarm.set_alarm_in(seconds=60, 
                                          wake_sound_id=DEFAULT_WAKE_SOUND, 
                                          get_up_sound_id=DEFAULT_GET_UP_SOUND)
        
        # Überprüfe, ob der Alarm existiert
        self.assertEqual(len(self.alarm.alarms), 1)
        
        # Breche den Alarm ab
        result = self.alarm.cancel_alarm(alarm_id)
        
        # Überprüfe, ob der Alarm erfolgreich abgebrochen wurde
        self.assertTrue(result)
        self.assertEqual(len(self.alarm.alarms), 0)
    
    def test_cancel_nonexistent_alarm(self):
        """Testet den Abbruch eines nicht existierenden Alarms."""
        # Breche einen nicht existierenden Alarm ab
        result = self.alarm.cancel_alarm(999)
        
        # Überprüfe, ob die Methode False zurückgibt
        self.assertFalse(result)
    
    def test_get_next_alarm_info(self):
        """Testet die Methode zur Abfrage des nächsten Alarms."""
        # Setze zwei Alarme zu unterschiedlichen Zeiten
        now = datetime.datetime.now()
        
        alarm1_time = now + datetime.timedelta(hours=2)
        alarm2_time = now + datetime.timedelta(hours=1)  # Dieser sollte der nächste sein
        
        self.alarm.set_alwarm(alarm1_time, DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND)
        alarm2_id = self.alarm.set_alarm(alarm2_time, DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND)
        
        # Rufe get_next_alarm_info auf
        next_alarm_info = self.alarm.get_next_alarm_info()
        
        # Überprüfe, ob die richtigen Informationen zurückgegeben werden
        self.assertIsNotNone(next_alarm_info)
        
        returned_id, returned_wake_time, returned_get_up_time = next_alarm_info
        
        # Der zweite Alarm sollte der nächste sein
        self.assertEqual(returned_id, alarm2_id)
        self.assertEqual(returned_wake_time, alarm2_time)
        self.assertEqual(returned_get_up_time, alarm2_time + datetime.timedelta(seconds=self.alarm.snooze_duration))
    
    def test_get_next_alarm_info_empty(self):
        """Testet get_next_alarm_info ohne gesetzte Alarme."""
        # Keine Alarme gesetzt
        next_alarm_info = self.alarm.get_next_alarm_info()
        
        # Sollte None zurückgeben
        self.assertIsNone(next_alarm_info)
    
    @patch('threading.Thread')
    def test_trigger_alarm(self, thread_mock):
        """Testet das Auslösen eines Alarms."""
        # Mock-Thread, der sofort die _trigger_alarm-Methode aufruft
        def trigger_immediately(target, args, daemon):
            target(*args)
            return MagicMock()
        
        thread_mock.side_effect = trigger_immediately
        
        # Erstelle einen Alarm in der Vergangenheit
        now = datetime.datetime.now()
        past_time = now - datetime.timedelta(minutes=5)
        
        callback_mock = MagicMock()
        
        # Setze den Alarm
        self.alarm.set_alarm(past_time, DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND, callback=callback_mock)
        
        # Starte die Überwachung manuell (normalerweise wird dies von set_alarm aufgerufen)
        self._monitor_alarms_once()
        
        # Überprüfe, ob die Sounds korrekt abgespielt wurden
        self.play_loop_mock.assert_has_calls([
            # Wake-Up-Sound
            call(DEFAULT_WAKE_SOUND, self.alarm.wake_up_duration - self.alarm.fade_out_duration),
            # Get-Up-Sound
            call(DEFAULT_GET_UP_SOUND, self.alarm.get_up_duration - self.alarm.fade_out_duration)
        ])
        
        # Überprüfe, ob Fade-Out aufgerufen wurde
        self.assertEqual(self.fade_out_mock.call_count, 2)
        
        # Überprüfe, ob der Callback aufgerufen wurde
        callback_mock.assert_called_once()
        
        # Überprüfe, ob der Alarm aus der Liste entfernt wurde
        self.assertEqual(len(self.alarm.alarms), 0)
    
    def test_shutdown(self):
        """Testet, ob das Alarm-System ordnungsgemäß heruntergefahren wird."""
        # Setze einen Alarm (nicht relevant für diesen Test)
        self.alarm.set_alarm_in(60, DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND)
        
        # Fahre das System herunter
        self.alarm.shutdown()
        
        # Überprüfe, ob running auf False gesetzt wurde
        self.assertFalse(self.alarm.running)
        
        # Überprüfe, ob fade_out und stop aufgerufen wurden
        self.fade_out_mock.assert_called_once()
        self.stop_mock.assert_called_once()
    
    def _monitor_alarms_once(self):
        """Führt einen einzelnen Durchlauf der _monitor_alarms-Methode aus."""
        # Aktuelle Zeit
        now = datetime.datetime.now()
        triggered_indices = []
        
        # Prüfe alle Alarme
        for i, alarm in enumerate(self.alarm.alarms):
            if not alarm.triggered and now >= alarm.time:
                self.alarm._trigger_alarm(alarm)
                alarm.triggered = True
                triggered_indices.append(i)
        
        # Entferne getriggerte Alarme
        for i in sorted(triggered_indices, reverse=True):
            self.alarm.alarms.pop(i)


class TestAlarmIntegration(unittest.TestCase):
    """Integrationstests für das Alarm-System.
    
    Diese Tests verwenden keine Mocks für time.sleep und führen daher reale Verzögerungen aus.
    Sie sind nützlich, um die tatsächliche Zeitsteuerung zu testen, sollten aber sparsam eingesetzt werden.
    """
    
    def setUp(self):
        # Patches für die Audio-Funktionen
        self.audio_manager_mock = MagicMock()
        self.audio_manager_mock.is_playing.return_value = True
        
        self.get_mapper_patch = patch('alarm.alarm.get_mapper', return_value=self.audio_manager_mock)
        self.play_loop_patch = patch('alarm.alarm.play_loop')
        self.fade_out_patch = patch('alarm.alarm.fade_out')
        self.stop_patch = patch('alarm.alarm.stop')
        
        # Patches starten
        self.get_mapper_mock = self.get_mapper_patch.start()
        self.play_loop_mock = self.play_loop_patch.start()
        self.fade_out_mock = self.fade_out_patch.start()
        self.stop_mock = self.stop_patch.start()
        
        # Alarm-Instanz erstellen
        self.alarm = Alarm()
        
        # Konfiguriere sehr kurze Dauern für schnelleres Testen
        self.alarm.wake_up_duration = 0.2
        self.alarm.get_up_duration = 0.2
        self.alarm.snooze_duration = 0.3
        self.alarm.fade_out_duration = 0.1
    
    def tearDown(self):
        # Patches stoppen
        self.get_mapper_patch.stop()
        self.play_loop_patch.stop()
        self.fade_out_patch.stop()
        self.stop_patch.stop()
        
        # Alarm-System herunterfahren
        self.alarm.shutdown()
    
    def test_immediate_alarm_with_real_timing(self):
        """Testet einen sofortigen Alarm mit echten Verzögerungen."""
        # Callback-Mock
        callback_mock = MagicMock()
        
        # Setze einen Alarm, der sofort ausgelöst wird
        self.alarm.set_alarm_in(0.1, DEFAULT_WAKE_SOUND, DEFAULT_GET_UP_SOUND, callback=callback_mock)
        
        # Warte etwas länger als die Gesamtdauer des Alarms
        expected_duration = (0.1 +  # Verzögerung bis Auslösung
                           self.alarm.wake_up_duration +
                           self.alarm.snooze_duration +
                           self.alarm.get_up_duration +
                           0.5)  # Extra-Puffer
        
        # Warte auf die Ausführung
        time.sleep(expected_duration)
        
        # Überprüfe, ob die Sounds korrekt abgespielt wurden
        self.play_loop_mock.assert_has_calls([
            # Wake-Up-Sound
            call(DEFAULT_WAKE_SOUND, self.alarm.wake_up_duration - self.alarm.fade_out_duration),
            # Get-Up-Sound
            call(DEFAULT_GET_UP_SOUND, self.alarm.get_up_duration - self.alarm.fade_out_duration)
        ])
        
        # Überprüfe, ob der Callback aufgerufen wurde
        callback_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()