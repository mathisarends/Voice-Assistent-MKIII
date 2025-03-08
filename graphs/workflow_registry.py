from typing import Dict, Any, List, Optional


class WorkflowRegistry:
    """Registry für alle Workflows in der Anwendung."""
    
    _workflows: Dict[str, Dict[str, Any]] = {}
    
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
        print(f"Workflow '{name}' registriert: {description}")
    
    @classmethod
    def get_workflow(cls, name: str):
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
