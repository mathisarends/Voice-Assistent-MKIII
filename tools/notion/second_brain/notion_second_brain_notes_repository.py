from textwrap import dedent
from typing import Dict, Any, Optional, TypedDict
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from config.notion_config import NOTION_DATABASES
from tools.notion.core.parsing.notion_markdown_parser import NotionMarkdownParser

class NoteInfo(TypedDict):
    """Definition für die Informationen einer Notiz."""
    title: str
    content: Optional[str]
    url: str
    id: str

class NotionNotesRepository(AbstractNotionClient):
    """Repository für die Verwaltung von Notizen in Notion."""
    
    def __init__(self,):
        super().__init__()
        self.notes_database_id = NOTION_DATABASES.get("WISSEN_NOTIZEN", "1a6389d5-7bd3-8097-aa38-e93cb052615a")
    
    async def create_note(self, 
                         title: str,
                         project_id: str,
                         content: Optional[str] = None,
                         source: Optional[str] = None) -> NoteInfo:
        """
        Erstellt eine neue Notiz in der Notion-Datenbank und verknüpft sie mit einem Projekt.
        
        Args:
            title: Der Titel der Notiz
            project_id: Die ID des Projekts, mit dem die Notiz verknüpft werden soll
            content: Der Inhalt der Notiz (optional)
            source: Die Quelle der Notiz (optional)
            
        Returns:
            Ein Dictionary mit Informationen über die erstellte Notiz
        """
        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "📁 Projekte": {
                "relation": [
                    {
                        "id": project_id
                    }
                ]
            }
        }
        
        if source:
            properties["Quelle"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": source
                        }
                    }
                ]
            }
            
        properties["Status"] = {
            "status": {
                "name": "Entwurf"
            }
        }
        
        request_body = {
            "parent": {
                "database_id": self.notes_database_id
            },
            "properties": properties
        }
        
        if content:
            content = dedent(content)  # Entfernt unnötige Einrückungen
            
            # Verwende den Markdown-Parser
            content_blocks = NotionMarkdownParser.parse_markdown(content)
            
            if content_blocks:
                for block in content_blocks:
                    block["object"] = "block"
                
                request_body["children"] = content_blocks
            else:
                request_body["children"] = [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": content
                                    }
                                }
                            ]
                        }
                    }
                ]
                
        
        response = await self._make_request("post", "pages", request_body)
        
        if response.status_code != 200:
            self.logger.error(f"Error creating note: {response.text}")
            raise Exception(f"Error creating note: {response.text}")
        
        response_data = response.json()
        
        return {
            "title": title,
            "content": content,
            "url": response_data.get("url", ""),
            "id": response_data.get("id", "")
        }
    
    async def get_note_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        response = await self._make_request("get", f"pages/{note_id}")
        
        if response.status_code != 200:
            self.logger.error(f"Error retrieving note: {response.text}")
            return None
            
        return response.json()
    
    async def update_note_content(self, note_id: str, content: str) -> bool:
        children_response = await self._make_request("get", f"blocks/{note_id}/children")
        
        if children_response.status_code != 200:
            self.logger.error(f"Error retrieving blocks: {children_response.text}")
            return False
            
        for block in children_response.json().get("results", []):
            await self._make_request("delete", f"blocks/{block['id']}")
        
        request_body = {
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        response = await self._make_request("patch", f"blocks/{note_id}/children", request_body)
        
        return response.status_code == 200

# Beispiel für die Verwendung
async def example_usage():
    """Zeigt die Verwendung des NotionNotesRepository."""
    notes_repo = NotionNotesRepository()
    
    try:
        # Erstelle eine neue Notiz
        new_note = await notes_repo.create_note(
            title="Testnotiz aus dem Repository",
            project_id="1a6389d5-7bd3-80ac-a51b-ea79142d8204",  
            content="Dies ist ein Test der NotionNotesRepository-Klasse.",
            source="Repository-Test"
        )
        
        print(f"Notiz erstellt: {new_note['title']}")
        print(f"URL: {new_note['url']}")
        print(f"ID: {new_note['id']}")
        
        # Optional: Aktualisiere den Inhalt
        # await notes_repo.update_note_content(
        #     note_id=new_note['id'],
        #     content="Dies ist der aktualisierte Inhalt der Testnotiz."
        # )
        
    except Exception as e:
        print(f"Fehler: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())