import random
from typing import Dict, Any, Optional, Protocol

from audio.audio_manager import play

class WorkflowObserver(Protocol):
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        pass

class WorkflowAudioFeedbackObserver:
    def __init__(self):
        self.workflow_sound_mapping = {
            "weather": {"category": "weather", "count": 6},
            "alarm": {"category": "alarm", "count": 4},
            "todo": {"category": "todo", "count": 3},
            
            "spotify": {"category": "spotify_loading", "count": 4},
            "notion_todo": {"category": "notion_todo_loading", "count": 5},
            "notion_clipboard": {"category": "notion_clipboard_loading", "count": 5},
            
            "lights": {"category": "lights_loading", "count": 8},
            "alarm_loading": {"category": "alarm_loading", "count": 6}
        }
    
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        """Spielt einen Sound basierend auf dem ausgewählten Workflow ab."""
        print(f"[AUDIO] Feedback für Workflow: {workflow_name}")
        
        if workflow_name in self.workflow_sound_mapping:
            config = self.workflow_sound_mapping[workflow_name]
            file_name = self._get_random_file_name_from_category(config["category"], config["count"])
            if file_name:
                play(file_name)
        else:
            print(f"[AUDIO] Kein Sound-Mapping für Workflow '{workflow_name}' gefunden")
    
    def _get_random_file_name_from_category(self, category: str, count: int) -> Optional[str]:
        if count <= 0:
            return None
        
        random_index = random.randint(1, count)
        
        filename = f"tts_{category}_{random_index}"
        print(f"[AUDIO] Zufälliger Sound ausgewählt: {filename}")
        return filename