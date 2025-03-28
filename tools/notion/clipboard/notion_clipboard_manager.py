from textwrap import dedent

from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.core.notion_pages import NotionPages
from tools.notion.core.parsing.notion_markdown_parser import NotionMarkdownParser


class NotionClipboardManager(AbstractNotionClient):
    """Class for managing clipboard content in Notion."""

    def __init__(self):
        super().__init__()
        self.clipboard_page_id = NotionPages.get_page_id("JARVIS_CLIPBOARD")

    async def append_to_clipboard(self, text):
        """Appends formatted text to the clipboard page with a divider."""
        divider_block = {"type": "divider", "divider": {}}

        text = dedent(text)
        content_blocks = NotionMarkdownParser.parse_markdown(text)

        data = {"children": [divider_block] + content_blocks}

        response = await self._make_request(
            "patch", f"blocks/{self.clipboard_page_id}/children", data
        )

        if response.status_code == 200:
            self.logger.info("Text successfully added to clipboard page.")
            return "Text successfully added to clipboard page."
        else:
            self.logger.error(f"Error adding text: {response.text}")
            return f"Error adding text: {response.text}"
