from typing import Optional, Dict, Any, List
import asyncio
from langgraph.graph import StateGraph
from graphs.base_graph import BaseGraph
from states.state_definitions import State
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.second_brain.notion_project_repository import NotionProjectsRepository
from tools.notion.second_brain.notion_second_brain_notes_repository import NotionNotesRepository
from util.extract_user_message import extract_user_message

class SecondBrainWorkflowState(State):
    """State für den Second Brain Workflow."""
    # User input
    user_input: str = ""
    
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    
    # Verfügbare Projekte
    available_projects: List[Dict[str, Any]] = []

class SecondBrainWorkflow(BaseGraph):
    """Ein minimaler Workflow zur Identifikation des richtigen Projekts."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.notion_projects_repo = NotionProjectsRepository()
        self.notion_notes_repo = NotionNotesRepository()
        
        super().__init__(model_name=model_name)
        self.graph_builder = StateGraph(SecondBrainWorkflowState)
        
    
    def build_graph(self):
        self.graph_builder.add_node("identify_project", self._identify_project)
        self.graph_builder.set_entry_point("identify_project")
        
        graph = self.graph_builder.compile()
        
        return graph
    
    
    async def _identify_project(self, state: SecondBrainWorkflowState) -> SecondBrainWorkflowState:
        user_input = extract_user_message(state)
        state["user_input"] = user_input
        
        identified_project = await self.notion_projects_repo.identify_project_with_llm(user_input)
        
        state["project_id"] = identified_project["id"] if identified_project["id"] != "keine_übereinstimmung" else None
        state["project_name"] = identified_project["name"]
        
        # Füge eine Antwort hinzu
        if state["project_id"]:
            response_message = f"Projekt identifiziert: {state['project_name']} (ID: {state["project_id"]})"
        else:
            response_message = "Konnte kein passendes Projekt finden. Bitte spezifiziere das Projekt genauer."
        
        state["messages"].append({"role": "assistant", "content": response_message})
        
        return state
    
    async def run_workflow(self, user_input: str):
        """Führt den Workflow aus und gibt das Ergebnis zurück."""
        initial_state = SecondBrainWorkflowState(messages=[{"role": "user", "content": user_input}])
        
        graph = self.build_graph()
        
        final_state = await graph.ainvoke(initial_state)
        
        return final_state


# Test-Funktion
async def test_project_identification():
    """Testet die Projekt-Identifikation."""
    workflow = SecondBrainWorkflow()
    
    # Test-Anfragen
    test_requests = [
        "Speichere Informationen über das neue Browser-Use Framework in meinem Jarvis-Projekt",
        # "Erstelle eine Notiz zu Machine Learning Algorithmen im AI Research Projekt",
        # "Füge die Links zum neuen Design im Website Redesign Projekt hinzu"
    ]
    
    for request in test_requests:
        print(f"\n\nTest-Anfrage: {request}")
        result = await workflow.run_workflow(request)
        
        print(f"Identifiziertes Projekt: {result['project_name'] if 'project_name' in result and result['project_name'] else 'Keines'}")
        print(f"Projekt-ID: {result['project_id'] if 'project_id' in result and result['project_id'] else 'Keine'}")
        print(f"LLM-Antwort: {extract_user_message(result)}")

if __name__ == "__main__":
    asyncio.run(test_project_identification())