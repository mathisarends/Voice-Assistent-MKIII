import datetime
from typing import List
from langchain.tools import tool

# Importiere die Alarm-Klasse aus deinem Originalcode
from tools.alarm.alarm import Alarm

# Gemeinsam genutzter Alarm-Manager als Singleton
_shared_alarm_manager = Alarm()

@tool(return_direct=True)
def set_alarm(hour: int, minute: int) -> str:
    """
    Setzt einen neuen Alarm für eine bestimmte Uhrzeit und löscht alle vorherigen Alarme.
    
    Args:
        hour: Stunde (0-23) für den Alarm
        minute: Minute (0-59) für den Alarm
    
    Returns:
        Eine Nachricht, die den Erfolg oder Misserfolg der Operation anzeigt.
    """
    try:
        # Validiere die Eingabewerte
        if not (0 <= hour <= 23):
            return f"Fehler: Die Stunde muss zwischen 0 und 23 liegen, erhalten: {hour}"
        if not (0 <= minute <= 59):
            return f"Fehler: Die Minute muss zwischen 0 und 59 liegen, erhalten: {minute}"
        
        # Lösche alle vorhandenen Alarme
        _delete_all_alarms()
        
        # Alarm setzen
        alarm_id = _shared_alarm_manager.set_alarm_for_time(hour=hour, minute=minute)
        
        # Berechne die Zeit bis zum Alarm
        now = datetime.datetime.now()
        alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if alarm_time <= now:
            alarm_time += datetime.timedelta(days=1)
        
        time_diff = alarm_time - now
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        return f"Neuer Alarm #{alarm_id} gesetzt für {hour:02d}:{minute:02d} (in {hours} Stunden und {minutes} Minuten)."
    except Exception as e:
        return f"Fehler beim Setzen des Alarms: {str(e)}"

@tool(return_direct=True)
def cancel_alarm(alarm_id: int) -> str:
    """
    Bricht einen bestehenden Alarm ab.
    
    Args:
        alarm_id: ID des Alarms, der abgebrochen werden soll
    
    Returns:
        Eine Nachricht, die den Erfolg oder Misserfolg der Operation anzeigt.
    """
    try:
        success = _shared_alarm_manager.cancel_alarm(alarm_id)
        if success:
            return f"Alarm #{alarm_id} wurde erfolgreich abgebrochen."
        else:
            return f"Alarm #{alarm_id} konnte nicht abgebrochen werden (evtl. nicht gefunden oder bereits ausgelöst)."
    except Exception as e:
        return f"Fehler beim Abbrechen des Alarms: {str(e)}"

@tool(return_direct=True)
def get_alarm_info() -> str:
    """
    Gibt Informationen über den nächsten geplanten Alarm zurück.
    
    Returns:
        Eine Nachricht mit Informationen zum nächsten Alarm oder einer Mitteilung, dass keine Alarme geplant sind.
    """
    try:
        alarm_info = _shared_alarm_manager.get_next_alarm_info()
        if alarm_info:
            alarm_id, wake_time, get_time = alarm_info
            
            # Berechne die Zeit bis zum nächsten Alarm
            now = datetime.datetime.now()
            time_diff = wake_time - now
            
            if time_diff.total_seconds() <= 0:
                return f"Der nächste Alarm (#{alarm_id}) wird gerade ausgelöst!"
            
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return (
                f"Nächster Alarm: #{alarm_id}\n"
                f"Wake-Up Phase: {wake_time.strftime('%H:%M:%S')} (in {hours}h {minutes}m {seconds}s)\n"
                f"Get-Up Phase: {get_time.strftime('%H:%M:%S')}"
            )
        else:
            return "Keine Alarme geplant."
    except Exception as e:
        return f"Fehler beim Abrufen der Alarm-Informationen: {str(e)}"

def _delete_all_alarms() -> None:
    """Löscht alle vorhandenen Alarme."""
    # Hole Informationen zu allen Alarmen
    next_alarm_info = _shared_alarm_manager.get_next_alarm_info()
    
    # Solange es noch Alarme gibt, lösche sie
    while next_alarm_info:
        alarm_id, _, _ = next_alarm_info
        _shared_alarm_manager.cancel_alarm(alarm_id)
        next_alarm_info = _shared_alarm_manager.get_next_alarm_info()

def get_alarm_tools() -> List:

    return [
        set_alarm,
        cancel_alarm,
        get_alarm_info
    ]
