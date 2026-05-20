"""CRUD API for Locations (Phase 1 Asset Library)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Location, Story
from schemas import LocationCreate, LocationOut, LocationUpdate

router = APIRouter(prefix="/api/stories/{story_id}/locations", tags=["locations"])


def _require_story(story_id: int, db: Session) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    return story


def _require_location(location_id: int, story_id: int, db: Session) -> Location:
    loc = db.get(Location, location_id)
    if not loc or loc.story_id != story_id:
        raise HTTPException(404, "Location not found")
    return loc


@router.get("", response_model=list[LocationOut])
def list_locations(story_id: int, db: Session = Depends(get_db)):
    _require_story(story_id, db)
    return (
        db.query(Location)
        .filter(Location.story_id == story_id)
        .order_by(Location.sort_order, Location.id)
        .all()
    )


@router.post("", response_model=LocationOut, status_code=201)
def create_location(story_id: int, body: LocationCreate, db: Session = Depends(get_db)):
    _require_story(story_id, db)
    # Validate parent_id if provided
    if body.parent_id is not None:
        parent = db.get(Location, body.parent_id)
        if not parent or parent.story_id != story_id:
            raise HTTPException(400, "Parent location not found in this story")
    loc = Location(
        story_id=story_id,
        parent_id=body.parent_id,
        name=body.name,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@router.get("/{location_id}", response_model=LocationOut)
def get_location(story_id: int, location_id: int, db: Session = Depends(get_db)):
    return _require_location(location_id, story_id, db)


@router.put("/{location_id}", response_model=LocationOut)
def update_location(story_id: int, location_id: int, body: LocationUpdate, db: Session = Depends(get_db)):
    loc = _require_location(location_id, story_id, db)
    if body.name is not None:
        loc.name = body.name
    if body.parent_id is not None:
        if body.parent_id == loc.id:
            raise HTTPException(400, "Location cannot be its own parent")
        parent = db.get(Location, body.parent_id)
        if not parent or parent.story_id != story_id:
            raise HTTPException(400, "Parent location not found in this story")
        loc.parent_id = body.parent_id
    elif body.parent_id is None and "parent_id" in (body.model_fields_set or set()):
        loc.parent_id = None
    if body.description is not None:
        loc.description = body.description
    if body.sort_order is not None:
        loc.sort_order = body.sort_order
    db.commit()
    db.refresh(loc)
    return loc


@router.delete("/{location_id}")
def delete_location(story_id: int, location_id: int, db: Session = Depends(get_db)):
    loc = _require_location(location_id, story_id, db)
    db.delete(loc)
    db.commit()
    return {"ok": True}
