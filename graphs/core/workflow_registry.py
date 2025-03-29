import logging
from typing import Any, Callable, Dict, List, Optional

from graphs.core.base_graph import BaseGraph
from graphs.workflows.youtube_summary_workflow import YoutubeSummaryWorkflow
from tools.alarm.alarm_tools import get_alarm_tools
from tools.light_tools import get_hue_tools
from tools.notion.todo.notion_todo_tools import get_notion_todo_tools
from tools.pomodoro.pomodoro_tools import get_pomodoro_tools
from tools.research_tools import get_research_tools
from tools.spotify_tools import get_spotify_tools
from tools.volume_control_tool import get_volume_tools


class WorkflowRegistry:
    """Registry für alle Workflows in der Anwendung."""

    _workflows: Dict[str, Dict[str, Any]] = {}
    _logger = logging.getLogger(__name__)

    @classmethod
    def register(
        cls,
        name: str,
        workflow_class,
        description: str,
        capabilities: Optional[List[str]] = None,
    ):
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
            "capabilities": capabilities or [],
        }
        cls._logger.info(f"Workflow '{name}' registriert: {description}")
        
    @classmethod
    def register_simple(
        cls,
        name: str,
        tools_provider: Callable[[], List[Any]],
        description: str,
        capabilities: Optional[List[str]] = None,
        speak_responses: bool = True,
        additional_tools: Optional[List[Callable]] = None
    ):
        """
        Registriert einen einfachen Workflow ohne eigene Klassenimplementierung.
        
        Args:
            name: Eindeutiger Name des Workflows
            tools_provider: Funktion, die die Tools für diesen Workflow liefert
            description: Beschreibung der Funktionalität des Workflows
            capabilities: Liste von Fähigkeiten des Workflows
            speak_responses: Ob Antworten gesprochen werden sollen
            additional_tools: Liste zusätzlicher Tool-Funktionen
        """

        # Factory-Funktion, die eine Closure über die Parameter erstellt
        def workflow_factory(model_name=None):
            return WorkflowRegistry.create_simple_workflow(
                tools_provider=tools_provider,
                model_name=model_name,
                speak_responses=speak_responses,
                additional_tools=additional_tools
            )
        
        cls._workflows[name] = {
            "class": workflow_factory,
            "description": description,
            "capabilities": capabilities or [],
            "is_simple": True  # Markierung für einfache Workflows
        }
        
        cls._logger.info(f"Einfacher Workflow '{name}' registriert: {description}")

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
            capabilities = (
                ", ".join(data["capabilities"])
                if data["capabilities"]
                else "Keine spezifischen Fähigkeiten"
            )
            formatted += (
                f"- {name}: {data['description']} (Fähigkeiten: {capabilities})\n"
            )
        return formatted

    @classmethod
    def get_workflow_names(cls) -> List[str]:
        """
        Gibt eine Liste aller registrierten Workflow-Namen zurück.

        Returns:
            Liste mit allen Workflow-Namen
        """
        return list(cls._workflows.keys())
    
    
    @staticmethod
    def create_simple_workflow(
        tools_provider: Callable[[], List[Any]],
        model_name: Optional[str] = None,
        speak_responses: bool = True,
        additional_tools: Optional[List[Callable]] = None
    ) -> BaseGraph:
        """
        Factory-Funktion für einfache Workflows ohne eigene Klasse.
        
        Args:
            tools_provider: Funktion, die die Tools für diesen Workflow liefert
            model_name: Optional, Name des zu verwendenden Modells
            speak_responses: Ob Antworten gesprochen werden sollen
            additional_tools: Liste zusätzlicher Tool-Funktionen
            
        Returns:
            Eine Instanz von BaseGraph mit den konfigurierten Tools
        """
        tools = tools_provider()
        
        # Zusätzliche Tools hinzufügen, falls vorhanden
        if additional_tools:
            for tool_fn in additional_tools:
                result = tool_fn()
                if isinstance(result, list):
                    tools.extend(result)
                else:
                    tools.append(result)
        
        return BaseGraph(
            tools=tools,
            model_name=model_name,
            speak_responses=speak_responses
        )



def register_workflows():
    """Registriert alle verfügbaren Workflows in der Registry."""
    WorkflowRegistry.register_simple(
        name="lights",
        tools_provider=get_hue_tools,
        speak_responses=False,
        description="Steuert Philips Hue Beleuchtung mit Szenen, Helligkeit und Ein-/Ausschalt-Funktionen",
        capabilities=["Beleuchtung", "Philips Hue", "Szenen", "Helligkeit", "Licht"],
    )
    
    WorkflowRegistry.register_simple(
        name="pomodoro",
        tools_provider=get_pomodoro_tools,
        speak_responses=False,
        description="Verwaltet Pomodoro-Timer für fokussierte Arbeitsintervalle und Pausen",
        capabilities=["Pomodoro", "Timer", "Fokus", "Produktivität", "Zeitmanagement"],
    )

    WorkflowRegistry.register_simple(
        name="alarm",
        tools_provider=get_alarm_tools,
        description="Verwaltet Alarme mit Wake-Up und Get-Up Phasen sowie Lichtwecker-Integration",
        capabilities=["Alarm", "Wecker", "Aufwachen", "Lichtwecker", "Timer"],
    )
    
    WorkflowRegistry.register_simple(
        name="notion_todo",
        tools_provider=get_notion_todo_tools,
        description="Verwaltet Notion-Tasks, Projekte und tägliche Top-Aufgaben für Produktivität",
        capabilities=["Notion", "To-Do", "Projektmanagement", "Produktivität", "Tägliche Aufgaben"],
    )
    
    WorkflowRegistry.register_simple(
        name="notion_clipboard",
        tools_provider=get_research_tools,
        description="Durchsucht das Web nach relevanten Informationen und speichert sie in der Notion zwischenablage",
        capabilities=["Recherche", "Websuche", "Notion", "Zwischenablage"],
    )

    WorkflowRegistry.register_simple(
        name="spotify",
        tools_provider=get_spotify_tools,
        speak_responses=False,
        description="Steuert Spotify-Wiedergabe, Lautstärke, Geräte und Playlists per Sprachbefehl",
        capabilities=["Musik", "Spotify", "Wiedergabe", "Playlist", "Lautstärke", "Geräte"],
    )

    WorkflowRegistry.register_simple(
        name="volume",
        tools_provider=get_volume_tools,
        speak_responses=False,
        description="Steuert die Systemlautstärke des Geräts mit einfachen Sprachbefehlen",
        capabilities=["Lautstärke", "Volume", "Audio", "Ton", "Sound"],
    )

    WorkflowRegistry.register(
        "youtube",
        YoutubeSummaryWorkflow,
        "Sucht und fasst YouTube-Videos zusammen und speichert sie in der Notion-Zwischenablage",
        ["YouTube", "Video", "Zusammenfassung", "Transkript", "Notion", "Recherche"],
    )
