import os
import random
from typing import Dict, Any, Optional, TypedDict, List, Callable, Protocol
from abc import ABC, abstractmethod

from audio.audio_manager import AudioManager, play

# Interface für Beobachter
class WorkflowObserver(Protocol):
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        pass

class WorkflowAudioFeedbackObserver:
    def __init__(self):
        # Mapping von Workflow-Namen zu Sound-Kategorien und Anzahl verfügbarer Sounds
        self.workflow_sound_mapping = {
            "weather": {"category": "weather", "count": 6},
            "alarm": {"category": "alarm", "count": 4},  # Annahme: 4 Alarm-Sounds
            "todo": {"category": "todo", "count": 3},    # Annahme: 3 Todo-Sounds
            # Weitere Workflows hier zuordnen...
        }
    
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        """Spielt einen Sound basierend auf dem ausgewählten Workflow ab."""
        print(f"[AUDIO] Feedback für Workflow: {workflow_name}")
        
        if workflow_name in self.workflow_sound_mapping:
            config = self.workflow_sound_mapping[workflow_name]
            file_name = self._get_random_file_name_from_category(config["category"], config["count"])
            play(file_name)
    
    def _get_random_file_name_from_category(self, category: str, count: int) -> Optional[str]:
        if count <= 0:
            return None
        
        random_index = random.randint(1, count)
        
        filename = f"tts_{category}_{random_index}"
        print(f"[AUDIO] Zufälliger Sound ausgewählt: {filename}")
        return filename