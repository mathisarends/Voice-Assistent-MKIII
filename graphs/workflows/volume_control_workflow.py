from typing import Optional
from graphs.base_graph import BaseGraph
from tools.volume.volume_control_tool import VolumeControlTool

class VolumeControlWorkflow(BaseGraph):
    def __init__(self, model_name: Optional[str] = None):
        volume_control_tool = VolumeControlTool()
        tools = [volume_control_tool]
        
        super().__init__(tools, model_name)
