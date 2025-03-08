from typing import List
from dataclasses import dataclass, field

@dataclass
class NotionBlock:
    """Strukturierte Darstellung eines Notion-Blocks."""
    type: str
    text: str
    depth: int = 0
    children: List['NotionBlock'] = field(default_factory=list)