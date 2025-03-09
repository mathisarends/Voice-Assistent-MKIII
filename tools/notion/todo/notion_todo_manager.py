import asyncio
import json
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.core.notion_pages import NotionPages

from dotenv import load_dotenv
load_dotenv()

class NotionTodoManager(AbstractNotionClient):
    def __init__(self):
        super().__init__()
        self.database_id = NotionPages.get_database_id("TODOS")

    async def add_todo(self, title, priority="Mittel", status="Nicht begonnen", done=False):
        data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Titel": {"title": [{"text": {"content": title}}]},
                "Priorität": {"select": {"name": priority}},
                "Status": {"status": {"name": status}},
                "Fertig": {"checkbox": done}
            }
        }

        try:
            response = await self._make_request("post", "pages", data)
            
            if response.status_code != 200:
                self.logger.error(lambda: f"❌ Error adding TODO: {response.text}")
                return f"❌ Error adding TODO: {response.text}"

            self.logger.info(lambda: f"✅ TODO added: {title}")
            return f"✅ TODO '{title}' added successfully."
                
        except Exception as e:
            self.logger.error(lambda: f"❌ API call failed: {str(e)}")
            return f"❌ API call failed: {str(e)}"

    async def get_all_todos(self):
        await self._delete_completed_todos()
        raw_todos = await self._get_raw_todos()
        return self._format_todo_list(raw_todos)

    async def get_daily_top_tasks(self):
        try:
            await self._delete_completed_todos()
            raw_todos = await self._get_raw_todos()
            daily_top_tasks = [todo for todo in raw_todos if todo["priority"] == "Daily Top Task"]
            return self._format_todo_list(daily_top_tasks)
        except Exception as e:
            self.logger.error(lambda: f"❌ API call failed: {str(e)}")
            return f"API call failed: {str(e)}"
            
    async def get_todos_by_project(self, project_name=None, project_id=None):
        """
        Holt alle TODOs für ein bestimmtes Projekt, sortiert nach Priorität.
        
        Args:
            project_name (str, optional): Name des Projekts aus PROJECT_PAGES (z.B. "JARVIS_PROJECT")
            project_id (str, optional): Direkte ID des Projekts (z.B. "1a6389d5-7bd3-80ac-a51b-ea79142d8204")
            
        Returns:
            str: Formatierte Liste der TODOs zum angegebenen Projekt
        """
        try:
            # Wenn ein Projektname angegeben wurde, versuchen wir die ID zu bekommen
            if project_name and not project_id:
                # Da wir die Methode get_project_page_id nicht kennen, 
                # verwenden wir hier einen Workaround über PROJECT_PAGES
                from tools.notion.core.notion_pages import PROJECT_PAGES
                project_id = PROJECT_PAGES.get(project_name.upper())
                if not project_id:
                    return f"❌ Unbekanntes Projekt: {project_name}"
            
            # Wenn keine gültige Projekt-ID vorliegt, brechen wir ab
            if not project_id:
                return "❌ Keine gültige Projekt-ID angegeben"
                
            # Alle TODOs abrufen und die abgeschlossenen löschen
            await self._delete_completed_todos()
            raw_todos = await self._get_raw_todos()
            
            # Nach Projekt-ID filtern
            project_todos = [
                todo for todo in raw_todos 
                if project_id in todo["project_ids"]
            ]
            
            # Wenn keine TODOs gefunden wurden
            if not project_todos:
                project_name_display = project_name or NotionPages.get_project_name_by_id(project_id)
                return f"Keine offenen TODOs für Projekt '{project_name_display}' gefunden."
            
            return self._format_todo_list(project_todos)
            
        except Exception as e:
            self.logger.error(lambda: f"❌ API call failed: {str(e)}")
            return f"❌ API call failed: {str(e)}"
    
    async def _get_raw_todos(self):
        try:
            results = await self._fetch_todos_from_notion()
            for item in results[:5]:
                print(f"ID: {item.get('id')}")
                print(f"Properties: {json.dumps(item.get('properties'), indent=2)}")
                print("---")
            
            if not results:
                return []
            
            open_todos = self._process_todo_results(results)
            return self._sort_todos_by_priority(open_todos)
            
        except Exception as e:
            self.logger.error(lambda: f"❌ API call failed: {str(e)}")
            return []

    async def _fetch_todos_from_notion(self):
        response = await self._make_request("post", f"databases/{self.database_id}/query")
        return response.json().get("results", [])

    def _process_todo_results(self, results):
        open_todos = []
        
        for item in results:
            # Nur offene TODOs verarbeiten
            if item.get("properties", {}).get("Fertig", {}).get("checkbox", True):
                continue
            
            try:
                todo_item = self._extract_todo_data(item)
                if todo_item:
                    open_todos.append(todo_item)
            except Exception as e:
                self.logger.error(lambda: f"❌ Error processing TODO item: {str(e)}")
        
        return open_todos

    def _extract_todo_data(self, item):
        # Titel extrahieren
        title_content = item.get("properties", {}).get("Titel", {}).get("title", [])
        title = "Untitled Task"
        if title_content and len(title_content) > 0:
            title = title_content[0].get("text", {}).get("content", "Untitled Task")
        
        # Priorität extrahieren
        priority = item.get("properties", {}).get("Priorität", {}).get("select", {})
        priority_name = priority.get("name", "Mittel") if priority else "Mittel"
        
        # Status extrahieren
        status = item.get("properties", {}).get("Status", {}).get("status", {})
        status_name = status.get("name", "Nicht begonnen") if status else "Nicht begonnen"
        
        # Projekt-IDs extrahieren
        project_relation = item.get("properties", {}).get("Projekt", {}).get("relation", [])
        project_ids = [relation.get("id") for relation in project_relation if relation.get("id")]
        
        # Projektnamen aus IDs ermitteln
        project_names = []
        for project_id in project_ids:
            project_name = NotionPages.get_project_name_by_id(project_id)
            if project_name != "UNKNOWN_PROJECT":
                project_names.append(project_name)
        
        return {
            "id": item.get("id", ""),
            "title": title,
            "priority": priority_name,
            "status": status_name,
            "done": False,
            "project_ids": project_ids,
            "project_names": project_names
        }

    def _sort_todos_by_priority(self, todos):
        priority_order = {
            "Daily Top Task": 1,
            "Hoch": 2,
            "Mittel": 3,
            "Niedrig": 4
        }
        
        return sorted(todos, key=lambda todo: priority_order.get(todo["priority"], 99))

    def _format_todo_list(self, todos):
        if not todos:
            return "Keine offenen TODOs vorhanden."

        formatted_todos = []
        for i, todo in enumerate(todos):
            # Basis-Information
            formatted_todo = f"{i + 1}. {todo['title']} (Priorität: {todo['priority']}, Status: {todo['status']}"
            
            # Projektnamen hinzufügen, falls vorhanden
            if todo.get("project_names") and len(todo["project_names"]) > 0:
                projects_str = ", ".join(todo["project_names"])
                formatted_todo += f", Projekte: {projects_str}"
            
            formatted_todo += ")"
            formatted_todos.append(formatted_todo)
            
        return "\n".join(formatted_todos)
    
    async def _delete_completed_todos(self):
        try:
            results = await self._fetch_todos_from_notion()
            
            completed_todos = [
                item.get("id") for item in results 
                if item.get("properties", {}).get("Fertig", {}).get("checkbox", False)
            ]
            
            if not completed_todos:
                return
                
            async def delete_todo(todo_id):
                try:
                    response = await self._make_request("delete", f"pages/{todo_id}")
                    if response.status_code == 200:
                        return True
                    else:
                        self.logger.error(lambda: f"❌ Fehler beim Löschen von TODO {todo_id}: {response.text}")
                        return False
                except Exception as e:
                    self.logger.error(lambda: f"❌ Fehler beim Löschen von TODO {todo_id}: {str(e)}")
                    return False
            
            results = await asyncio.gather(*[delete_todo(todo_id) for todo_id in completed_todos])
            
            deleted_count = sum(1 for result in results if result)
            
            if deleted_count > 0:
                self.logger.info(lambda: f"✅ {deleted_count} abgeschlossene TODOs gelöscht")
                
        except Exception as e:
            self.logger.error(lambda: f"❌ Fehler beim Aufräumen der TODOs: {str(e)}")
    
async def main():
    notion_todo_manager = NotionTodoManager()
    # Beispiele für verschiedene Aufrufmöglichkeiten:
    # print(await notion_todo_manager.get_all_todos())
    # print(await notion_todo_manager.get_daily_top_tasks())
    
    # TODOs für ein Projekt nach Namen abrufen
    print("TODOs für JARVIS_PROJECT:")
    print(await notion_todo_manager.get_todos_by_project(project_name="JARVIS_PROJECT"))
    
    # TODOs für ein Projekt direkt nach ID abrufen
    print("\nTODOs für Projekt mit ID '1a6389d5-7bd3-80ac-a51b-ea79142d8204':")
    print(await notion_todo_manager.get_todos_by_project(project_id="1a6389d5-7bd3-80ac-a51b-ea79142d8204"))
    
if __name__ == "__main__":
    asyncio.run(main())