from typing import Optional
from graphs.base_graph import BaseGraph
from tools.volume.volume_control_tool import get_volume_tools

class VolumeControlWorkflow(BaseGraph):
    def __init__(self, model_name: Optional[str] = None):
        tools =  get_volume_tools()
        
        # TODO: Müsste eigentlich heißen use_cache_for_responses
        super().__init__(speak_responses=False, tools=tools, model_name=model_name)
