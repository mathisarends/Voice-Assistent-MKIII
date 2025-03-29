from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class State(TypedDict):
    """Basisklasse für alle Zustände in der Anwendung."""

    messages: Annotated[list, add_messages]
