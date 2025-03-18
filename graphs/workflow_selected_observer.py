from typing import Dict, Any, TypedDict, List, Callable, Protocol
from abc import ABC, abstractmethod

# Interface für Beobachter
class WorkflowObserver(Protocol):
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        pass

# Audio-Feedback-Implementierung
class AudioFeedbackObserver:
    def on_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        """Spielt einen Sound basierend auf dem ausgewählten Workflow ab."""
        print(f"[AUDIO] Feedback für Workflow: {workflow_name}")