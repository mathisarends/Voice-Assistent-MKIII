import time
import random
from typing import Dict, Any, Protocol, ClassVar
from dataclasses import dataclass

from audio.sonos.sonos_manager import SonosAudioManager
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
    """Observer, der Audio-Feedback für ausgewählte Workflows abspielt."""
    
    # Definiere alle Sound-Kategorien als Klassenvariablen für bessere Wartbarkeit
    SOUND_CATEGORIES: ClassVar[Dict[str, SoundCategory]] = {
        "weather": SoundCategory(name="weather", count=6),
        "alarm": SoundCategory(name="alarm", count=4),
        "alarm_loading": SoundCategory(name="alarm_loading", count=6),
        "todo": SoundCategory(name="todo", count=3),
        "notion_todo_loading": SoundCategory(name="notion_todo_loading", count=5),
        "notion_clipboard_loading": SoundCategory(name="notion_clipboard_loading", count=5),
        "spotify_loading": SoundCategory(name="spotify_loading", count=3),
        "lights_loading": SoundCategory(name="lights_loading", count=7),
        "volume_loading": SoundCategory(name="volume_loading", count=5),
        "pomodoro_loading": SoundCategory(name="pomodoro_loading", count=5),
        "youtube_loading": SoundCategory(name="youtube_loading", count=6)
        
    }
    
    # Hier könnte man auch überlegen ob man das nicht direkt in die WorkflowRegistry Klassen packt diese mapping
    WORKFLOW_TO_SOUND_CATEGORY: ClassVar[Dict[str, str]] = {
        "weather": "weather",
        "alarm": "alarm_loading",
        "todo": "todo",
        "notion_todo": "notion_todo_loading",
        "notion_clipboard": "notion_clipboard_loading",
        "spotify": "spotify_loading",
        "lights": "lights_loading",
        "volume": "volume_loading",
        "pomodoro": "pomodoro_loading",
        "youtube": "youtube_loading"
    }
    
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        """Spielt einen Sound basierend auf dem ausgewählten Workflow ab."""
        self.logger.info(f"[AUDIO] Feedback für Workflow: {workflow_name}")
        
        category_name = self.WORKFLOW_TO_SOUND_CATEGORY.get(workflow_name)
        if not category_name:
            self.logger.warning(f"[AUDIO] Kein Sound-Mapping für Workflow '{workflow_name}' gefunden")
            return
            
        category = self.SOUND_CATEGORIES.get(category_name)
        if not category:
            self.logger.warning(f"[AUDIO] Kategorie '{category_name}' nicht gefunden")
            return
            
        filename = category.get_random_filename()
        self.logger.info(f"[AUDIO] Zufälliger Sound ausgewählt: {filename}")
        
        SonosAudioManager().play(filename)