import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from agents.tools.notion.core.abstract_notion_client import AbstractNotionClient

class NotionUtility(AbstractNotionClient):
    """Utility class for general Notion operations."""
    
    async def get_accessible_pages(self):
        """Retrieves all Notion pages accessible with the current API token."""
        response = await self._make_request(
            "post", 
            "search", 
            {"filter": {"value": "page", "property": "object"}}
        )

        if response.status_code != 200:
            self.logger.error(f"Error retrieving pages: {response.text}")
            return f"Error retrieving pages: {response.text}"

        pages = response.json().get("results", [])
        if not pages:
            return "No accessible pages found."

        formatted_pages = []
        for page in pages:
            page_id = page["id"]
            title = self._extract_page_title(page)
            formatted_pages.append(f"- {title} (ID: {page_id})")

        return "\nAccessible Pages:\n" + "\n".join(formatted_pages)
    
    async def get_page_children(self, page_id):
        response = await self._make_request("get", f"blocks/{page_id}/children")

        if response.status_code != 200:
            self.logger.error(f"Error retrieving blocks: {response.text}")
            return f"Error retrieving blocks: {response.text}"

        return response.json()
    
    def format_page_children(self, response_json):
        """Parses and formats Notion page children to display only databases with their IDs."""
        results = response_json.get("results", [])
        
        databases = []
        for block in results:
            if block["type"] == "child_database":
                db_name = block["child_database"]["title"]
                db_id = block["id"]
                databases.append(f"- {db_name} (ID: {db_id})")

        if not databases:
            return "No databases found on this page."

        return "\nAccessible Databases:\n" + "\n".join(databases)
    
    async def get_database_schema(self, database_id):
        response = await self._make_request("get", f"databases/{database_id}")

        if response.status_code != 200:
            self.logger.error(f"Error retrieving database: {response.text}")
            return f"Error retrieving database: {response.text}"

        return response.json()
    
    def _extract_page_title(self, page):
        if "properties" in page and "title" in page.get("properties", {}):
            title_property = page.get("properties", {}).get("title", {}).get("title", [])
            if title_property:
                return title_property[0]["text"]["content"]
                
        if "title" in page:
            title_array = page.get("title", [])
            if title_array:
                return title_array[0]["text"]["content"]
                
        return "Unnamed Page"
    
    
if __name__ == "__main__":
    util = NotionUtility()

    # - Jarvis Clipboard (ID: 1a3389d5-7bd3-80d7-a507-e67d1b25822c)
    # - Second Brain (ID: 1a6389d5-7bd3-80c5-9a87-e90b034989d0)
    # - TODOs & Ideen (ID: 1a6389d5-7bd3-80b2-a8a7-e1e93f4d8dac)
    # - Wissens & Notizen Datenbank  1a6389d5-7bd3-8097-aa38-e93cb052615a

    print(util.get_database_schema("1a6389d5-7bd3-8097-aa38-e93cb052615a"))