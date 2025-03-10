from typing import Optional, Dict, Any, List
import asyncio
import json
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph
from config.notion_config import NOTION_DATABASES
from graphs.base_graph import BaseGraph
from states.state_definitions import State
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.second_brain.notion_project_repository import NotionProjectsRepository
from util.extract_user_message import extract_user_message

class SecondBrainWorkflowState(State):
    """State für den Second Brain Workflow."""
    # User input
    user_input: str = ""
    
    # Extrahierte Projekt-ID
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    
    # Verfügbare Projekte
    available_projects: List[Dict[str, Any]] = []

class SecondBrainWorkflow(BaseGraph):
    """Ein minimaler Workflow zur Identifikation des richtigen Projekts."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.notion_projects_repo = NotionProjectsRepository()
        super().__init__(model_name=model_name)
    
    def build_graph(self):
        """Baut einen einfachen Graphen mit einem Schritt auf."""
        graph_builder = StateGraph(SecondBrainWorkflowState)
        
        # Nur ein Schritt: Identifiziere das Projekt
        graph_builder.add_node("identify_project", self._identify_project)
        
        # Setze den Einstiegspunkt
        graph_builder.set_entry_point("identify_project")
        
        # Kompiliere den Graphen
        self.graph = graph_builder.compile()
        
        return self.graph
    
    async def _get_all_projects(self) -> List[Dict[str, Any]]:
        """Holt alle verfügbaren Projekte aus Notion."""
        notion_client = AbstractNotionClient()
        
        response = await notion_client._make_request(
            "post",
            "databases/" + self.projects_database_id + "/query",
            {}
        )
        
        if response.status_code != 200:
            print(f"Error retrieving projects: {response.text}")
            return []
            
        projects = response.json().get("results", [])
        
        # Wandle die Projekte in ein einfaches Format um
        formatted_projects = []
        for project in projects:
            # Extrahiere den Titel
            title = self._extract_page_title(project)
            project_id = project["id"]
            
            formatted_projects.append({
                "id": project_id,
                "name": title
            })
            
        return formatted_projects
    
    def _extract_page_title(self, page):
        """Extrahiert den Titel aus einem Seitenobjekt."""
        if "properties" in page and "title" in page.get("properties", {}):
            title_prop = page["properties"].get("title", {})
            if "title" in title_prop and title_prop["title"]:
                return title_prop["title"][0]["text"]["content"]
                
        if "properties" in page:
            for prop_name, prop_value in page["properties"].items():
                if prop_value.get("type") == "title" and prop_value.get("title"):
                    return prop_value["title"][0]["text"]["content"]
        
        if "title" in page:
            title_array = page.get("title", [])
            if title_array:
                return title_array[0]["text"]["content"]
                
        return "Unnamed Page"
    
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
        # Initialisiere den State
        initial_state = SecondBrainWorkflowState(messages=[{"role": "user", "content": user_input}])
        
        # Baue den Graphen
        graph = self.build_graph()
        
        # Führe den Graphen aus
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