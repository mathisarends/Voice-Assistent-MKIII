from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Basisklasse für alle Tools in der Anwendung."""
    
    name: str
    description: str
    
    @abstractmethod
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Führt das Tool aus."""
        pass
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Gibt die Tooldefinition für LangChain zurück."""
        return {
            "name": self.name,
            "description": self.description
        }
