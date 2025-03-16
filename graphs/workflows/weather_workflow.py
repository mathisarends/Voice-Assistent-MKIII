from datetime import datetime
from typing import Any, Dict, List, Optional, override
from graphs.base_graph import BaseGraph
from langchain_core.messages import HumanMessage, SystemMessage

from states.state_definitions import State
from tools.weather.weather_tool import WeatherClient, WeatherTool
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
        
        
    @override
    def build_graph(self) -> BaseGraph:
        
        self.graph_builder.add_node("chatbot", self._chatbot)
        self.graph_builder.add_node("get_current_time", self._get_current_time)
        self.graph_builder.add_node("get_weather_data", self._get_weather_data)
        self.graph_builder.add_node("format_for_speech", self._format_for_speech)
        
        self.graph_builder.set_entry_point("chatbot")
        
        self.graph_builder.add_edge("chatbot", "get_weather_data")
        self.graph_builder.add_edge("chatbot", "get_current_time")
        
        self.graph_builder.add_edge("get_current_time", "format_for_speech")
        self.graph_builder.add_edge("get_weather_data", "format_for_speech")
        
        graph = self.graph_builder.compile()
            
        return graph
    
    def _chatbot(self, state: WeatherWorkflowState) -> Dict[str, Any]:
        message = self.llm_with_tools.invoke(state["messages"])
        return {"messages": [message]}
    
    def _get_current_time(self, state: WeatherWorkflowState) -> str:
        state["current_time"] = datetime.now().strftime("%H:%M")
        return state
    
    async def _get_weather_data(self, state: WeatherWorkflowState):
        state["weather_data"] = await self.weather_client.fetch_weather_data()
        return state
    
    async def _format_for_speech(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            weather_data = state.get("weather_data")
            current_time = state.get("current_time")
            
            # Wetterdaten zu einem Text zusammenfassen
            weather_text = "\n".join(weather_data)
            
            # System-Prompt für natürliche Sprachausgabe
            system_prompt = """
            Deine Aufgabe ist es, Wetterinformationen in eine natürliche, gesprochene Form umzuwandeln.
            
            Folgende Richtlinien solltest du beachten:
            1. Formuliere die Antwort so, als würdest du mit jemandem sprechen, nicht als würdest du einen Text schreiben
            2. Halte die Antwort kurz und prägnant
            3. Hebe die wichtigsten Informationen hervor (aktuelle Temperatur, Wetterlage)
            4. Verwende gesprächstypische Formulierungen (z.B. "Es sind aktuell 14 Grad bei leichtem Regen.")
            5. Vermeide Aufzählungen, Listen oder technische Formatierungen
            6. Erwähne die Tageszeit und beziehe dich auf den Rest des Tages, wenn relevant
            
            Gib NUR die optimierte Antwort zurück, ohne Erklärungen oder zusätzlichen Text.
            """
            
            # Human-Prompt mit Wetterdaten und aktueller Zeit
            human_prompt = f"""
            Es ist {current_time} Uhr.
            
            Hier sind die Wetterdaten:
            
            {weather_text}
            
            Bitte wandle diese Informationen in eine natürliche, gesprochene Antwort um.
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
            
            # Debug-Ausgabe
            self.logger.info(f"Sprachoptimierung abgeschlossen: {len(speech_result)} Zeichen")
            
            return state
        
        except Exception as e:
            print(f"Fehler bei der Sprachoptimierung: {str(e)}")
            default_message = "Entschuldigung, ich konnte die Wetterinformationen nicht in Sprache umwandeln."
            state["speech_result"] = default_message
            if "messages" not in state:
                state["messages"] = [{"role": "user", "content": "Wie ist das Wetter?"}]
            state["messages"].append({"role": "assistant", "content": default_message})
            return state

async def main():
    workflow = WeatherWorkflow()
    
    return await workflow.arun(input_message="Wie wird das Wetter heute?", thread_id="lights_1")

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(main())
    print(result)
