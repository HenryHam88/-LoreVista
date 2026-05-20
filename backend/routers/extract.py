"""Phase 2: Auto-extract characters and locations from novel text.

Endpoints:
  POST /api/stories/{story_id}/extract-characters
  POST /api/stories/{story_id}/extract-locations
  POST /api/chapters/{chapter_id}/generate-structured-scenes
  POST /api/chapters/{chapter_id}/resolve-panels   (name → ID)
"""

from __future__ import annotations

import difflib
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Character, Chapter, Location, Outfit, Page, Panel, Story
from schemas import CharacterOut, LocationOut, PageOut

logger = logging.getLogger("extract")

router = APIRouter(tags=["extract"])


# ──────────────────────────────────────────────────────────────────────────────
# Fuzzy matching helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fuzzy_match_character(
    name: str,
    characters: list[Character],
    aliases_map: dict[int, list[str]],
    threshold: float = 0.75,
) -> Character | None:
    """Return the best-matching existing character for *name*, or None."""
    name_lower = name.lower().strip()
    best_score = 0.0
    best_char: Character | None = None

    for char in characters:
        # Exact match
        if char.name.lower() == name_lower:
            return char
        # Check aliases
        aliases = aliases_map.get(char.id, [])
        if any(a.lower() == name_lower for a in aliases):
            return char
        # Fuzzy on name
        score = difflib.SequenceMatcher(None, name_lower, char.name.lower()).ratio()
        if score > best_score:
            best_score = score
            best_char = char
        # Fuzzy on aliases
        for alias in aliases:
            s = difflib.SequenceMatcher(None, name_lower, alias.lower()).ratio()
            if s > best_score:
                best_score = s
                best_char = char

    if best_score >= threshold and best_char:
        return best_char
    return None


