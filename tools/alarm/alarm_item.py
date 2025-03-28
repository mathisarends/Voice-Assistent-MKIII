# tools/alarm/alarm_item.py
from datetime import datetime
from typing import Optional, Callable, Dict, Any


class AlarmItem:
    def __init__(
        self,
        id: int,
        time: datetime,
        wake_sound_id: str,
        get_up_sound_id: str,
        callback: Optional[Callable] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.time = time
        self.wake_sound_id = wake_sound_id
        self.get_up_sound_id = get_up_sound_id
        self.callback = callback
        self.extra = (
            extra or {}
        )  # Speichert zusätzliche Einstellungen wie Lichtwecker-Parameter
        self.triggered = False
