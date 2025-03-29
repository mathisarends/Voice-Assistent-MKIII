from typing import Optional

from graphs.core.base_graph import BaseGraph
from tools.alarm.alarm_tools import get_alarm_tools


class AlarmWorkflow(BaseGraph):
    """Ein Workflow für Lichtsteuerung."""

    def __init__(self, model_name: Optional[str] = None):
        tools = get_alarm_tools()

        super().__init__(tools=tools, model_name=model_name)
