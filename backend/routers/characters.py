"""CRUD API for Characters and Outfits (Phase 1 Asset Library)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Character, Outfit, Story
from schemas import (
    CharacterCreate,
    CharacterOut,
    CharacterUpdate,
    OutfitCreate,
    OutfitOut,
    OutfitUpdate,
)

router = APIRouter(prefix="/api/stories/{story_id}/characters-library", tags=["characters"])


def _require_story(story_id: int, db: Session) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    return story


def _require_character(character_id: int, story_id: int, db: Session) -> Character:
    char = db.get(Character, character_id)
    if not char or char.story_id != story_id:
        raise HTTPException(404, "Character not found")
    return char


# ─── Character CRUD ─────────────────────────────────────────


@router.get("", response_model=list[CharacterOut])
def list_characters(story_id: int, db: Session = Depends(get_db)):
    _require_story(story_id, db)
    return (
        db.query(Character)
        .filter(Character.story_id == story_id)
        .order_by(Character.sort_order, Character.id)
        .all()
    )


@router.post("", response_model=CharacterOut, status_code=201)
def create_character(story_id: int, body: CharacterCreate, db: Session = Depends(get_db)):
    _require_story(story_id, db)
    char = Character(
        story_id=story_id,
        name=body.name,
        role=body.role,
        aliases=body.aliases,
        core_appearance=body.core_appearance,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(char)
    db.commit()
    db.refresh(char)
    return char


@router.get("/{character_id}", response_model=CharacterOut)
def get_character(story_id: int, character_id: int, db: Session = Depends(get_db)):
    return _require_character(character_id, story_id, db)


@router.put("/{character_id}", response_model=CharacterOut)
def update_character(story_id: int, character_id: int, body: CharacterUpdate, db: Session = Depends(get_db)):
    char = _require_character(character_id, story_id, db)
    if body.name is not None:
        char.name = body.name
    if body.role is not None:
        if body.role not in ("protagonist", "supporting", "antagonist", "background"):
            raise HTTPException(400, "Invalid role. Must be protagonist/supporting/antagonist/background")
        char.role = body.role
    if body.aliases is not None:
        char.aliases = body.aliases
    if body.core_appearance is not None:
        char.core_appearance = body.core_appearance
    if body.description is not None:
        char.description = body.description
    if body.sort_order is not None:
        char.sort_order = body.sort_order
    db.commit()
    db.refresh(char)
    return char


@router.delete("/{character_id}")
def delete_character(story_id: int, character_id: int, db: Session = Depends(get_db)):
    char = _require_character(character_id, story_id, db)
    db.delete(char)
    db.commit()
    return {"ok": True}


# ─── Outfit CRUD ────────────────────────────────────────────


@router.get("/{character_id}/outfits", response_model=list[OutfitOut])
def list_outfits(story_id: int, character_id: int, db: Session = Depends(get_db)):
    _require_character(character_id, story_id, db)
    return (
        db.query(Outfit)
        .filter(Outfit.character_id == character_id)
        .order_by(Outfit.sort_order, Outfit.id)
        .all()
    )


@router.post("/{character_id}/outfits", response_model=OutfitOut, status_code=201)
def create_outfit(story_id: int, character_id: int, body: OutfitCreate, db: Session = Depends(get_db)):
    _require_character(character_id, story_id, db)
    outfit = Outfit(
        character_id=character_id,
        label=body.label,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    return outfit


@router.put("/{character_id}/outfits/{outfit_id}", response_model=OutfitOut)
def update_outfit(story_id: int, character_id: int, outfit_id: int, body: OutfitUpdate, db: Session = Depends(get_db)):
    _require_character(character_id, story_id, db)
    outfit = db.get(Outfit, outfit_id)
    if not outfit or outfit.character_id != character_id:
        raise HTTPException(404, "Outfit not found")
    if body.label is not None:
        outfit.label = body.label
    if body.description is not None:
        outfit.description = body.description
    if body.sort_order is not None:
        outfit.sort_order = body.sort_order
    db.commit()
    db.refresh(outfit)
    return outfit


@router.delete("/{character_id}/outfits/{outfit_id}")
def delete_outfit(story_id: int, character_id: int, outfit_id: int, db: Session = Depends(get_db)):
    _require_character(character_id, story_id, db)
    outfit = db.get(Outfit, outfit_id)
    if not outfit or outfit.character_id != character_id:
        raise HTTPException(404, "Outfit not found")
    db.delete(outfit)
    db.commit()
    return {"ok": True}
