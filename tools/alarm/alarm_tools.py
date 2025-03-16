import asyncio
import datetime
from typing import Type, List
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

# Importiere die Alarm-Klasse aus deinem Originalcode
from tools.alarm.alarm import Alarm, AlarmConfig

# Gemeinsam genutzter Alarm-Manager
_shared_alarm_manager = Alarm()

# ------ SetAlarmTool ------

class SetAlarmInput(BaseModel):
    """Eingabemodell für das SetAlarm Tool."""
    hour: int = Field(..., description="Stunde (0-23) für den Alarm")
    minute: int = Field(..., description="Minute (0-59) für den Alarm")

class SetAlarmTool(BaseTool):
    """Tool zum Setzen eines neuen Alarms, wobei vorherige Alarme gelöscht werden."""
    
    name: str = "set_alarm"
    description: str = """
    Setzt einen neuen Alarm für eine bestimmte Uhrzeit und löscht alle vorherigen Alarme.
    
    Benötigte Parameter:
    - hour: Stunde (0-23) für den Alarm
    - minute: Minute (0-59) für den Alarm
    
    Beispiel: "Setze einen Alarm für 7:30 Uhr" -> hour=7, minute=30
    """
    args_schema: Type[BaseModel] = SetAlarmInput

    # Alarm-Manager-Instanz
    alarm_manager: Alarm = Field(default_factory=lambda: _shared_alarm_manager, exclude=True)
    
    def _run(self, hour: int, minute: int) -> str:
        return asyncio.run(self._arun(hour=hour, minute=minute))

    async def _arun(self, hour: int, minute: int) -> str:
        """Setzt einen neuen Alarm und löscht alle vorherigen Alarme."""
        try:
            # Validiere die Eingabewerte
            if not (0 <= hour <= 23):
                return f"Fehler: Die Stunde muss zwischen 0 und 23 liegen, erhalten: {hour}"
            if not (0 <= minute <= 59):
                return f"Fehler: Die Minute muss zwischen 0 und 59 liegen, erhalten: {minute}"
            
            # Lösche alle vorhandenen Alarme
            self._delete_all_alarms()
            
            # Alarm setzen
            alarm_id = self.alarm_manager.set_alarm_for_time(hour=hour, minute=minute)
            
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
    
    def _delete_all_alarms(self) -> None:
        """Löscht alle vorhandenen Alarme."""
        # Hole Informationen zu allen Alarmen
        next_alarm_info = self.alarm_manager.get_next_alarm_info()
        
        # Solange es noch Alarme gibt, lösche sie
        while next_alarm_info:
            alarm_id, _, _ = next_alarm_info
            self.alarm_manager.cancel_alarm(alarm_id)
            next_alarm_info = self.alarm_manager.get_next_alarm_info()

# ------ CancelAlarmTool ------

class CancelAlarmInput(BaseModel):
    """Eingabemodell für das CancelAlarm Tool."""
    alarm_id: int = Field(..., description="ID des Alarms, der abgebrochen werden soll")

class CancelAlarmTool(BaseTool):
    """Tool zum Abbrechen eines Alarms."""
    
    name: str = "cancel_alarm"
    description: str = """
    Bricht einen bestehenden Alarm ab.
    
    Benötigte Parameter:
    - alarm_id: ID des Alarms, der abgebrochen werden soll
    
    Beispiel: "Breche Alarm Nummer 3 ab" -> alarm_id=3
    """
    args_schema: Type[BaseModel] = CancelAlarmInput

    # Alarm-Manager-Instanz
    alarm_manager: Alarm = Field(default_factory=lambda: _shared_alarm_manager, exclude=True)
    
    def _run(self, alarm_id: int) -> str:
        """Bricht einen Alarm ab."""
        try:
            success = self.alarm_manager.cancel_alarm(alarm_id)
            if success:
                return f"Alarm #{alarm_id} wurde erfolgreich abgebrochen."
            else:
                return f"Alarm #{alarm_id} konnte nicht abgebrochen werden (evtl. nicht gefunden oder bereits ausgelöst)."
        except Exception as e:
            return f"Fehler beim Abbrechen des Alarms: {str(e)}"

    async def _arun(self, alarm_id: int) -> str:
        """Asynchrone Version von _run."""
        return self._run(alarm_id=alarm_id)

# ------ AlarmInfoTool ------

class AlarmInfoTool(BaseTool):
    """Tool zum Abrufen von Informationen über den nächsten Alarm."""
    
    name: str = "alarm_info"
    description: str = """
    Gibt Informationen über den nächsten geplanten Alarm zurück.
    
    Keine Parameter erforderlich.
    
    Beispiel: "Zeige mir den nächsten Alarm"
    """
    args_schema: Type[BaseModel] = None  # Keine Parameter erforderlich

    # Alarm-Manager-Instanz
    alarm_manager: Alarm = Field(default_factory=lambda: _shared_alarm_manager, exclude=True)
    
    def _run(self) -> str:
        """Gibt Informationen zum nächsten Alarm zurück."""
        try:
            alarm_info = self.alarm_manager.get_next_alarm_info()
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

    async def _arun(self) -> str:
        """Asynchrone Version von _run."""
        return self._run()

# ------ Hilfsfunktion zum Abrufen aller Alarm-Tools ------

def get_alarm_tools() -> List[BaseTool]:
    """
    Gibt eine Liste aller Alarm-Tools zurück.
    
    Returns:
        List[BaseTool]: Liste der Alarm-Tools
    """
    return [
        SetAlarmTool(),
        CancelAlarmTool(),
        AlarmInfoTool()
    ]

# Beispiel zur Verwendung
if __name__ == "__main__":
    # Alle Tools abrufen
    tools = get_alarm_tools()
    
    # Beispiel: Alarm setzen
    set_tool = tools[0]
    print(set_tool.run({"hour": 7, "minute": 30}))
    
    # Beispiel: Alarm-Info abrufen
    info_tool = tools[2]
    print(info_tool.run({}))
    
    # Beispiel: Alarm abbrechen
    cancel_tool = tools[1]
    print(cancel_tool.run({"alarm_id": 0}))
    
    # Prüfen, ob Alarm abgebrochen wurde
    print(info_tool.run({}))