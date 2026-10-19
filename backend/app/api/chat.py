"""SKINSIGHT v2 — Chat API"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import require_user
from app.database import ChatMessage, ChatSession, get_db
from app.services.chatbot import get_bot_response

router = APIRouter()

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None

@router.post("/message")
async def chat(data: ChatRequest, user=Depends(require_user), db: Session = Depends(get_db)):
    if not data.message.strip():
        return JSONResponse({"response": "Please type a message! 😊", "category": "general"})

    session = None
    if data.session_id is not None:
        session = db.query(ChatSession).filter_by(
            id=data.session_id,
            user_id=user["user_id"],
        ).first()
        if session is None:
            raise HTTPException(404, "Chat session not found.")
    else:
        session = ChatSession(user_id=user["user_id"], title=data.message.strip()[:150])
        db.add(session)
        db.flush()

    result = get_bot_response(data.message.strip())
    now = datetime.utcnow()
    db.add(ChatMessage(session_id=session.id, sender="user", content=data.message.strip(), created_at=now))
    db.add(ChatMessage(session_id=session.id, sender="assistant", content=result["response"], created_at=now))
    session.updated_at = now
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Could not save the chat. Please try again.") from exc

    result["session_id"] = session.id
    return JSONResponse(result)


@router.get("/sessions")
async def list_sessions(user=Depends(require_user), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter_by(user_id=user["user_id"])
    sessions = sessions.order_by(ChatSession.updated_at.desc()).limit(50).all()
    return {"sessions": [{
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    } for session in sessions]}


@router.get("/sessions/{session_id}")
async def get_session(session_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    session = db.query(ChatSession).options(selectinload(ChatSession.messages)).filter_by(
        id=session_id,
        user_id=user["user_id"],
    ).first()
    if session is None:
        raise HTTPException(404, "Chat session not found.")
    return {"session_id": session.id, "messages": [{
        "id": message.id,
        "sender": message.sender,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    } for message in session.messages]}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter_by(
        id=session_id,
        user_id=user["user_id"],
    ).first()
    if session is None:
        raise HTTPException(404, "Chat session not found.")

    db.delete(session)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Could not delete the chat session. Please try again.") from exc

    return {"message": "Chat session deleted.", "session_id": session_id}
