from datetime import datetime
import textwrap
from typing_extensions import Any, Dict, List, Optional, override
from graphs.base_graph import BaseGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph

from states.state_definitions import State
from tools.weather.weather_client import WeatherClient
from util.loggin_mixin import LoggingMixin


class WeatherWorkflowState(State):
    current_time: str = ""
    weather_data: Optional[List[str]] = None
    speech_result: str = ""
    

class WeatherWorkflow(BaseGraph, LoggingMixin):
    """Ein Workflow für Lichtsteuerung."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.weather_client = WeatherClient()
        
        super().__init__(model_name=model_name)
        self.graph_builder = StateGraph(WeatherWorkflowState)
        
        
    @override
    def build_graph(self):
        self.graph_builder.add_node("get_current_time", self._get_current_time)
        self.graph_builder.add_node("get_weather_data", self._get_weather_data)
        self.graph_builder.add_node("format_for_speech", self._format_for_speech)
        
        self.graph_builder.set_entry_point("get_current_time")
        
        self.graph_builder.add_edge("get_current_time", "get_weather_data")
        self.graph_builder.add_edge("get_weather_data", "format_for_speech")
        
        return self.graph_builder.compile()
    
    def _chatbot(self, state: WeatherWorkflowState) -> Dict[str, Any]:
        message = self.llm_with_tools.invoke(state["messages"])
        return {"messages": [message]}
    
    def _get_current_time(self, state: WeatherWorkflowState) -> str:
        print("current_time")
        state["current_time"] = datetime.now().strftime("%H:%M")
        return state
    
    async def _get_weather_data(self, state: WeatherWorkflowState):
        print("weather_data")
        state["weather_data"] = await self.weather_client.fetch_weather_data()
        print("weather_data fetched", state["weather_data"])
        return state
    
    async def _format_for_speech(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            weather_data = state.get("weather_data")
            current_time = state.get("current_time")
            
            # Wetterdaten zu einem Text zusammenfassen
            weather_text = "\n".join(weather_data)
            
            # System-Prompt für natürliche Sprachausgabe im Jarvis-Stil
            system_prompt = """
            Du bist ein hochentwickelter KI-Assistent mit einem präzisen, effizienten Kommunikationsstil, ähnlich wie Jarvis (ohne "Sir" zu verwenden).

            Deine Aufgabe ist es, Wetterinformationen in eine natürliche, gesprochene Form umzuwandeln.

            Beziehe dich NUR auf den aktuellen Tag und die nächsten Stunden.

            Folgende Richtlinien solltest du beachten:
            1. Sei präzise und direkt - vermittle die wichtigsten Informationen zuerst
            2. Halte die Antwort kurz und prägnant
            3. Verwende einen effizienten, selbstbewussten Ton
            4. Formuliere technisch präzise, aber verständlich
            5. Vermeide Füllwörter und überflüssige Höflichkeiten
            6. Hebe die aktuellen Bedingungen und relevante Veränderungen für die nächsten Stunden hervor
            7. Struktur: Aktuelle Bedingungen → Wichtige Änderungen → Empfehlungen (falls sinnvoll)

            Gib NUR die optimierte Antwort zurück, ohne Erklärungen oder zusätzlichen Text.
            """
            
            # Human-Prompt mit Wetterdaten und aktueller Zeit
            human_prompt = f"""
            Es ist {current_time} Uhr.

            Hier sind die Wetterdaten:

            {weather_text}

            Bitte wandle diese Informationen in eine natürliche, gesprochene Antwort um.
            Beziehe dich nur auf den heutigen Tag und die aktuelle Situation.
            """
            
            # LLM für Sprachoptimierung verwenden
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            # Optimierte Antwort speichern
            speech_result = response.content.strip()
            state["speech_result"] = speech_result
            
            # Für das Messaging-Format anpassen
            if "messages" not in state:
                state["messages"] = [{"role": "user", "content": "Wie ist das Wetter?"}]
            
            # Antwort als Nachricht hinzufügen
            state["messages"].append({"role": "assistant", "content": speech_result})
            
            return state
        
        except Exception as e:
            print(f"Fehler bei der Sprachoptimierung: {str(e)}")
            default_message = "Entschuldigung, ich konnte die Wetterinformationen nicht in Sprache umwandeln."
            state["speech_result"] = default_message
            if "messages" not in state:
                state["messages"] = [{"role": "user", "content": "Wie ist das Wetter?"}]
            state["messages"].append({"role": "assistant", "content": default_message})
            return state
            
        
    async def run_workflow(self, user_input: str):
            """Führt den Workflow aus und gibt das Ergebnis zurück."""
            initial_state = WeatherWorkflowState(messages=[{"role": "user", "content": user_input}])
            
            graph = self.build_graph()
            
            final_state = await graph.ainvoke(initial_state)
            
            return final_state