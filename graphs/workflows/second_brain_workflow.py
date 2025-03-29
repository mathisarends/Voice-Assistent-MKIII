import asyncio
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph

from graphs.core.base_graph import BaseGraph
from graphs.core.state_definitions import State
from tools.notion.second_brain.notion_project_repository import \
    NotionProjectsRepository
from tools.notion.second_brain.notion_second_brain_notes_repository import \
    NotionNotesRepository
from tools.tavily_tool import tavily_search
from util.extract_user_message import extract_user_message


class SecondBrainWorkflowState(State):
    """State für den Second Brain Workflow."""

    user_input: str = ""

    project_id: Optional[str] = None
    project_name: Optional[str] = None
    available_projects: List[Dict[str, Any]] = []
    research_results: Any = None

    search_query: str = ""

    # Speicherergebnisse
    note_id: Optional[str] = None
    note_url: Optional[str] = None
    note_title: Optional[str] = None


class SecondBrainWorkflow(BaseGraph):
    """Ein Workflow zur Identifikation des richtigen Projekts und Recherche von Informationen."""

    def __init__(self, model_name: Optional[str] = None):
        self.notion_projects_repo = NotionProjectsRepository()
        self.notion_notes_repo = NotionNotesRepository()
        self.tavily_search_tool = tavily_search

        super().__init__(model_name=model_name)
        self.graph_builder = StateGraph(SecondBrainWorkflowState)

    # TODO: Parallelisieren und RAG-System hierdrauf bauean
    def build_graph(self):
        # Nodes hinzufügen
        self.graph_builder.add_node("identify_project", self._identify_project)
        self.graph_builder.add_node("extract_search_query", self._extract_search_query)
        self.graph_builder.add_node("research_topic", self._research_topic)
        self.graph_builder.add_node("create_note", self._create_note)
        self.graph_builder.add_node("finalize_response", self._finalize_response)

        # Kanten definieren
        self.graph_builder.add_edge("identify_project", "extract_search_query")
        self.graph_builder.add_edge("extract_search_query", "research_topic")
        self.graph_builder.add_edge("research_topic", "create_note")
        self.graph_builder.add_edge("create_note", "finalize_response")

        # Startpunkt setzen
        self.graph_builder.set_entry_point("identify_project")

        graph = self.graph_builder.compile()

        return graph

    async def _identify_project(
        self, state: SecondBrainWorkflowState
    ) -> SecondBrainWorkflowState:
        user_input = extract_user_message(state)
        state["user_input"] = user_input

        identified_project = await self.notion_projects_repo.identify_project_with_llm(
            user_input
        )

        state["project_id"] = (
            identified_project["id"]
            if identified_project["id"] != "keine_übereinstimmung"
            else None
        )
        state["project_name"] = identified_project["name"]

        return state

    async def _extract_search_query(
        self, state: SecondBrainWorkflowState
    ) -> SecondBrainWorkflowState:
        """Extrahiert das Hauptthema aus der Anfrage für die Recherche."""
        prompt = f"""
        Identifiziere das Hauptthema für eine Recherche aus der folgenden Anfrage.
        Extrahiere nur das spezifische Thema, zu dem Informationen benötigt werden, 
        in präziser, suchmaschinenfreundlicher Form.
        
        Anfrage: {state["user_input"]}
        
        Identifiziertes Projekt: {state["project_name"]}
        
        Thema für Recherche:
        """

        response = await self.llm.ainvoke(prompt)
        state["search_query"] = response.content.strip()

        return state

    async def _research_topic(
        self, state: SecondBrainWorkflowState
    ) -> SecondBrainWorkflowState:
        """Führt eine Webrecherche zum identifizierten Thema durch."""
        if not state["search_query"]:
            state["research_results"] = (
                "Kein spezifisches Thema für die Recherche gefunden."
            )
            return state

        search_results = self.tavily_search_tool._run(state["search_query"])
        state["research_results"] = search_results

        return state

    async def _create_note(
        self, state: SecondBrainWorkflowState
    ) -> SecondBrainWorkflowState:
        """Erstellt eine Notiz mit den Recherche-Ergebnissen in Notion."""
        if not state["project_id"]:
            # Keine Notiz erstellen, wenn kein Projekt identifiziert wurde
            return state

        # Note-Titel generieren
        note_title = f"Recherche: {state['search_query']}"

        # Note-Inhalt aus Recherche-Ergebnissen erstellen
        note_content = self._format_research_results_for_note(
            state["research_results"], state["search_query"]
        )

        # Quelle der Notiz (optional)
        source = "Tavily Web Search"

        try:
            # Notiz in Notion erstellen
            note_info = await self.notion_notes_repo.create_note(
                title=note_title,
                project_id=state["project_id"],
                content=note_content,
                source=source,
            )

            # Notiz-Informationen im State speichern
            state["note_id"] = note_info["id"]
            state["note_url"] = note_info["url"]
            state["note_title"] = note_info["title"]

        except Exception as e:
            # Fehlerbehandlung
            error_message = f"Fehler beim Erstellen der Notiz: {str(e)}"
            print(error_message)
            state["messages"].append({"role": "assistant", "content": error_message})

        return state

    def _format_research_results_for_note(
        self, research_results, search_query: str
    ) -> str:
        """Formatiert die Recherche-Ergebnisse für die Notion-Notiz."""
        note_content = f"# Recherche zu '{search_query}'\n\n"
        note_content += "## Zusammenfassung\n\n"
        note_content += (
            "Dies ist eine automatisch generierte Notiz mit Recherche-Ergebnissen.\n\n"
        )
        note_content += "## Recherche-Ergebnisse\n\n"

        if isinstance(research_results, list):
            for idx, result in enumerate(research_results, 1):
                if isinstance(result, dict):
                    title = result.get("title", f"Ergebnis {idx}")
                    url = result.get("url", "Keine URL verfügbar")
                    content = result.get("content", "Kein Inhalt verfügbar")

                    note_content += f"### {idx}. {title}\n"
                    note_content += f"**Quelle:** {url}\n\n"
                    note_content += f"{content}\n\n"
                else:
                    note_content += f"### {idx}. Ergebnis\n"
                    note_content += f"{str(result)}\n\n"
        else:
            note_content += str(research_results)

        note_content += "\n\n## Weitere Schritte\n\n"
        note_content += "- Diese Notiz bearbeiten und verfeinern\n"
        note_content += "- Relevante Informationen extrahieren\n"
        note_content += "- Mit anderen Projekten oder Notizen verknüpfen\n"

        return note_content

    async def _finalize_response(
        self, state: SecondBrainWorkflowState
    ) -> SecondBrainWorkflowState:
        """Erstellt die finale Antwort basierend auf den Recherche-Ergebnissen und der erstellten Notiz."""
        # Antwort erstellen
        if state["project_id"]:
            project_info = f"Projekt identifiziert: {state['project_name']} (ID: {state['project_id']})"
        else:
            project_info = "Konnte kein passendes Projekt finden. Keine Notiz erstellt."

        # Notiz-Informationen
        note_info = ""
        if state.get("note_id"):
            note_info = f"\nNotiz erstellt: {state['note_title']}\n"
            note_info += f"Notiz-URL: {state['note_url']}\n"

        # Formate die Recherche-Ergebnisse für bessere Lesbarkeit in der Antwort
        research_summary = "Zusammenfassung der Recherche-Ergebnisse:\n"

        research_results = state["research_results"]
        if isinstance(research_results, list):
            for idx, result in enumerate(
                research_results[:3], 1
            ):  # Zeige nur die ersten 3 Ergebnisse
                if isinstance(result, dict):
                    title = result.get("title", f"Ergebnis {idx}")
                    url = result.get("url", "Keine URL verfügbar")

                    research_summary += f"\n{idx}. {title}\n"
                    research_summary += f"   URL: {url}\n"
                else:
                    research_summary += f"\n{idx}. {str(result)[:100]}...\n"

            if len(research_results) > 3:
                research_summary += f"\n... und {len(research_results) - 3} weitere Ergebnisse (vollständig in der Notion-Notiz)\n"
        else:
            research_summary += str(research_results)[:500] + "..."

        # Finale Antwort zusammenstellen
        response_message = f"{project_info}\n\n"
        response_message += f"Recherchiert zu: {state['search_query']}\n"
        response_message += note_info + "\n"
        response_message += research_summary
        response_message += "\n\nDie Informationen wurden erfolgreich recherchiert und in Notion gespeichert."

        state["messages"].append({"role": "assistant", "content": response_message})

        return state

    async def run_workflow(self, user_input: str):
        """Führt den Workflow aus und gibt das Ergebnis zurück."""
        initial_state = SecondBrainWorkflowState(
            messages=[{"role": "user", "content": user_input}]
        )

        graph = self.build_graph()

        final_state = await graph.ainvoke(initial_state)

        return final_state


# Test-Funktion
async def test_project_identification():
    """Testet die Projekt-Identifikation, Recherche und Notiz-Erstellung."""
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

        print(
            f"Identifiziertes Projekt: {result['project_name'] if 'project_name' in result and result['project_name'] else 'Keines'}"
        )
        print(
            f"Projekt-ID: {result['project_id'] if 'project_id' in result and result['project_id'] else 'Keine'}"
        )
        print(
            f"Suchanfrage: {result['search_query'] if 'search_query' in result else 'Keine'}"
        )

        if result.get("note_id"):
            print(f"Erstellte Notiz: {result['note_title']} (ID: {result['note_id']})")
            print(f"Notiz-URL: {result['note_url']}")
        else:
            print("Keine Notiz erstellt.")

        print(f"LLM-Antwort: {extract_user_message(result)}")


if __name__ == "__main__":
    asyncio.run(test_project_identification())
