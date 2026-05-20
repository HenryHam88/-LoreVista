"""Phase 4: N-pick image generation — generate N candidates, user picks one."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Chapter, ImageCandidate, MangaImage
from schemas import ImageCandidateOut

logger = logging.getLogger("npick")

router = APIRouter(tags=["npick"])

MANGA_DIR = Path(__file__).resolve().parent.parent / "manga_outputs"

N_CANDIDATES_DEFAULT = 4
N_CANDIDATES_MAX = 4


@router.post(
    "/api/chapters/{chapter_id}/npick/{image_number}",
    response_model=list[ImageCandidateOut],
)
async def generate_npick_candidates(
    chapter_id: int,
    image_number: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Generate N candidate images for a given panel slot.

    The existing confirmed image (if any) is not overwritten until the user
    calls the /confirm endpoint. Candidates are stored in the image_candidates
    table for the client to display.
    """
    from services.image2 import generate_image_candidates
    from routers.extract import resolve_panel_refs
    from models import Page, Panel

    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    # Load scenes
    from main import _load_chapter_scenes, _load_characters, _load_color_mode, _effective_ref_image_paths
    scenes = _load_chapter_scenes(chapter)
    if not scenes or image_number < 1 or image_number > len(scenes):
        raise HTTPException(400, f"image_number {image_number} out of range")

    prompt = scenes[image_number - 1]
    api_key = request.headers.get("x-image-api-key") or None

    art_style: str | None = chapter.art_style
    aspect_ratio: str | None = chapter.aspect_ratio

    # Resolve ref images
    ref_imgs = _effective_ref_image_paths(chapter_id, db)
    panels_for_num = (
        db.query(Panel)
        .join(Page)
        .filter(Page.chapter_id == chapter_id)
        .order_by(Page.page_number, Panel.panel_number)
        .all()
    )
    if len(panels_for_num) >= image_number:
        panel_refs = resolve_panel_refs(panels_for_num[image_number - 1], db, MANGA_DIR)
        if panel_refs:
            ref_imgs = panel_refs

    # Delete old candidates for this slot
    db.query(ImageCandidate).filter(
        ImageCandidate.chapter_id == chapter_id,
        ImageCandidate.image_number == image_number,
    ).delete()
    db.flush()

    try:
        paths = await generate_image_candidates(
            prompt=prompt,
            chapter_id=chapter_id,
            image_number=image_number,
            n=N_CANDIDATES_DEFAULT,
            all_scenes=scenes,
            character_profiles=_load_characters(chapter_id, db),
            ref_image_paths=[str(p) for p in ref_imgs] if ref_imgs else None,
            color_mode=_load_color_mode(chapter_id, db),
            api_key=api_key,
            art_style=art_style,
            aspect_ratio=aspect_ratio,
        )
    except Exception as exc:
        raise HTTPException(502, f"候选图生成失败: {exc}")

    candidates: list[ImageCandidate] = []
    for path in paths:
        cand = ImageCandidate(
            chapter_id=chapter_id,
            image_number=image_number,
            image_path=path,
            prompt=prompt,
            is_selected=False,
        )
        db.add(cand)
        candidates.append(cand)

    db.commit()
    for c in candidates:
        db.refresh(c)

    return candidates


@router.get(
    "/api/chapters/{chapter_id}/npick/{image_number}",
    response_model=list[ImageCandidateOut],
)
def list_npick_candidates(
    chapter_id: int,
    image_number: int,
    db: Session = Depends(get_db),
):
    """List pending candidates for a panel slot."""
    return (
        db.query(ImageCandidate)
        .filter(
            ImageCandidate.chapter_id == chapter_id,
            ImageCandidate.image_number == image_number,
        )
        .order_by(ImageCandidate.id)
        .all()
    )


@router.post(
    "/api/chapters/{chapter_id}/npick/{image_number}/confirm/{candidate_id}",
)
def confirm_npick_candidate(
    chapter_id: int,
    image_number: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    """Confirm one candidate as the panel image, discard others."""
    cand = db.get(ImageCandidate, candidate_id)
    if not cand or cand.chapter_id != chapter_id or cand.image_number != image_number:
        raise HTTPException(404, "Candidate not found")

    # Update or create the MangaImage record for this slot
    existing = (
        db.query(MangaImage)
        .filter(
            MangaImage.chapter_id == chapter_id,
            MangaImage.image_number == image_number,
        )
        .first()
    )
    if existing:
        # Delete the old image file
        old_path = Path(__file__).resolve().parent.parent / existing.image_path
        if old_path.exists() and str(old_path) != str(Path(__file__).resolve().parent.parent / cand.image_path):
            try:
                old_path.unlink()
            except OSError:
                pass
        existing.image_path = cand.image_path
        existing.prompt = cand.prompt
    else:
        manga = MangaImage(
            chapter_id=chapter_id,
            image_number=image_number,
            image_path=cand.image_path,
            prompt=cand.prompt,
        )
        db.add(manga)

    # Delete all candidates for this slot (keep selected file, delete others)
    all_cands = (
        db.query(ImageCandidate)
        .filter(
            ImageCandidate.chapter_id == chapter_id,
            ImageCandidate.image_number == image_number,
        )
        .all()
    )
    for c in all_cands:
        if c.id != candidate_id:
            p = Path(__file__).resolve().parent.parent / c.image_path
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        db.delete(c)

    db.commit()
    return {
        "ok": True,
        "image_number": image_number,
        "image_path": cand.image_path,
        "prompt": cand.prompt,
    }
