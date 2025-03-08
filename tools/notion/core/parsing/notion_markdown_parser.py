import re
from typing import List, Dict, Any, Tuple, Optional

class NotionMarkdownParser:
    @staticmethod
    def parse_markdown(text: str) -> List[Dict[str, Any]]:
        """
        Hauptmethode zum Parsen von Markdown in Notion-Blocks.
        Hier findet die eigentliche Logik statt statt nur zu delegieren.
        """
        if not text:
            return []
            
        blocks = []
        for line in text.split('\n'):
            if not line.strip():
                continue
                
            block = NotionMarkdownParser._parse_line(line)
            if block:
                blocks.append(block)
                
        return blocks

    @staticmethod
    def _parse_line(line: str) -> Optional[Dict[str, Any]]:
        """
        Verarbeitet eine einzelne Zeile und bestimmt den Block-Typ.
        """
        parsers = [
            NotionMarkdownParser._parse_header,
            NotionMarkdownParser._parse_bullet_list,
            NotionMarkdownParser._parse_numbered_list,
        ]
        
        for parser in parsers:
            block = parser(line)
            if block:
                return block
                
        # Fallback zu Paragraph
        return {
            "type": "paragraph",
            "paragraph": {
                "rich_text": NotionMarkdownParser._parse_inline_formatting(line)
            }
        }

    @staticmethod
    def _parse_header(line: str) -> Optional[Dict[str, Any]]:
        """Parse header blocks."""
        header_match = re.match(r'^(#{1,6})\s(.+)$', line)
        if not header_match:
            return None
            
        level = len(header_match.group(1))
        content = header_match.group(2)
        return {
            "type": f"heading_{level}",
            f"heading_{level}": {
                "rich_text": NotionMarkdownParser._parse_inline_formatting(content)
            }
        }

    @staticmethod
    def _parse_bullet_list(line: str) -> Optional[Dict[str, Any]]:
        """Parse bullet list items."""
        list_match = re.match(r'^(\s*)[*\-+]\s(.+)$', line)
        if not list_match:
            return None
            
        content = list_match.group(2)
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": NotionMarkdownParser._parse_inline_formatting(content)
            }
        }

    @staticmethod
    def _parse_numbered_list(line: str) -> Optional[Dict[str, Any]]:
        """Parse numbered list items."""
        numbered_match = re.match(r'^\s*\d+\.\s(.+)$', line)
        if not numbered_match:
            return None
            
        content = numbered_match.group(1)
        return {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": NotionMarkdownParser._parse_inline_formatting(content)
            }
        }

    @staticmethod
    def _parse_inline_formatting(text: str) -> List[Dict[str, Any]]:
        """
        Verarbeitet Inline-Formatierungen mit reduzierter Komplexität.
        """
        if not text:
            return []

        elements = []
        segments = NotionMarkdownParser._split_text_into_segments(text)
        
        for segment in segments:
            element = NotionMarkdownParser._create_text_element(segment)
            if element:
                elements.append(element)
                
        return elements

    @staticmethod
    def _split_text_into_segments(text: str) -> List[Tuple[str, Dict[str, bool]]]:
        """
        Teilt Text in Segmente auf und identifiziert deren Formatierung.
        """
        patterns = [
            (r'\*\*(.+?)\*\*', {'bold': True}),
            (r'\*(.+?)\*', {'italic': True}),
            (r'_(.+?)_', {'italic': True}),
            (r'__(.+?)__', {'underline': True}),
            (r'~~(.+?)~~', {'strikethrough': True}),
            (r'`(.+?)`', {'code': True}),
            (r'\[(.+?)\]\((.+?)\)', {'link': True}),
        ]
        
        segments = []
        current_pos = 0
        
        while current_pos < len(text):
            earliest_match = None
            earliest_format = None
            earliest_pos = len(text)
            
            # Find next formatting
            for pattern, formatting in patterns:
                match = re.search(pattern, text[current_pos:])
                if match and (current_pos + match.start()) < earliest_pos:
                    earliest_match = match
                    earliest_format = formatting
                    earliest_pos = current_pos + match.start()
            
            if not earliest_match:
                # Add remaining text as plain segment
                if current_pos < len(text):
                    segments.append((text[current_pos:], {}))
                break
                
            # Add text before formatting as plain segment
            if earliest_pos > current_pos:
                segments.append((text[current_pos:earliest_pos], {}))
            
            # Add formatted segment
            content = earliest_match.group(1)
            if 'link' in earliest_format:
                url = earliest_match.group(2)
                segments.append((content, {'url': url}))
            else:
                segments.append((content, earliest_format))
            
            current_pos = earliest_pos + len(earliest_match.group(0))
            
        return segments

    @staticmethod
    def _create_text_element(segment: Tuple[str, Dict[str, bool]]) -> Dict[str, Any]:
        """
        Erstellt ein einzelnes Text-Element aus einem Segment.
        """
        text, formatting = segment
        
        if 'url' in formatting:
            return {
                "type": "text",
                "text": {
                    "content": text,
                    "link": {"url": formatting['url']}
                },
                "annotations": NotionMarkdownParser._default_annotations()
            }
            
        annotations = NotionMarkdownParser._default_annotations()
        annotations.update(formatting)
        
        return {
            "type": "text",
            "text": {"content": text},
            "annotations": annotations
        }

    @staticmethod
    def _default_annotations() -> Dict[str, bool]:
        """Erstellt Standard-Annotations-Objekt."""
        return {
            "bold": False,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default"
        }