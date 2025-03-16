import datetime
from langchain.tools import BaseTool

class TimeTool(BaseTool):
    """Ein einfaches Tool, das das aktuelle Datum und die Uhrzeit liefert."""
    
    name: str = "get_current_time"
    description: str = "Gibt das aktuelle Datum und die aktuelle Uhrzeit in einem menschenlesbaren Format zurück."
    
    def _run(self) -> str:
        return self._get_time()

    async def _arun(self, *args, **kwargs) -> str:
        return self._get_time()
    
    def _get_time(self) -> str:
        """Gibt das aktuelle Datum und die Uhrzeit zurück."""
        now = datetime.datetime.now()
        return now.strftime("Datum: %Y-%m-%d Uhrzeit: %H:%M:%S")

# Testen des TimeTools
if __name__ == "__main__":
    time_tool = TimeTool()
    print(time_tool._run())
