from typing import AsyncGenerator, List, Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from states.state_definitions import State
from tools.base import BaseTool
from config.settings import DEFAULT_LLM_MODEL
from util.loggin_mixin import LoggingMixin


from langchain.schema import HumanMessage, AIMessage, SystemMessage
# TODO: Was hier auch cool wäre wenn das hier yielden würde, Performance

class BaseGraph(LoggingMixin):
    """Basisklasse für alle Graph-Workflows in der Anwendung."""
    
    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        model_name: Optional[str] = None
    ):
        self.tools = tools or []
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.graph_builder = StateGraph(State)
        
        self.llm = ChatAnthropic(model=self.model_name) # TODO: Diesem LLM hier einen SystemPrompt gebena
        
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.memory = MemorySaver()
        
    def build_graph(self):
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
    
    def run(self, input_message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        graph = self.build_graph()
        config = {"configurable": {"thread_id": thread_id or "1"}}
        
        final_message = None
        events = graph.stream(
            {"messages": [{"role": "user", "content": input_message}]},
            config,
            stream_mode="values",
        )
        
        for event in events:
            if "messages" in event:
                final_message = event["messages"][-1]
                final_message.pretty_print()
        
        return final_message.content

    async def arun(self, input_message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        graph = self.build_graph()
        config = {"configurable": {"thread_id": thread_id or "1"}}
        
        final_message = None
        events = graph.astream(
            {"messages": [{"role": "user", "content": input_message}]},
            config,
            stream_mode="values",
        )
        
        async for event in events:
            if "messages" in event:
                final_message = event["messages"][-1]
                final_message.pretty_print()
                
        print("final_message", final_message)
        
        return final_message.content
    
    async def arun_generator(self, input_message: str, thread_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        graph = self.build_graph()
        config = {"configurable": {"thread_id": thread_id or "1"}}

        events = graph.astream(
            {"messages": [{"role": "user", "content": input_message}]},
            config,
            stream_mode="values",
        )

        async for event in events:
            if "messages" in event and isinstance(event["messages"], list):
                for message in event["messages"]:
                    if isinstance(message, AIMessage):
                        # Extract text content, prioritizing text fields
                        if isinstance(message.content, list):
                            # For complex messages, extract text from first text-type entry
                            text_content = next(
                                (item['text'] for item in message.content if item.get('type') == 'text'), 
                                None
                            )
                            if text_content:
                                yield text_content
                        elif isinstance(message.content, str):
                            # For simple string messages
                            yield message.content