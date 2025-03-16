from typing import Optional
from graphs.base_graph import BaseGraph

from tools.alarm.alarm_tools import get_alarm_tools

class AlarmWorkflow(BaseGraph):
    """Ein Workflow für Lichtsteuerung."""
    
    def __init__(self, model_name: Optional[str] = None):
        tools = get_alarm_tools()
        
        super().__init__(tools, model_name)

if __name__ == "__main__":
    workflow = AlarmWorkflow()
    workflow.run(input_message="Stelle einen Alarm für 7:30 Uhr morgens ein.", thread_id="lights_1")
    
    workflow_2 = AlarmWorkflow()
    workflow_2.run(input_message="Welche Alarme sind aktuell eingestellt?", thread_id="lights_1")
    
    workflow_3 = AlarmWorkflow()
    workflow_3.run(input_message="Deaktiviere bitte den aktuellen Alarm", thread_id="lights_1")