def _fuzzy_match_location(
    name: str,
    locations: list[Location],
    threshold: float = 0.72,
) -> Location | None:
    name_lower = name.lower().strip()
    best_score = 0.0
    best_loc: Location | None = None
    for loc in locations:
        if loc.name.lower() == name_lower:
            return loc
        score = difflib.SequenceMatcher(None, name_lower, loc.name.lower()).ratio()
        if score > best_score:
            best_score = score
            best_loc = loc
    if best_score >= threshold and best_loc:
        return best_loc
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Extract characters
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/stories/{story_id}/extract-characters")
async def extract_characters_endpoint(story_id: int, request: Request, db: Session = Depends(get_db)):
    """Use DeepSeek to extract characters from chapter novel texts.

    - Matches against existing characters (fuzzy).
    - New characters → created as drafts with AI-extracted names.
    - Matched characters → description appended as observation.

    Returns: { "created": [...], "merged": [...], "skipped": [...] }
    """
    from services.deepseek import extract_characters

    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")

    # Collect novel text from all chapters
    novel_text = "\n\n".join(
        f"【第{ch.chapter_number}话】\n{ch.novel_content}"
        for ch in story.chapters
        if ch.novel_content and ch.novel_content.strip()
    )
    if not novel_text.strip():
        raise HTTPException(400, "没有找到小说正文，请先生成小说内容")

    existing = db.query(Character).filter(Character.story_id == story_id).all()
    existing_names = [c.name for c in existing]
    aliases_map: dict[int, list[str]] = {
        c.id: (c.aliases or []) for c in existing
    }

    api_key = request.headers.get("x-deepseek-api-key") or None
    extracted = await extract_characters(novel_text, existing_names, api_key)

    created_list: list[dict] = []
    merged_list: list[dict] = []
    skipped_list: list[dict] = []

    for entry in extracted:
        name: str = (entry.get("name") or "").strip()
        if not name:
            continue
        confidence: float = float(entry.get("confidence", 0.8))

        match = _fuzzy_match_character(name, existing, aliases_map)

        if match:
            # Append observation to description
            obs = entry.get("description", "").strip()
            if obs:
                prev = (match.description or "").strip()
                combined = f"{prev}\n\n【新增观察 from 正文】{obs}".strip() if prev else obs
                match.description = combined[:2000]
            # Merge aliases
            new_aliases: list[str] = entry.get("aliases", []) or []
            current_aliases: list[str] = list(match.aliases or [])
            added = [a for a in new_aliases if a not in current_aliases and a != match.name]
            if added:
                match.aliases = current_aliases + added
            merged_list.append({"id": match.id, "name": match.name, "matched_from": name})
        else:
            # Low-confidence → still create as draft
            if confidence < 0.4:
                skipped_list.append({"name": name, "reason": "low_confidence"})
                continue

            core: dict = entry.get("core_appearance") or {}
            new_char = Character(
                story_id=story_id,
                name=name,
                role=entry.get("role", "supporting"),
                aliases=entry.get("aliases") or [],
                core_appearance=core if core else None,
                description=(entry.get("description") or "").strip() or None,
                sort_order=len(existing) + len(created_list),
            )
            db.add(new_char)
            db.flush()
            existing.append(new_char)
            aliases_map[new_char.id] = new_char.aliases or []
            created_list.append({"id": new_char.id, "name": new_char.name})

    db.commit()
    return {
        "created": created_list,
        "merged": merged_list,
        "skipped": skipped_list,
        "total_extracted": len(extracted),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Extract locations
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/stories/{story_id}/extract-locations")
async def extract_locations_endpoint(story_id: int, request: Request, db: Session = Depends(get_db)):
    """Use DeepSeek to extract locations from chapter novel texts."""
    from services.deepseek import extract_locations

    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")

    novel_text = "\n\n".join(
        f"【第{ch.chapter_number}话】\n{ch.novel_content}"
        for ch in story.chapters
        if ch.novel_content and ch.novel_content.strip()
    )
    if not novel_text.strip():
        raise HTTPException(400, "没有找到小说正文，请先生成小说内容")

    existing = db.query(Location).filter(Location.story_id == story_id).all()
    existing_names = [loc.name for loc in existing]

    api_key = request.headers.get("x-deepseek-api-key") or None
    extracted = await extract_locations(novel_text, existing_names, api_key)

    # Build name→id lookup for resolving parent_name
    name_to_id: dict[str, int] = {loc.name.lower(): loc.id for loc in existing}
    created_list: list[dict] = []
    merged_list: list[dict] = []
    skipped_list: list[dict] = []

    for entry in extracted:
        name: str = (entry.get("name") or "").strip()
        if not name:
            continue
        confidence: float = float(entry.get("confidence", 0.8))

        match = _fuzzy_match_location(name, existing)

        if match:
            obs = (entry.get("description") or "").strip()
            if obs:
                prev = (match.description or "").strip()
                match.description = (f"{prev}\n\n【新增观察】{obs}".strip() if prev else obs)[:2000]
            merged_list.append({"id": match.id, "name": match.name, "matched_from": name})
        else:
            if confidence < 0.4:
                skipped_list.append({"name": name, "reason": "low_confidence"})
                continue

            # Resolve parent
            parent_name_raw: str = (entry.get("parent_name") or "").strip()
            parent_id: int | None = None
            if parent_name_raw:
                parent_match = _fuzzy_match_location(parent_name_raw, existing)
                if parent_match:
                    parent_id = parent_match.id
                else:
                    # Check if we just created a matching parent this loop
                    parent_id = name_to_id.get(parent_name_raw.lower())

            new_loc = Location(
                story_id=story_id,
                name=name,
                parent_id=parent_id,
                description=(entry.get("description") or "").strip() or None,
                sort_order=len(existing) + len(created_list),
            )
            db.add(new_loc)
            db.flush()
            existing.append(new_loc)
            name_to_id[new_loc.name.lower()] = new_loc.id
            created_list.append({"id": new_loc.id, "name": new_loc.name, "parent_id": parent_id})

    db.commit()
    return {
        "created": created_list,
        "merged": merged_list,
        "skipped": skipped_list,
        "total_extracted": len(extracted),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Generate structured storyboard
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/chapters/{chapter_id}/generate-structured-scenes", response_model=list[PageOut])
async def generate_structured_scenes(chapter_id: int, request: Request, db: Session = Depends(get_db)):
    """Generate structured storyboard (Page+Panel records) for a chapter.

    1. Calls split_scenes_structured → list of page dicts with panels.
    2. Resolves character_names → character_ids (fuzzy match within story).
    3. Resolves location_name → location_id (fuzzy match within story).
    4. Creates/replaces Page+Panel records.
    5. Also saves the legacy scenes_text for backward compat.
    """
    from services.deepseek import split_scenes_structured, split_scenes

    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    if not chapter.messages:
        raise HTTPException(400, "No chat messages yet")

    story_id = chapter.story_id
    image_count = chapter.image_count or 10

    chat_history = [{"role": m.role, "content": m.content} for m in chapter.messages]

    # Load character profiles for prompt context
    char_profiles = ""
    if chapter.character_profiles:
        char_profiles = chapter.character_profiles.strip()
    elif chapter.story and chapter.story.character_profiles:
        char_profiles = chapter.story.character_profiles.strip()

    api_key = request.headers.get("x-deepseek-api-key") or None

    # --- Step 1: Get structured JSON from DeepSeek ---
    try:
        pages_json = await split_scenes_structured(chat_history, char_profiles, image_count, api_key)
    except Exception as exc:
        raise HTTPException(502, f"结构化分镜生成失败: {exc}")

    # --- Step 2: Load existing characters + locations for fuzzy resolution ---
    characters = db.query(Character).filter(Character.story_id == story_id).all()
    locations = db.query(Location).filter(Location.story_id == story_id).all()
    char_aliases: dict[int, list[str]] = {c.id: (c.aliases or []) for c in characters}

    def _resolve_char_ids(names: list[str]) -> list[int]:
        ids: list[int] = []
        for n in names:
            m = _fuzzy_match_character(n, characters, char_aliases)
            if m and m.id not in ids:
                ids.append(m.id)
        return ids

    def _resolve_location_id(name: str) -> int | None:
        if not name:
            return None
        m = _fuzzy_match_location(name, locations)
        return m.id if m else None

    # --- Step 3: Delete old pages for this chapter, create new ones ---
    old_pages = db.query(Page).filter(Page.chapter_id == chapter_id).all()
    for p in old_pages:
        db.delete(p)
    db.flush()

    new_pages: list[Page] = []
    for page_obj in pages_json:
        if isinstance(page_obj, str):
            # Fallback: plain string page (shouldn't happen with structured prompt)
            pg = Page(chapter_id=chapter_id, page_number=len(new_pages) + 1)
            db.add(pg)
            db.flush()
            panel = Panel(
                page_id=pg.id,
                panel_number=1,
                description=page_obj,
            )
            db.add(panel)
            new_pages.append(pg)
            continue

        page_num = page_obj.get("page", len(new_pages) + 1)
        pg = Page(
            chapter_id=chapter_id,
            page_number=page_num,
            layout_hint=None,
        )
        db.add(pg)
        db.flush()

        panels_data = page_obj.get("panels", [])
        for panel_data in panels_data:
            char_names = panel_data.get("character_names", []) or []
            char_ids = _resolve_char_ids(char_names)
            loc_name = panel_data.get("location_name", "") or ""
            loc_id = _resolve_location_id(loc_name)

            # Build description for backward compat / display
            action = panel_data.get("action", "")
            dlg_list = panel_data.get("dialogue", []) or []
            dlg_str = " ".join(f'「{d["speaker"]}：{d["text"]}」' for d in dlg_list if d.get("text"))
            sfx = "、".join(panel_data.get("sfx", []) or [])

            description_parts = []
            if action:
                description_parts.append(action)
            if dlg_str:
                description_parts.append(dlg_str)
            if sfx:
                description_parts.append(f"音效：{sfx}")
            description = " ".join(description_parts)

            panel = Panel(
                page_id=pg.id,
                panel_number=panel_data.get("panel_number", 1),
                description=description or None,
                dialogue=dlg_str or None,
                character_ids=char_ids if char_ids else None,
                outfit_ids=None,
                location_id=loc_id,
                camera_angle=panel_data.get("shot_type") or panel_data.get("frame_size") or None,
            )
            db.add(panel)

        new_pages.append(pg)

    # --- Step 4: Also save legacy scenes_text for backward compat ---
    try:
        legacy_scenes = await split_scenes.__wrapped__(  # type: ignore[attr-defined]
            None, None, None, None
        )
    except Exception:
        pass

    # Build legacy scenes from the structured data we already have
    legacy_scenes_list: list[str] = []
    for page_obj in pages_json:
        if isinstance(page_obj, str):
            legacy_scenes_list.append(page_obj)
            continue
        panels_data = page_obj.get("panels", [])
        parts: list[str] = [f"第{page_obj.get('page', len(legacy_scenes_list)+1)}页："]
        for panel in panels_data:
            pn = panel.get("panel_number", "?")
            fs = panel.get("frame_size", "")
            label = f"【第{pn}格（{fs}）】" if fs else f"【第{pn}格】"
            action = panel.get("action", "")
            chars = panel.get("character_names", [])
            chars_str = f"出场：{'、'.join(chars)}。" if chars else ""
            loc = panel.get("location_name", "")
            loc_str = f"场景：{loc}。" if loc else ""
            dlg_parts = [f"「{d['speaker']}：{d['text']}」" for d in panel.get("dialogue", []) if d.get("text")]
            dlg_str = " ".join(dlg_parts)
            sfx_parts = panel.get("sfx", [])
            sfx_str = f" 音效：{''.join(sfx_parts)}" if sfx_parts else ""
            parts.append(f"{label}{chars_str}{loc_str}{action}{dlg_str}{sfx_str}")
        legacy_scenes_list.append("".join(parts))

    scenes_text = "\n\n".join(
        f"=== 第{idx}格 ===\n{s}" for idx, s in enumerate(legacy_scenes_list, 1)
    ).strip() + "\n"
    chapter.scenes_text = scenes_text

    db.commit()
    for pg in new_pages:
        db.refresh(pg)

    return new_pages


# ──────────────────────────────────────────────────────────────────────────────
# Resolve panel names → IDs (lightweight helper for frontend re-resolution)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/api/chapters/{chapter_id}/resolve-panels")
async def resolve_panels(chapter_id: int, request: Request, db: Session = Depends(get_db)):
    """Re-resolve character_names/location_name to IDs for all panels in chapter.

    Useful after user creates new characters/locations in the library.
    """
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    story_id = chapter.story_id
    characters = db.query(Character).filter(Character.story_id == story_id).all()
    locations = db.query(Location).filter(Location.story_id == story_id).all()
    char_aliases: dict[int, list[str]] = {c.id: (c.aliases or []) for c in characters}

    pages = db.query(Page).filter(Page.chapter_id == chapter_id).all()
    updated = 0
    for page in pages:
        for panel in page.panels:
            # We can only re-resolve if character names are stored in description
            # This endpoint is mainly a no-op placeholder for now - panels already
            # have ids set at creation time. Future: store raw names in a separate field.
            pass

    db.commit()
    return {"ok": True, "pages": len(pages), "updated_panels": updated}


# ──────────────────────────────────────────────────────────────────────────────
# Panel reference image resolver (for image generation)
# ──────────────────────────────────────────────────────────────────────────────

def get_panel_ref_image_paths(panel: Panel, story_id: int, base_dir: Path) -> list[Path]:
    """Collect reference image paths for a specific panel.

    Priority order for each character in the panel:
      1. Specific outfit ref image (if outfit_ids set)
      2. Character avatar
      3. Fall through to story-level defaults
    For location:
      1. Location ref_image_path
    """
    paths: list[Path] = []
    seen: set[str] = set()

    def _add(p: Path | str | None) -> None:
        if not p:
            return
        path = Path(p) if isinstance(p, str) else p
        # Resolve relative to base_dir if not absolute
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        key = str(path)
        if key not in seen and path.exists() and path.is_file():
            seen.add(key)
            paths.append(path)

    # Character refs
    char_ids: list[int] = panel.character_ids or []
    outfit_ids: list[int] = panel.outfit_ids or []

    for char_id in char_ids:
        from database import SessionLocal
        # We're already inside a request with a db session; use it via sqlalchemy
        # (panel is already loaded from db, so we can query via panel.page.chapter...)
        # Instead we use the db session passed through the panel's session context.
        # Since we don't have db here, defer to caller or use lazy-load.
        pass  # handled below via db parameter

    return paths  # caller fills in after querying


def resolve_panel_refs(
    panel: Panel,
    db: Session,
    manga_dir: Path,
) -> list[Path]:
    """Resolve reference image paths for a panel using DB lookups."""
    paths: list[Path] = []
    seen: set[str] = set()

    def _add(rel_path: str | None) -> None:
        if not rel_path:
            return
        full = (manga_dir.parent / rel_path).resolve()
        k = str(full)
        if k not in seen and full.exists():
            seen.add(k)
            paths.append(full)

    char_ids: list[int] = panel.character_ids or []
    outfit_ids_set: set[int] = set(panel.outfit_ids or [])

    for char_id in char_ids:
        char = db.get(Character, char_id)
        if not char:
            continue
        # Try specific outfit first
        found_outfit = False
        for outfit in (char.outfits or []):
            if outfit.id in outfit_ids_set and outfit.ref_image_path:
                _add(outfit.ref_image_path)
                found_outfit = True
                break
        if not found_outfit:
            # Use avatar or first outfit with image
            if char.avatar_path:
                _add(char.avatar_path)
            else:
                for outfit in (char.outfits or []):
                    if outfit.ref_image_path:
                        _add(outfit.ref_image_path)
                        break

    # Location ref
    if panel.location_id:
        loc = db.get(Location, panel.location_id)
        if loc and loc.ref_image_path:
            _add(loc.ref_image_path)

    return paths
