import os
import logging
import sys
from abc import ABC
from dotenv import load_dotenv
import httpx

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
load_dotenv()

class AbstractNotionClient(ABC):
    """Abstract base class for Notion API interactions."""
    
    NOTION_TOKEN = os.getenv("NOTION_SECRET")
    
    HEADERS = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    def __init__(self):
        self.client = httpx.AsyncClient()
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger.info("%s initialized.", self.__class__.__name__)

    async def _make_request(self, method: str, endpoint: str, data=None):
        """Makes a request to the Notion API."""
        url = f"https://api.notion.com/v1/{endpoint}"
        
        try:
            if method.lower() == "get":
                response = await self.client.get(url, headers=self.HEADERS)
            elif method.lower() == "post":
                response = await self.client.post(url, headers=self.HEADERS, json=data)
            elif method.lower() == "patch":
                response = await self.client.patch(url, headers=self.HEADERS, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            return {"error": f"API request failed: {str(e)}"}