import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名故事")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ref_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    character_profiles: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    chapters: Mapped[list["Chapter"]] = relationship("Chapter", back_populates="story", order_by="Chapter.chapter_number", cascade="all, delete-orphan")
    asset_groups: Mapped[list["StoryAssetGroup"]] = relationship("StoryAssetGroup", back_populates="story", order_by="StoryAssetGroup.id", cascade="all, delete-orphan")
    characters: Mapped[list["Character"]] = relationship("Character", back_populates="story", order_by="Character.sort_order", cascade="all, delete-orphan")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="story", order_by="Location.sort_order", cascade="all, delete-orphan", foreign_keys="[Location.story_id]")
    share_tokens: Mapped[list["StoryShareToken"]] = relationship("StoryShareToken", back_populates="story", cascade="all, delete-orphan")

    @property
    def has_character_profiles(self) -> bool:
        return bool((self.character_profiles or "").strip())


class StoryAssetGroup(Base):
    __tablename__ = "story_asset_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="设定组")
    character_profiles: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    story: Mapped["Story"] = relationship("Story", back_populates="asset_groups")
    chapters: Mapped[list["Chapter"]] = relationship("Chapter", back_populates="asset_group")

    @property
    def has_character_profiles(self) -> bool:
        return bool((self.character_profiles or "").strip())


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("story_id", "chapter_number", name="uq_chapters_story_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id"), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    novel_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scenes_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    character_profiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_group_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("story_asset_groups.id"), nullable=True)
    ref_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    image_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    # Phase 3: chapter summary & style presets
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI-generated summary of this chapter's content
    art_style: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Phase 4: art style preset: shonen | shojo | chibi | ink | cel
    aspect_ratio: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Phase 4: aspect ratio: portrait | landscape | square

    story: Mapped["Story"] = relationship("Story", back_populates="chapters")
    asset_group: Mapped["StoryAssetGroup | None"] = relationship("StoryAssetGroup", back_populates="chapters")
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="chapter", order_by="ChatMessage.created_at", cascade="all, delete-orphan")
    images: Mapped[list["MangaImage"]] = relationship("MangaImage", back_populates="chapter", order_by="MangaImage.image_number", cascade="all, delete-orphan")
    pages: Mapped[list["Page"]] = relationship("Page", back_populates="chapter", order_by="Page.page_number", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="messages")


class MangaImage(Base):
    __tablename__ = "manga_images"
    __table_args__ = (UniqueConstraint("chapter_id", "image_number", name="uq_manga_images_chapter_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id"), nullable=False)
    image_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="images")



# ─── Phase 1: Structured Asset Library ──────────────────────


class Character(Base):
    """Structured character entry in the asset library."""
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="supporting")
    # role values: protagonist, supporting, antagonist, background
    aliases: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # aliases: ["小明", "阿明"] — alternative names for AI matching
    core_appearance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Structured appearance: { "hair": "黑色短发", "eyes": "棕色", "build": "中等", "features": "左脸有疤" }
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form description / notes
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    story: Mapped["Story"] = relationship("Story", back_populates="characters")
    outfits: Mapped[list["Outfit"]] = relationship("Outfit", back_populates="character", order_by="Outfit.sort_order", cascade="all, delete-orphan")
    appearance_events: Mapped[list["CharacterAppearanceEvent"]] = relationship("CharacterAppearanceEvent", back_populates="character", order_by="CharacterAppearanceEvent.chapter_number", cascade="all, delete-orphan")


class Outfit(Base):
    """A costume/outfit variant for a character, each with its own reference image."""
    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="默认造型")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    character: Mapped["Character"] = relationship("Character", back_populates="outfits")


class Location(Base):
    """Scene/location library entry. Supports hierarchy via parent_id."""
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("locations.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    story: Mapped["Story"] = relationship("Story", back_populates="locations")
    parent: Mapped["Location | None"] = relationship("Location", remote_side="Location.id", back_populates="children")
    children: Mapped[list["Location"]] = relationship("Location", back_populates="parent", cascade="all, delete-orphan")


class Page(Base):
    """A page in a chapter's storyboard. Contains multiple panels."""
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    layout_hint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g. "2x2", "full-page", "3-row"
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="pages")
    panels: Mapped[list["Panel"]] = relationship("Panel", back_populates="page", order_by="Panel.panel_number", cascade="all, delete-orphan")


class Panel(Base):
    """A single panel (frame) in a storyboard page. References characters/locations by ID."""
    __tablename__ = "panels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(Integer, ForeignKey("pages.id"), nullable=False)
    panel_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The scene description for this panel (what's happening)
    dialogue: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Character dialogue / text in this panel
    character_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [12, 34] — references to Character.id appearing in this panel
    outfit_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [5, 8] — specific outfits to use for characters in this panel
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("locations.id"), nullable=True)
    camera_angle: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g. "close-up", "wide-shot", "bird-eye"
    generated_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    page: Mapped["Page"] = relationship("Page", back_populates="panels")
    location: Mapped["Location | None"] = relationship("Location")



# ─── Phase 3: Character Appearance Events ────────────────────


class CharacterAppearanceEvent(Base):
    """Records a change in a character's appearance at a specific chapter.

    E.g. "Chapter 50: gets a haircut → short silver hair".
    After this chapter_number, the new appearance description is used for prompts.
    """
    __tablename__ = "character_appearance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Chapter number FROM which this appearance takes effect
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # New appearance description after this event
    event_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Human-readable note of what changed, e.g. "剪头发，现在是短银发"
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    character: Mapped["Character"] = relationship("Character", back_populates="appearance_events")


# ─── Phase 4: Story Share Token ──────────────────────────────


class StoryShareToken(Base):
    """Read-only public share token for a story."""
    __tablename__ = "story_share_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    story: Mapped["Story"] = relationship("Story", back_populates="share_tokens")


# ─── Phase 4: N-pick image candidates ────────────────────────


class ImageCandidate(Base):
    """Stores N image candidates for a panel (N-pick feature). User picks one to keep."""
    __tablename__ = "image_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id"), nullable=False)
    image_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
