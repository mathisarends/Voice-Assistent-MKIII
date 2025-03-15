from abc import ABC, abstractmethod
from typing import Any, Dict, List

from tools.lights.core.light_receiver import LightReceiver

class LightCommand(ABC):
    """Basisklasse für Lichtbefehle nach dem Command-Pattern."""
    
    @abstractmethod
    async def execute(self, light: LightReceiver) -> List[Dict[str, Any]]:
        """Führt den Befehl für das angegebene Licht aus."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Gibt eine Beschreibung des Befehls zurück."""
        pass