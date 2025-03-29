from typing import Optional

from graphs.base_graph import BaseGraph
from tools.spotify_tools import get_spotify_tools


class SpotifyWorkflow(BaseGraph):
    """Ein Workflow für Lichtsteuerung."""

    def __init__(self, model_name: Optional[str] = None):
        tools = get_spotify_tools()

        super().__init__(tools=tools, model_name=model_name, speak_responses=False)
