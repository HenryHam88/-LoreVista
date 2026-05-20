from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, model_validator


# --- Story ---
class StoryCreate(BaseModel):
    title: str = "未命名故事"
    description: str = ""


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class StoryOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = ""
    cover_image: Optional[str] = None
    ref_image: Optional[str] = None
    has_character_profiles: bool = False
    has_ref_image: bool = False
    created_at: datetime.datetime

    model_config = {"from_attributes": True}

    @model_validator(mode='before')
    @classmethod
    def _extract_computed_flags(cls, data):
        if hasattr(data, 'character_profiles'):
            cp = getattr(data, 'character_profiles', '') or ''
            ref_image = getattr(data, 'ref_image', '') or ''
            d = dict(data.__dict__) if hasattr(data, '__dict__') else dict(data)
            d['has_character_profiles'] = bool(cp.strip())
            groups = list(getattr(data, 'asset_groups', []) or [])
            if not d['has_character_profiles']:
                d['has_character_profiles'] = any(bool((getattr(group, 'character_profiles', '') or '').strip()) for group in groups)
            # Check DB ref_image field OR multi-ref dir on disk
            has_db_ref = bool(ref_image and (Path(__file__).resolve().parent / ref_image).exists())
            story_id = getattr(data, 'id', None)
            has_multi_ref = False
            has_legacy_ref = False
            has_group_ref = False
            if story_id:
                story_dir = Path(__file__).resolve().parent / "manga_outputs" / f"story_{story_id}"
                ref_dir = story_dir / "ref_images"
                has_multi_ref = ref_dir.exists() and any(
                    p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
                    for p in ref_dir.iterdir()
                )
                has_legacy_ref = (story_dir / "ref_image.png").exists()
            for group in groups:
                group_id = getattr(group, 'id', None)
                if not group_id:
                    continue
                ref_dir = Path(__file__).resolve().parent / "manga_outputs" / "asset_groups" / f"group_{group_id}" / "ref_images"
                if ref_dir.exists() and any(p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} for p in ref_dir.iterdir()):
                    has_group_ref = True
                    break
            d['has_ref_image'] = has_db_ref or has_multi_ref or has_legacy_ref or has_group_ref
            return d
        return data


# --- Chapter ---
class ChapterUpdate(BaseModel):
    title: Optional[str] = None


class ChapterOut(BaseModel):
    id: int
    story_id: int
    chapter_number: int
    title: Optional[str] = None
    novel_content: Optional[str] = None
    content_source: Optional[str] = None
    asset_group_id: Optional[int] = None
    created_at: datetime.datetime
    messages: list[ChatMessageOut] = []
    images: list[MangaImageOut] = []

    model_config = {"from_attributes": True}


# --- Chat ---
class ChatMessageIn(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    id: int
    chapter_id: int
    role: str
    content: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# --- Manga ---
class MangaImageOut(BaseModel):
    id: int
    chapter_id: int
    image_number: int
    image_path: str
    prompt: Optional[str] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class GenerateNovelRequest(BaseModel):
    pass


class GenerateMangaRequest(BaseModel):
    pass


# ─── Phase 1: Structured Asset Library Schemas ──────────────


# --- Character ---
class CharacterCreate(BaseModel):
    name: str
    role: str = "supporting"
    aliases: Optional[list[str]] = None
    core_appearance: Optional[dict] = None
    description: Optional[str] = None
    sort_order: int = 0


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    aliases: Optional[list[str]] = None
    core_appearance: Optional[dict] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class OutfitOut(BaseModel):
    id: int
    character_id: int
    label: str
    description: Optional[str] = None
    ref_image_path: Optional[str] = None
    sort_order: int = 0
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class CharacterOut(BaseModel):
    id: int
    story_id: int
    name: str
    role: str
    aliases: Optional[list[str]] = None
    core_appearance: Optional[dict] = None
    description: Optional[str] = None
    avatar_path: Optional[str] = None
    sort_order: int = 0
    outfits: list[OutfitOut] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


# --- Outfit ---
class OutfitCreate(BaseModel):
    label: str = "默认造型"
    description: Optional[str] = None
    sort_order: int = 0


class OutfitUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


# --- Location ---
class LocationCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: int = 0


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class LocationOut(BaseModel):
    id: int
    story_id: int
    parent_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    ref_image_path: Optional[str] = None
    sort_order: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


# --- Page & Panel ---
class PanelCreate(BaseModel):
    panel_number: int = 1
    description: Optional[str] = None
    dialogue: Optional[str] = None
    character_ids: Optional[list[int]] = None
    outfit_ids: Optional[list[int]] = None
    location_id: Optional[int] = None
    camera_angle: Optional[str] = None


class PanelUpdate(BaseModel):
    panel_number: Optional[int] = None
    description: Optional[str] = None
    dialogue: Optional[str] = None
    character_ids: Optional[list[int]] = None
    outfit_ids: Optional[list[int]] = None
    location_id: Optional[int] = None
    camera_angle: Optional[str] = None


class PanelOut(BaseModel):
    id: int
    page_id: int
    panel_number: int
    description: Optional[str] = None
    dialogue: Optional[str] = None
    character_ids: Optional[list[int]] = None
    outfit_ids: Optional[list[int]] = None
    location_id: Optional[int] = None
    camera_angle: Optional[str] = None
    generated_image_path: Optional[str] = None
    generated_prompt: Optional[str] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class PageCreate(BaseModel):
    page_number: int = 1
    layout_hint: Optional[str] = None
    panels: list[PanelCreate] = []


class PageUpdate(BaseModel):
    page_number: Optional[int] = None
    layout_hint: Optional[str] = None


class PageOut(BaseModel):
    id: int
    chapter_id: int
    page_number: int
    layout_hint: Optional[str] = None
    panels: list[PanelOut] = []
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# Resolve forward references
ChapterOut.model_rebuild()
CharacterOut.model_rebuild()
PageOut.model_rebuild()
