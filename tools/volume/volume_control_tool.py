import asyncio
from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from tools.volume.volume_control import VolumeControl  

class VolumeControlInput(BaseModel):
    """Eingabemodell für das VolumeControl Tool."""
    action: str = Field(
        description="Die auszuführende Aktion: 'set', 'increase', 'decrease', 'mute', 'get'"
    )
    value: Optional[int] = Field(
        default=None,
        description="Der Wert für die Aktion 'set' (1-10) oder die Schrittgröße für 'increase'/'decrease'"
    )

class VolumeControlTool(BaseTool):
    """Steuert die Systemlautstärke mit PulseAudio."""
    
    name: str = "volume_control"
    description: str = """Steuert die Systemlautstärke über PulseAudio (Linux).
    Aktionen:
    - 'set': Setzt die Lautstärke auf eine Stufe (1-10)
    - 'increase': Erhöht die Lautstärke (Standardschritt: 15%)
    - 'decrease': Verringert die Lautstärke (Standardschritt: 15%)
    - 'get': Gibt die aktuelle Lautstärke zurück"""
    
    args_schema: Type[BaseModel] = VolumeControlInput
    
    def _run(self, action: str, value: Optional[int] = None) -> str:
        return asyncio.run(self._arun(action, value))

    async def _arun(self, action: str, value: Optional[int] = None) -> str:
        try:
            if action == "set":
                if value is None:
                    return "Fehler: Für die Aktion 'set' wird ein Wert (1-10) benötigt."
                
                if not 1 <= value <= 10:
                    return "Fehler: Lautstärkelevel muss zwischen 1 und 10 liegen."
                    
                VolumeControl.set_volume_level(value)
            
            elif action == "increase":
                step = value if value is not None else 15
                VolumeControl.increase_volume(step)
            
            elif action == "decrease":
                step = value if value is not None else 15
                VolumeControl.decrease_volume(step)
                
            elif action == "get":
                current_volume = VolumeControl.get_volume()
                return f"Aktuelle Lautstärke: {current_volume}%"
            
            else:
                return f"Fehler: Unbekannte Aktion '{action}'"

            current_volume = VolumeControl.get_volume()
            
            return f"Lautstärkeaktion '{action}' erfolgreich ausgeführt. Aktuelle Lautstärke: {current_volume}%."

        except Exception as e:
            return f"Fehler bei der Ausführung des VolumeControlTools: {str(e)}"