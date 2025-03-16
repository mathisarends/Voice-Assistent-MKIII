from typing import Optional
from graphs.base_graph import BaseGraph

from tools.spotify.spotify_tools import get_spotify_tools

class SpotifyWorkflow(BaseGraph):
    """Ein Workflow für Lichtsteuerung."""
    
    def __init__(self, model_name: Optional[str] = None):
        tools = get_spotify_tools()
        
        super().__init__(tools, model_name)
        
        
async def main() -> None:
    workflow = SpotifyWorkflow()
    await workflow.arun(input_message="Gebe mir Informationen über den aktuellen Track", thread_id="lights_1")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())