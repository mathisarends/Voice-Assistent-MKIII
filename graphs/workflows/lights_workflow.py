from typing import Optional
from graphs.base_graph import BaseGraph

from tools.lights.light_tools import get_hue_tools

class LightsWorkflow(BaseGraph):
    """Ein Workflow für Lichtsteuerung."""
    
    def __init__(self, model_name: Optional[str] = None):
        tools = get_hue_tools()
        
        super().__init__(tools, model_name)