"""Migration endpoint: parse old character_profiles text into structured Character entries."""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Character, Story
from schemas import CharacterOut

router = APIRouter(tags=["migration"])


def _parse_character_profiles(text: str, story_id: int) -> list[dict]:
    """Best-effort parse of free-text character profiles into structured entries.

    Supports common patterns like:
      - "【角色名】 description..." (Chinese brackets)
      - "角色名: description..."
      - "角色名 — description..."
      - Numbered lists "1. 角色名 ..."
      - Lines starting with a name (short) followed by longer text

    Returns list of dicts with {name, role, description}.
    """
    entries: list[dict] = []
    lines = text.strip().splitlines()
    if not lines:
        return entries

    # Strategy 1: Try to find 【name】 patterns
    bracket_pattern = re.compile(r'[【\[](.+?)[】\]]')
    current_name = None
    current_lines: list[str] = []

    for line in lines:
        m = bracket_pattern.search(line)
        if m:
            # Save previous
            if current_name:
                entries.append({
                    "name": current_name.strip(),
                    "role": _guess_role(current_name, "\n".join(current_lines)),
                    "description": "\n".join(current_lines).strip(),
                })
            current_name = m.group(1)
            rest = bracket_pattern.sub("", line).strip()
            current_lines = [rest] if rest else []
        elif current_name:
            current_lines.append(line)

    if current_name:
        entries.append({
            "name": current_name.strip(),
            "role": _guess_role(current_name, "\n".join(current_lines)),
            "description": "\n".join(current_lines).strip(),
        })

    if entries:
        return entries

    # Strategy 2: Try "Name: description" or "Name — description"
    colon_pattern = re.compile(r'^(.{1,20})\s*[：:—–\-]\s*(.+)', re.DOTALL)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = colon_pattern.match(line)
        if m:
            name = m.group(1).strip().lstrip("0123456789.、) ")
            desc = m.group(2).strip()
            if name and len(name) <= 20:
                entries.append({
                    "name": name,
                    "role": _guess_role(name, desc),
                    "description": desc,
                })

    if entries:
        return entries

    # Strategy 3: Treat each non-empty line as a character name (last resort)
    for line in lines:
        line = line.strip().lstrip("0123456789.、) ")
        if line and len(line) <= 30:
            entries.append({
                "name": line,
                "role": "supporting",
                "description": "",
            })

    return entries


def _guess_role(name: str, description: str) -> str:
    """Heuristic role assignment based on keywords."""
    text = (name + " " + description).lower()
    if any(kw in text for kw in ("主角", "主人公", "protagonist", "男主", "女主")):
        return "protagonist"
    if any(kw in text for kw in ("反派", "boss", "villain", "敌人", "对手", "antagonist")):
        return "antagonist"
    if any(kw in text for kw in ("路人", "background", "龙套", "配角路人")):
        return "background"
    return "supporting"


@router.post("/api/stories/{story_id}/migrate-characters", response_model=list[CharacterOut])
def migrate_character_profiles(story_id: int, db: Session = Depends(get_db)):
    """Parse story-level character_profiles text and create structured Character entries.

    The old text field is preserved (marked as 'free notes') — no data is lost.
    Only creates new characters if the story doesn't already have structured entries.
    """
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")

    text = (story.character_profiles or "").strip()
    if not text:
        raise HTTPException(400, "No character profiles text to migrate")

    # Check if already migrated
    existing = db.query(Character).filter(Character.story_id == story_id).count()
    if existing > 0:
        raise HTTPException(409, "This story already has structured characters. Delete them first if you want to re-migrate.")

    parsed = _parse_character_profiles(text, story_id)
    if not parsed:
        raise HTTPException(400, "Could not parse any characters from the profile text")

    created: list[Character] = []
    for i, entry in enumerate(parsed):
        char = Character(
            story_id=story_id,
            name=entry["name"],
            role=entry["role"],
            description=entry["description"] or None,
            sort_order=i,
        )
        db.add(char)
        created.append(char)

    db.commit()
    for char in created:
        db.refresh(char)

    return created
