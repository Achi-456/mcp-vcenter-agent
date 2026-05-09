import json
import logging
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage

from app.graph.state import AgentState
from app.llm.provider_factory import factory as llm_factory
from app.prompts.vcenter_admin import SYSTEM_PROMPT
from app.tools.registry import get_langchain_tools

logger = logging.getLogger(__name__)

async def agent_node(state: AgentState) -> dict[str, Any]:
    """Invoke the LLM with bound tools."""
    messages = state.get("messages", [])
    if not messages:
        user_msg = state.get("user_message", "")
        if user_msg:
            messages = [HumanMessage(content=user_msg)]
            
    # Add system prompt if not present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    provider = state.get("provider", "gemini")
    model = state.get("model", "gemini-2.5-flash")

    # Fallback to gemini if client fails
    client = llm_factory.get_client(provider)
    
    tools = get_langchain_tools()
    
    # Check if the client supports LangChain's ChatModels natively. 
    # Since we installed langchain-google-genai, etc., we can create the ChatModel instance directly
    chat_model = None
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        import os
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            chat_model = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            chat_model = ChatOpenAI(model=model, openai_api_key=api_key)
            
    if not chat_model:
        # Fallback if no LLM configured:
        return {"messages": [AIMessage(content="LLM is not configured properly.")], "status": "done"}
        
    chat_model_with_tools = chat_model.bind_tools(tools)
    response = await chat_model_with_tools.ainvoke(messages)
    
    return {
        "messages": [response],
        "status": "streaming" if response.tool_calls else "done"
    }

async def save_session_node(state: AgentState) -> dict[str, Any]:
    """Persist the session title and metadata to Postgres."""
    from app.settings import get_settings
    import asyncpg
    
    dsn = get_settings().postgres_dsn
    session_id = state.get("session_id")
    if not dsn or not session_id:
        return {}
        
    messages = state.get("messages", [])
    if not messages:
        return {}
        
    # Find the first user message for title, or generate one
    title = "New Session"
    for m in messages:
        if isinstance(m, HumanMessage):
            title = str(m.content)[:50] + ("..." if len(str(m.content)) > 50 else "")
            break
            
    try:
        conn = await asyncpg.connect(dsn)
        await conn.execute("""
            INSERT INTO sessions (id, title, message_count)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE 
            SET title = EXCLUDED.title,
                message_count = EXCLUDED.message_count,
                updated_at = CURRENT_TIMESTAMP
        """, session_id, title, len(messages))
        await conn.close()
    except Exception as e:
        logger.error(f"Failed to save session: {e}")
        
    return {}
