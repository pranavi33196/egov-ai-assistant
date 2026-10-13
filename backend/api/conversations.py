from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from database.base import get_db
from database.models import User, Conversation, Message
from auth.dependencies import get_current_user

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    language: Optional[str] = "en"


class RenameConversationRequest(BaseModel):
    title: str


@router.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).order_by(Conversation.created_at.desc()).all()

    return [
        {
            "id": c.id, "title": c.title, "language": c.language,
            "current_service": c.current_service,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in convs
    ]


@router.post("/conversations")
def create_conversation(req: CreateConversationRequest, current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    conv = Conversation(user_id=current_user.id, title=req.title, language=req.language)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "title": conv.title, "language": conv.language}


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return [
        {
            "id": m.id, "role": m.role, "content": m.content,
            "language": m.language,
            "sources": json.loads(m.source_references) if m.source_references else [],
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]


@router.put("/conversations/{conversation_id}/rename")
def rename_conversation(conversation_id: int, req: RenameConversationRequest,
                        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
    conv.title = req.title
    db.commit()
    return {"message": "Renamed."}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
    conv.is_deleted = True
    db.commit()
    return {"message": "Conversation deleted."}
