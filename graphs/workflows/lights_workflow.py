from typing import Optional

from graphs.core.base_graph import BaseGraph
from tools.light_tools import get_hue_tools
from tools.time_tool import get_current_time


class LightsWorkflow(BaseGraph):
    def __init__(self, model_name: Optional[str] = None):
        tools = get_hue_tools() + [get_current_time()]
        super().__init__(speak_responses=False, tools=tools, model_name=model_name)
