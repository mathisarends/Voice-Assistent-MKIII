import logging
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.core.notion_pages import NotionPages

class SecondBrainManager(AbstractNotionClient):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.database_id = NotionPages.get_database_id("WISSEN_NOTIZEN")
        
        
    async def capture_idea(self, title: str) -> str:
        default_status = "Entwurf"

        data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": title}}]
                },
                "Status": {
                    "status": {"name": default_status}
                }
            }
        }

        try:
            response = await self._make_request("post", "pages", data)
            if response is None:
                return "❌ Keine Antwort vom Server (response is None)."

            if response.status_code == 200:
                self.logger.info(f"Idee '{title}' erfolgreich in SecondBrain erfasst.")
                return f"✅ Idee '{title}' erfolgreich erfasst."
            else:
                error_text = response.text
                self.logger.error(f"Fehler beim Erfassen der Idee '{title}': {error_text}")
                return f"❌ Fehler beim Erfassen der Idee '{title}': {error_text}"
            
        except Exception as e:
            self.logger.error(f"❌ API call failed: {str(e)}")
            return f"❌ API call failed: {str(e)}"


if __name__ == "__main__":
    second_brain_manager = SecondBrainManager()
    print(second_brain_manager.capture_idea("Neue Minimal-Idee für Second Brain"))