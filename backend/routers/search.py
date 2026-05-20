"""Phase 4: Cross-chapter search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import Chapter, ChatMessage, MangaImage, Story

router = APIRouter(tags=["search"])


@router.get("/api/stories/{story_id}/search")
def search_story(
    story_id: int,
    q: str = "",
    db: Session = Depends(get_db),
):
    """Full-text search across all chapters of a story.

    Searches:
    - chapter titles
    - novel_content
    - chat messages
    - scenes_text
    - manga image prompts

    Returns list of hits grouped by chapter.
    """
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")

    q = q.strip()
    if not q:
        return {"results": [], "query": q, "total": 0}

    q_lower = q.lower()

    hits: list[dict] = []

    for chapter in sorted(story.chapters, key=lambda c: c.chapter_number):
        chapter_hits: list[dict] = []

        # Search title
        if chapter.title and q_lower in chapter.title.lower():
            chapter_hits.append({
                "type": "title",
                "snippet": chapter.title,
                "context": None,
            })

        # Search novel content
        if chapter.novel_content:
            idx = chapter.novel_content.lower().find(q_lower)
            if idx >= 0:
                start = max(0, idx - 60)
                end = min(len(chapter.novel_content), idx + len(q) + 60)
                snippet = chapter.novel_content[start:end]
                if start > 0:
                    snippet = "…" + snippet
                if end < len(chapter.novel_content):
                    snippet = snippet + "…"
                chapter_hits.append({
                    "type": "novel_content",
                    "snippet": snippet,
                    "context": None,
                })

        # Search chat messages
        for msg in chapter.messages:
            if q_lower in msg.content.lower():
                idx = msg.content.lower().find(q_lower)
                start = max(0, idx - 40)
                end = min(len(msg.content), idx + len(q) + 40)
                snippet = msg.content[start:end]
                if start > 0:
                    snippet = "…" + snippet
                if end < len(msg.content):
                    snippet = snippet + "…"
                chapter_hits.append({
                    "type": "chat_message",
                    "snippet": snippet,
                    "context": msg.role,
                })
                break  # One hit per chapter is enough for chat

        # Search scenes_text
        if chapter.scenes_text and q_lower in chapter.scenes_text.lower():
            idx = chapter.scenes_text.lower().find(q_lower)
            start = max(0, idx - 40)
            end = min(len(chapter.scenes_text), idx + len(q) + 40)
            snippet = chapter.scenes_text[start:end]
            if start > 0:
                snippet = "…" + snippet
            if end < len(chapter.scenes_text):
                snippet = snippet + "…"
            chapter_hits.append({
                "type": "scenes",
                "snippet": snippet,
                "context": None,
            })

        # Search image prompts
        for img in chapter.images:
            if img.prompt and q_lower in (img.prompt or "").lower():
                chapter_hits.append({
                    "type": "image_prompt",
                    "snippet": img.prompt[:120],
                    "context": f"第{img.image_number}格",
                })
                break

        if chapter_hits:
            hits.append({
                "chapter_id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title or "",
                "hits": chapter_hits,
            })

    return {
        "results": hits,
        "query": q,
        "total": sum(len(h["hits"]) for h in hits),
    }
