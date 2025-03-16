from typing import Optional
from graphs.base_graph import BaseGraph

from tools.weather.weather_tool import WeatherTool

class WeatherWorkflow(BaseGraph):
    """Ein Workflow für Lichtsteuerung."""
    
    def __init__(self, model_name: Optional[str] = None):
        weather_tool = WeatherTool()
        
        super().__init__(tools=[weather_tool], model_name=model_name)

if __name__ == "__main__":
    workflow = WeatherWorkflow()
    workflow.run(input_message="Wie wird das Wetter heute?", thread_id="lights_1")