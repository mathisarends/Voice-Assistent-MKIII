from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    """Basisklasse für alle Zustände in der Anwendung."""

    messages: Annotated[list, add_messages]
