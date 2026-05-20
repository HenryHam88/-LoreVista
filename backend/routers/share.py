"""Phase 4: Public read-only share links for stories."""

from __future__ import annotations

import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Story, StoryShareToken
from schemas import ChapterOut, ShareTokenOut, StoryOut

router = APIRouter(tags=["share"])


def _require_story(story_id: int, db: Session) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    return story


@router.post("/api/stories/{story_id}/share-token", response_model=ShareTokenOut)
def create_share_token(story_id: int, db: Session = Depends(get_db)):
    """Create (or return existing) a read-only share token for a story."""
    story = _require_story(story_id, db)
    # Return existing non-expired token if available
    existing = (
        db.query(StoryShareToken)
        .filter(StoryShareToken.story_id == story_id)
        .order_by(StoryShareToken.created_at.desc())
        .first()
    )
    if existing:
        return existing

    token_str = secrets.token_urlsafe(32)
    token = StoryShareToken(story_id=story_id, token=token_str)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@router.delete("/api/stories/{story_id}/share-token")
def revoke_share_token(story_id: int, db: Session = Depends(get_db)):
    """Revoke all share tokens for a story."""
    _require_story(story_id, db)
    db.query(StoryShareToken).filter(StoryShareToken.story_id == story_id).delete()
    db.commit()
    return {"ok": True}


@router.get("/api/share/{token}/story", response_model=StoryOut)
def get_shared_story(token: str, db: Session = Depends(get_db)):
    """Public read-only endpoint: get story info by share token."""
    token_row = db.query(StoryShareToken).filter(StoryShareToken.token == token).first()
    if not token_row:
        raise HTTPException(404, "Share link not found or expired")
    if token_row.expires_at and token_row.expires_at < datetime.datetime.utcnow():
        raise HTTPException(410, "Share link has expired")
    return token_row.story


@router.get("/api/share/{token}/chapters", response_model=list[ChapterOut])
def get_shared_chapters(token: str, db: Session = Depends(get_db)):
    """Public read-only endpoint: list chapters for a shared story."""
    token_row = db.query(StoryShareToken).filter(StoryShareToken.token == token).first()
    if not token_row:
        raise HTTPException(404, "Share link not found or expired")
    if token_row.expires_at and token_row.expires_at < datetime.datetime.utcnow():
        raise HTTPException(410, "Share link has expired")
    story = token_row.story
    return sorted(story.chapters, key=lambda c: c.chapter_number)
