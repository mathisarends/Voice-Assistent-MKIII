from typing import List
from tools.notion.core.parsing.notion_block import NotionBlock

class NotionMarkdownConverter:
    """Konvertiert Notion-Blöcke in Markdown mit integrierter Mapping-Logik."""
    
    BLOCK_TYPE_MAPPINGS = {
        "heading_1": lambda text, depth: f"# {text}",
        "heading_2": lambda text, depth: f"## {text}",
        "heading_3": lambda text, depth: f"### {text}",
        "bulleted_list_item": lambda text, depth: f"{'  ' * depth}- {text}",
        "numbered_list_item": lambda text, depth: f"{'  ' * depth}1. {text}",
        "quote": lambda text, depth: f"> {text}",
        "code": lambda text, depth: f"```\n{text}\n```",
        "toggle": lambda text, depth: f"**{text}**",
        "paragraph": lambda text, depth: text,
        "default": lambda text, depth: text
    }

    def convert_block_to_markdown(self, block: NotionBlock) -> List[str]:
        """
        Konvertiert einen Notion-Block rekursiv in Markdown.
        
        Args:
            block (NotionBlock): Der zu konvertierende Block.
        
        Returns:
            List[str]: Liste von Markdown-Zeilen.
        """
        # Konvertiere den aktuellen Block
        converter = self.BLOCK_TYPE_MAPPINGS.get(block.type, self.BLOCK_TYPE_MAPPINGS['default'])
        markdown_lines = [converter(block.text, block.depth)]
        
        # Rekursive Verarbeitung der Kindblöcke
        for child in block.children:
            markdown_lines.extend(self.convert_block_to_markdown(child))
        
        return markdown_lines