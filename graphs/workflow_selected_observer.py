import random
from typing import Dict, Any, Optional, Protocol, List, ClassVar, Final
from dataclasses import dataclass
from enum import Enum, auto

from audio.audio_manager import play
from util.loggin_mixin import LoggingMixin

class WorkflowObserver(Protocol):
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        pass

@dataclass
class SoundCategory:
    """Repräsentiert eine Kategorie von Sounds mit einem Namen und der Anzahl der verfügbaren Dateien."""
    name: str
    count: int
    
    def get_random_filename(self) -> str:
        """Generiert einen zufälligen Dateinamen für diese Kategorie."""
        random_index = random.randint(1, self.count)
        return f"tts_{self.name}_{random_index}"

@dataclass
class WorkflowAudioFeedbackObserver(LoggingMixin):
    CATEGORIES: ClassVar[Dict[str, SoundCategory]] = {
        "weather": SoundCategory(name="weather", count=6),
        
        "alarm": SoundCategory(name="alarm", count=4),
        "alarm_loading": SoundCategory(name="alarm_loading", count=6),
        
        "todo": SoundCategory(name="todo", count=3),
        "notion_todo": SoundCategory(name="notion_todo_loading", count=5),
        "notion_clipboard": SoundCategory(name="notion_clipboard_loading", count=5),
        
        "spotify": SoundCategory(name="spotify_loading", count=4),
        
        "lights": SoundCategory(name="lights_loading", count=8),
    }
    
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        print(f"[AUDIO] Feedback für Workflow: {workflow_name}")
        
        category = self.CATEGORIES.get(workflow_name)
        if not category:
            self.logger.warning(f"[AUDIO] Keine Sound-Kategorie für Workflow '{workflow_name}' gefunden")
            return
            
        # Zufälligen Dateinamen generieren und abspielen
        filename = category.get_random_filename()
        self.logger.info(f"[AUDIO] Zufälliger Sound ausgewählt: {filename}")
        play(filename)
