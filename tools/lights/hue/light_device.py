from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

class LightDevice(ABC):
    """Abstrakte Basis-Klasse für Lichtgeräte."""
    
    def __init__(self, device_id: str, name: str):
        self.device_id = device_id
        self._name = name
        self._is_on = False
        self._brightness = 100
    
    @property
    def name(self) -> str:
        """Gibt den Namen des Lichtgeräts zurück."""
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        """Setzt den Namen des Lichtgeräts."""
        self._name = value
    
    @property
    def is_on(self) -> bool:
        """Gibt zurück, ob das Licht eingeschaltet ist."""
        return self._is_on
    
    @is_on.setter
    def is_on(self, value: bool) -> None:
        """Setzt den Einschaltstatus des Lichts."""
        self._is_on = value
    
    @abstractmethod
    async def turn_on(self) -> Any:
        """Schaltet das Licht ein."""
        pass
    
    @abstractmethod
    async def turn_off(self) -> Any:
        """Schaltet das Licht aus."""
        pass
    
    @abstractmethod
    async def set_brightness(self, brightness: int) -> Any:
        """Stellt die Helligkeit ein (0-100%)."""
        pass
    
    @abstractmethod
    async def get_status(self) -> dict:
        """Gibt den aktuellen Status zurück."""
        pass