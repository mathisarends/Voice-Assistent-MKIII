import logging
from typing import Dict, Any, List, Optional

from graphs.base_graph import BaseGraph
from graphs.workflows.alarm_workflow import AlarmWorkflow
from graphs.workflows.lights_workflow import LightsWorkflow
from graphs.workflows.notion_todo_workflow import NotionTodoWorkflow
from graphs.workflows.research_workflow import ResearchWorkflow
from graphs.workflows.spotify_workflow import SpotifyWorkflow
from graphs.workflows.weather_workflow import WeatherWorkflow
from tools.time.time_tool import TimeTool
from util.loggin_mixin import LoggingMixin

class WorkflowRegistry():
    """Registry für alle Workflows in der Anwendung."""
    
    _workflows: Dict[str, Dict[str, Any]] = {}
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def register(cls, name: str, workflow_class, description: str, capabilities: Optional[List[str]] = None):
        """
        Registriert einen Workflow mit Metadaten.
        
        Args:
            name: Eindeutiger Name des Workflows
            workflow_class: Klasse des Workflows
            description: Beschreibung der Funktionalität des Workflows
            capabilities: Liste von Fähigkeiten des Workflows
        """
        cls._workflows[name] = {
            "class": workflow_class,
            "description": description,
            "capabilities": capabilities or []
        }
        # print-Statement durch Logger-Aufruf ersetzen
        cls._logger.info(f"Workflow '{name}' registriert: {description}")
    
    @classmethod
    def get_workflow(cls, name: str) -> BaseGraph:
        """
        Gibt eine Workflow-Klasse zurück.
        
        Args:
            name: Name des Workflows
            
        Returns:
            Die Workflow-Klasse oder None, wenn nicht gefunden
        """
        return cls._workflows.get(name, {}).get("class")
    
    @classmethod
    def get_all_workflows(cls) -> Dict[str, Dict[str, Any]]:
        """
        Gibt alle registrierten Workflows mit Metadaten zurück.
        
        Returns:
            Dictionary mit allen Workflows und ihren Metadaten
        """
        return cls._workflows
    
    @classmethod
    def format_for_prompt(cls) -> str:
        """
        Formatiert die Workflow-Informationen für einen LLM-Prompt.
        
        Returns:
            Formatierter String mit Workflow-Informationen
        """
        formatted = ""
        for name, data in cls._workflows.items():
            capabilities = ", ".join(data["capabilities"]) if data["capabilities"] else "Keine spezifischen Fähigkeiten"
            formatted += f"- {name}: {data['description']} (Fähigkeiten: {capabilities})\n"
        return formatted
    
    @classmethod
    def get_workflow_names(cls) -> List[str]:
        """
        Gibt eine Liste aller registrierten Workflow-Namen zurück.

        Returns:
            Liste mit allen Workflow-Namen
        """
        return list(cls._workflows.keys())

def register_workflows():
    """Registriert alle verfügbaren Workflows in der Registry."""
    WorkflowRegistry.register(
        "lights",
        LightsWorkflow,
        "Steuert Philips Hue Beleuchtung mit Szenen, Helligkeit und Ein-/Ausschalt-Funktionen",
        ["Beleuchtung", "Philips Hue", "Szenen", "Helligkeit", "Licht"]
    )
    
    WorkflowRegistry.register(
        "alarm",
        AlarmWorkflow,
        "Verwaltet Alarme mit Wake-Up und Get-Up Phasen sowie Lichtwecker-Integration",
        ["Alarm", "Wecker", "Aufwachen", "Lichtwecker", "Timer"]
    )
    
    WorkflowRegistry.register(
        "weather",
        WeatherWorkflow,
        "Liefert aktuelle Wetterinformationen und bereitet sie für Sprachwiedergabe auf",
        ["Wetter", "Vorhersage", "Sprachsteuerung", "Temperatur", "Regen"]
    )
    
    WorkflowRegistry.register(
        "time",
        TimeTool,
        "Gibt das aktuelle Datum und die Uhrzeit zurück",
        ["Zeit", "Datum", "Uhrzeit"]
    )
    
    WorkflowRegistry.register(
        "spotify",
        SpotifyWorkflow,
        "Steuert Spotify-Wiedergabe, Lautstärke, Geräte und Playlists per Sprachbefehl",
        ["Musik", "Spotify", "Wiedergabe", "Playlist", "Lautstärke", "Geräte"]
    )
    
    WorkflowRegistry.register(
        "notion_todo",
        NotionTodoWorkflow,
        "Verwaltet Notion-Tasks, Projekte und tägliche Top-Aufgaben für Produktivität",
        ["Notion", "To-Do", "Projektmanagement", "Produktivität", "Tägliche Aufgaben"]
    )
    
    WorkflowRegistry.register(
        "notion_clipboard",
        ResearchWorkflow,
        "Durchsucht das Web nach relevanten Informationen und speichert sie in der Notion zwischenablage",
        ["Recherche", "Websuche", "Notion", "Zwischenablage"]
    )