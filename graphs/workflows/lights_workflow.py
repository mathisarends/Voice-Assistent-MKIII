from typing import Optional
from graphs.base_graph import BaseGraph

from tools.lights.light_tools import get_hue_tools
from tools.time.time_tool import TimeTool

class LightsWorkflow(BaseGraph):
    def __init__(self, model_name: Optional[str] = None):
        tools = get_hue_tools() + [TimeTool()]
        super().__init__(tools, model_name)