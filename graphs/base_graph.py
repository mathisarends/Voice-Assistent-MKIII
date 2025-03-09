from typing import List, Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from states.state_definitions import State
from tools.base import BaseTool
from config.settings import DEFAULT_LLM_MODEL

# TODO: Was hier auch cool wäre wenn das hier yielden würde.

class BaseGraph:
    """Basisklasse für alle Graph-Workflows in der Anwendung."""
    
    def __init__(
        self,
        tools: List[BaseTool], 
        model_name: Optional[str] = None
    ):
        self.tools = tools
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.graph_builder = StateGraph(State)
        self.llm = ChatAnthropic(model=self.model_name)
        self.llm_with_tools = self.llm.bind_tools(tools)
        self.memory = MemorySaver()
        
    def build_graph(self) -> StateGraph:
        """
        Baut den Graphen mit Standardknoten auf.
        """
        def chatbot(state: Dict[str, Any]) -> Dict[str, Any]:
            message = self.llm_with_tools.invoke(state["messages"])
            return {"messages": [message]}
            
        self.graph_builder.add_node("chatbot", chatbot)
        
        tool_node = ToolNode(tools=self.tools)
        self.graph_builder.add_node("tools", tool_node)
        
        self.graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
        )
        
        self.graph_builder.add_edge("tools", "chatbot")
        self.graph_builder.set_entry_point("chatbot")
        
        return self.graph_builder.compile(checkpointer=self.memory)
    
    def run(self, input_message: str, thread_id: Optional[str] = None) -> List[Dict[str, Any]]:
        graph = self.build_graph()
        config = {"configurable": {"thread_id": thread_id or "1"}}
        
        results = []
        events = graph.stream(
            {"messages": [{"role": "user", "content": input_message}]},
            config,
            stream_mode="values",
        )
        
        for event in events:
            if "messages" in event:
                event["messages"][-1].pretty_print()
                results.append(event)
                
        return results
    
    async def arun(self, input_message: str, thread_id: Optional[str] = None) -> List[Dict[str, Any]]:
        graph = self.build_graph()
        config = {"configurable": {"thread_id": thread_id or "1"}}
        
        results = []
        events = graph.astream(
            {"messages": [{"role": "user", "content": input_message}]},
            config,
            stream_mode="values",
        )
        
        async for event in events:
            if "messages" in event:
                event["messages"][-1].pretty_print()
                results.append(event)
                
        return results
