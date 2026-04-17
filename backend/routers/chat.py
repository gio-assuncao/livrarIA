from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import ChatRequest, ChatResponse
from services.agent import agent_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Send a conversation to the LLM agent and receive a reply."""
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    reply, tools_invoked = await agent_service.run(messages, db)
    return ChatResponse(reply=reply, tool_calls_made=tools_invoked)
