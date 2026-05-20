"""CRUD API for Pages and Panels (Phase 1 structured storyboard)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Chapter, Page, Panel
from schemas import (
    PageCreate,
    PageOut,
    PageUpdate,
    PanelCreate,
    PanelOut,
    PanelUpdate,
)

router = APIRouter(prefix="/api/chapters/{chapter_id}/pages", tags=["pages"])


def _require_chapter(chapter_id: int, db: Session) -> Chapter:
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    return chapter


def _require_page(page_id: int, chapter_id: int, db: Session) -> Page:
    page = db.get(Page, page_id)
    if not page or page.chapter_id != chapter_id:
        raise HTTPException(404, "Page not found")
    return page


# ─── Page CRUD ──────────────────────────────────────────────


@router.get("", response_model=list[PageOut])
def list_pages(chapter_id: int, db: Session = Depends(get_db)):
    _require_chapter(chapter_id, db)
    return (
        db.query(Page)
        .filter(Page.chapter_id == chapter_id)
        .order_by(Page.page_number)
        .all()
    )


@router.post("", response_model=PageOut, status_code=201)
def create_page(chapter_id: int, body: PageCreate, db: Session = Depends(get_db)):
    _require_chapter(chapter_id, db)
    page = Page(
        chapter_id=chapter_id,
        page_number=body.page_number,
        layout_hint=body.layout_hint,
    )
    db.add(page)
    db.flush()
    # Create panels if provided
    for panel_data in body.panels:
        panel = Panel(
            page_id=page.id,
            panel_number=panel_data.panel_number,
            description=panel_data.description,
            dialogue=panel_data.dialogue,
            character_ids=panel_data.character_ids,
            outfit_ids=panel_data.outfit_ids,
            location_id=panel_data.location_id,
            camera_angle=panel_data.camera_angle,
        )
        db.add(panel)
    db.commit()
    db.refresh(page)
    return page


@router.get("/{page_id}", response_model=PageOut)
def get_page(chapter_id: int, page_id: int, db: Session = Depends(get_db)):
    return _require_page(page_id, chapter_id, db)


@router.put("/{page_id}", response_model=PageOut)
def update_page(chapter_id: int, page_id: int, body: PageUpdate, db: Session = Depends(get_db)):
    page = _require_page(page_id, chapter_id, db)
    if body.page_number is not None:
        page.page_number = body.page_number
    if body.layout_hint is not None:
        page.layout_hint = body.layout_hint
    db.commit()
    db.refresh(page)
    return page


@router.delete("/{page_id}")
def delete_page(chapter_id: int, page_id: int, db: Session = Depends(get_db)):
    page = _require_page(page_id, chapter_id, db)
    db.delete(page)
    db.commit()
    return {"ok": True}


# ─── Panel CRUD ─────────────────────────────────────────────


@router.get("/{page_id}/panels", response_model=list[PanelOut])
def list_panels(chapter_id: int, page_id: int, db: Session = Depends(get_db)):
    _require_page(page_id, chapter_id, db)
    return (
        db.query(Panel)
        .filter(Panel.page_id == page_id)
        .order_by(Panel.panel_number)
        .all()
    )


@router.post("/{page_id}/panels", response_model=PanelOut, status_code=201)
def create_panel(chapter_id: int, page_id: int, body: PanelCreate, db: Session = Depends(get_db)):
    _require_page(page_id, chapter_id, db)
    panel = Panel(
        page_id=page_id,
        panel_number=body.panel_number,
        description=body.description,
        dialogue=body.dialogue,
        character_ids=body.character_ids,
        outfit_ids=body.outfit_ids,
        location_id=body.location_id,
        camera_angle=body.camera_angle,
    )
    db.add(panel)
    db.commit()
    db.refresh(panel)
    return panel


@router.put("/{page_id}/panels/{panel_id}", response_model=PanelOut)
def update_panel(chapter_id: int, page_id: int, panel_id: int, body: PanelUpdate, db: Session = Depends(get_db)):
    _require_page(page_id, chapter_id, db)
    panel = db.get(Panel, panel_id)
    if not panel or panel.page_id != page_id:
        raise HTTPException(404, "Panel not found")
    if body.panel_number is not None:
        panel.panel_number = body.panel_number
    if body.description is not None:
        panel.description = body.description
    if body.dialogue is not None:
        panel.dialogue = body.dialogue
    if body.character_ids is not None:
        panel.character_ids = body.character_ids
    if body.outfit_ids is not None:
        panel.outfit_ids = body.outfit_ids
    if body.location_id is not None:
        panel.location_id = body.location_id
    if body.camera_angle is not None:
        panel.camera_angle = body.camera_angle
    db.commit()
    db.refresh(panel)
    return panel


@router.delete("/{page_id}/panels/{panel_id}")
def delete_panel(chapter_id: int, page_id: int, panel_id: int, db: Session = Depends(get_db)):
    _require_page(page_id, chapter_id, db)
    panel = db.get(Panel, panel_id)
    if not panel or panel.page_id != page_id:
        raise HTTPException(404, "Panel not found")
    db.delete(panel)
    db.commit()
    return {"ok": True}
