import datetime
from typing import Optional, Callable

class AlarmItem:
    def __init__(
        self,
        id: int,
        time: datetime.datetime,
        wake_sound_id: str,
        get_up_sound_id: str,
        callback: Optional[Callable] = None
    ):
        self.id: int = id
        self.time: datetime.datetime = time
        self.wake_sound_id: str = wake_sound_id
        self.get_up_sound_id: str = get_up_sound_id
        self.callback: Optional[Callable] = callback
        self.triggered: bool = False
    
    def __str__(self) -> str:
        return f"Alarm #{self.id} at {self.time.strftime('%H:%M:%S')} (Wake: {self.wake_sound_id}, Get-up: {self.get_up_sound_id})"
