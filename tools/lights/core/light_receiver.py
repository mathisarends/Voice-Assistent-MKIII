from __future__ import annotations

from typing import Protocol
from tools.lights.hue.bridge import Bridge
from tools.lights.hue.light_status import LightStatus


# Protocol für Lichtgeräte als Empfänger von Befehlen
class LightReceiver(Protocol):
    """Protocol für ein Lichtgerät, das Befehle empfangen kann."""
    bridge: Bridge
    device_id: str
    name: str
    
    async def get_status(self) -> LightStatus:
        """Gibt den aktuellen Status des Lichts zurück."""
        ...
