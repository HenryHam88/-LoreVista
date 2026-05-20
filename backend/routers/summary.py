"""Phase 3: Chapter Summary + CharacterAppearanceEvent endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Chapter, CharacterAppearanceEvent, Character, Story
from schemas import AppearanceEventCreate, AppearanceEventOut, AppearanceEventUpdate

router = APIRouter(tags=["summary"])


# ─── Chapter Summary ─────────────────────────────────────────


@router.post("/api/chapters/{chapter_id}/generate-summary")
async def generate_chapter_summary_endpoint(
    chapter_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Generate (or regenerate) AI summary for a chapter.

    The summary is saved to chapter.summary and returned.
    It is automatically injected as 「前情提要」when generating the NEXT chapter's content.
    """
    from services.deepseek import generate_chapter_summary

    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    if not chapter.novel_content and not chapter.messages:
        raise HTTPException(400, "本话还没有内容，无法生成摘要")

    content = chapter.novel_content or (
        "\n".join(m.content for m in chapter.messages if m.role == "assistant")
    )
    if not content.strip():
        raise HTTPException(400, "本话还没有小说内容")

    api_key = request.headers.get("x-deepseek-api-key") or None
    summary = await generate_chapter_summary(content, chapter.chapter_number, api_key)
    chapter.summary = summary
    db.commit()
    return {"chapter_id": chapter_id, "chapter_number": chapter.chapter_number, "summary": summary}


@router.get("/api/chapters/{chapter_id}/summary")
def get_chapter_summary(chapter_id: int, db: Session = Depends(get_db)):
    """Get the current summary for a chapter."""
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    return {"chapter_id": chapter_id, "summary": chapter.summary or ""}


@router.put("/api/chapters/{chapter_id}/summary")
async def update_chapter_summary(
    chapter_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Manually update the summary for a chapter."""
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    body = await request.json()
    summary = (body.get("summary") or "").strip()
    chapter.summary = summary or None
    db.commit()
    return {"ok": True, "summary": chapter.summary or ""}


@router.get("/api/stories/{story_id}/summaries")
def list_story_summaries(story_id: int, db: Session = Depends(get_db)):
    """Return summaries for all chapters of a story (for recap injection context)."""
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    result = []
    for chapter in story.chapters:
        result.append({
            "chapter_id": chapter.id,
            "chapter_number": chapter.chapter_number,
            "title": chapter.title,
            "summary": chapter.summary or "",
        })
    return result


# ─── CharacterAppearanceEvent CRUD ───────────────────────────


def _require_character(character_id: int, story_id: int, db: Session) -> Character:
    char = db.get(Character, character_id)
    if not char or char.story_id != story_id:
        raise HTTPException(404, "Character not found")
    return char


@router.get(
    "/api/stories/{story_id}/characters-library/{character_id}/appearance-events",
    response_model=list[AppearanceEventOut],
)
def list_appearance_events(
    story_id: int,
    character_id: int,
    db: Session = Depends(get_db),
):
    """List all appearance change events for a character, sorted by chapter_number."""
    char = _require_character(character_id, story_id, db)
    return sorted(char.appearance_events, key=lambda e: e.chapter_number)


@router.post(
    "/api/stories/{story_id}/characters-library/{character_id}/appearance-events",
    response_model=AppearanceEventOut,
    status_code=201,
)
def create_appearance_event(
    story_id: int,
    character_id: int,
    body: AppearanceEventCreate,
    db: Session = Depends(get_db),
):
    """Add a new appearance change event for a character."""
    char = _require_character(character_id, story_id, db)
    event = CharacterAppearanceEvent(
        character_id=char.id,
        chapter_number=body.chapter_number,
        description=body.description,
        event_note=body.event_note,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.put(
    "/api/stories/{story_id}/characters-library/{character_id}/appearance-events/{event_id}",
    response_model=AppearanceEventOut,
)
def update_appearance_event(
    story_id: int,
    character_id: int,
    event_id: int,
    body: AppearanceEventUpdate,
    db: Session = Depends(get_db),
):
    _require_character(character_id, story_id, db)
    event = db.get(CharacterAppearanceEvent, event_id)
    if not event or event.character_id != character_id:
        raise HTTPException(404, "Appearance event not found")
    if body.chapter_number is not None:
        event.chapter_number = body.chapter_number
    if body.description is not None:
        event.description = body.description
    if body.event_note is not None:
        event.event_note = body.event_note
    db.commit()
    db.refresh(event)
    return event


@router.delete(
    "/api/stories/{story_id}/characters-library/{character_id}/appearance-events/{event_id}",
)
def delete_appearance_event(
    story_id: int,
    character_id: int,
    event_id: int,
    db: Session = Depends(get_db),
):
    _require_character(character_id, story_id, db)
    event = db.get(CharacterAppearanceEvent, event_id)
    if not event or event.character_id != character_id:
        raise HTTPException(404, "Appearance event not found")
    db.delete(event)
    db.commit()
    return {"ok": True}


def get_character_appearance_at_chapter(
    character: Character,
    chapter_number: int,
) -> str:
    """Return the most up-to-date appearance description for a character at a given chapter.

    Checks appearance_events for any event with chapter_number <= the given chapter,
    returning the most recent one. Falls back to character.description.
    """
    relevant = [
        e for e in (character.appearance_events or [])
        if e.chapter_number <= chapter_number
    ]
    if relevant:
        latest = max(relevant, key=lambda e: e.chapter_number)
        return latest.description
    return character.description or ""
