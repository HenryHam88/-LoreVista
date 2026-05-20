import asyncio
import base64
import io
import logging
import os
import re
import time
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image

logger = logging.getLogger("image2")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

load_dotenv()

DEFAULT_IMAGE_API_BASE_URL = "https://api.duojie.games/v1"


def normalize_image_api_base_url(base_url: str | None) -> str:
    base = (base_url or DEFAULT_IMAGE_API_BASE_URL).strip().rstrip("/")
    return re.sub(r"(?i)(/v1)+$", "/v1", base)


IMAGE_API_BASE_URL = normalize_image_api_base_url(os.getenv("IMAGE_API_BASE_URL"))
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "")
IMAGE_MODEL = "gpt-image-2"
IMAGE_SIZE = "1024x1536"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "manga_outputs"

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds (base, exponential backoff applied)

# Phase 3: Concurrency & rate limiting
# Generate up to CONCURRENT_IMAGES images in parallel; throttle with a semaphore.
CONCURRENT_IMAGES = int(os.getenv("CONCURRENT_IMAGES", "2"))
_gen_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _gen_semaphore
    if _gen_semaphore is None:
        _gen_semaphore = asyncio.Semaphore(CONCURRENT_IMAGES)
    return _gen_semaphore


def _image_auth_headers(api_key: str | None = None, json_content: bool = False) -> dict[str, str]:
    key = (api_key or IMAGE_API_KEY or "").strip()
    if not key:
        from .errors import MissingApiKeyError
        raise MissingApiKeyError("Image2")
    headers = {"Authorization": f"Bearer {key}"}
    if json_content:
        headers["Content-Type"] = "application/json"
    return headers


def normalize_image_bytes(image_bytes: bytes) -> bytes:
    """Validate image bytes and return normalized PNG bytes."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
        with Image.open(io.BytesIO(image_bytes)) as img:
            output = io.BytesIO()
            img.convert("RGBA").save(output, format="PNG", optimize=True)
            return output.getvalue()
    except Exception as exc:
        raise RuntimeError("Generated image response is not a valid image") from exc


async def generate_manga_image(
    prompt: str,
    chapter_id: int,
    image_number: int,
    all_scenes: list[str] | None = None,
    character_profiles: str = "",
    ref_image_paths: list[str] | None = None,
    color_mode: str = "bw",
    api_key: str | None = None,
    art_style: str | None = None,
    aspect_ratio: str | None = None,
) -> str:
    """Generate a single manga image and save it. Returns the relative file path.

    Phase 3: Uses semaphore for concurrency control + exponential backoff retry.
    Phase 4: Supports art_style and aspect_ratio overrides.
    """
    from services.deepseek import ART_STYLE_PROMPTS, ASPECT_RATIO_SIZES, DEFAULT_ASPECT_RATIO

    total_pages = len(all_scenes) if all_scenes else 1
    progress_label = f"{image_number}/{total_pages}"
    valid_refs = [Path(p) for p in (ref_image_paths or []) if p and Path(p).exists()]
    use_ref = bool(valid_refs)

    char_block = ""
    if character_profiles and not use_ref:
        char_block = f"【角色外貌设定（每张图必须严格遵守）】\n{character_profiles}\n\n"

    ref_block = ""
    if use_ref:
        ref_block = (
            "【最重要：人物一致性】\n"
            "本次提供了参考图，**必须严格保持参考图中主角的外貌特征**："
            "包括发型、发色、瞳色、脸型、五官比例、服装风格——所有分镜格中的人物都必须是参考图中的同一批人物。\n"
            "禁止凭空创造新的人物外貌。\n\n"
        )

    # Phase 4: Art style block
    style_block = ""
    if art_style and art_style in ART_STYLE_PROMPTS:
        style_block = f"【画面风格要求】{ART_STYLE_PROMPTS[art_style]}\n\n"

    # Phase 4: Aspect ratio → image size
    image_size = ASPECT_RATIO_SIZES.get(aspect_ratio or DEFAULT_ASPECT_RATIO, IMAGE_SIZE)

    if color_mode == "color":
        MANGA_STYLE = (
            "日式彩色漫画插画页，竖向多格分镜布局，每页包含4-6个分镜格，"
            "格子高度不等（动作场景用宽格，对话特写用窄格），"
            "每个分镜格之间有清晰的边框分隔，"
            "包含圆形/椭圆形对话气泡和中文台词，"
            "包含漫画音效字（如\u300c唷\u300d\u300c铿！\u300d\u300c嗡—\u300d），"
            "全彩高饱和度配色，日系动漫赛璐珞上色风格，"
            "柔和光影与高光，细腻的色彩渐变，"
            "人物绘制精美，表情生动，动作有力度感"
        )
    else:
        MANGA_STYLE = (
            "日式黑白漫画页，竖向多格分镜布局，每页包含4-6个分镜格，"
            "格子高度不等（动作场景用宽格，对话特写用窄格），"
            "每个分镜格之间有清晰的黑色边框分隔，"
            "包含圆形/椭圆形白色对话气泡和中文台词，"
            "包含漫画音效字（如\u300c唷\u300d\u300c铿！\u300d\u300c嗡—\u300d），"
            "黑白高对比度，戏剧性光影，精细的线条和网点，"
            "人物绘制精美，表情生动，动作有力度感"
        )

    if all_scenes:
        script_context = "\n".join(f"第{i+1}页：{s}" for i, s in enumerate(all_scenes))
        full_prompt = (
            f"{ref_block}"
            f"{char_block}"
            f"{style_block}"
            f"你正在绘制一部日式漫画的第{image_number}页（共{total_pages}页）。\n"
            f"以下是完整的{total_pages}页的分镜脚本，请保持人物外貌、服装、风格的一致性：\n\n"
            f"{script_context}\n\n"
            f"现在请绘制第{image_number}页：\n"
            f"{MANGA_STYLE}\n{prompt}"
        )
    else:
        full_prompt = f"{ref_block}{char_block}{style_block}{MANGA_STYLE}\n{prompt}"

    # Prepare reference image bytes (one or multiple)
    ref_blobs: list[tuple[str, bytes]] = []
    for idx, ref_path in enumerate(valid_refs, start=1):
        try:
            img = Image.open(ref_path)
            max_side = 1024
            ratio = min(max_side / img.width, max_side / img.height)
            if ratio < 1:
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.convert("RGBA").save(buf, format="PNG", optimize=True)
            blob = buf.getvalue()
            ref_blobs.append((f"ref{idx}.png", blob))
            logger.info(f"[{progress_label}] 参考图 {idx} 已加载: {ref_path.name} → {len(blob) / 1024:.0f} KB")
        except Exception as exc:
            logger.warning(f"[{progress_label}] 参考图 {ref_path} 加载失败: {exc}")

    last_err: Exception | None = None
    # Phase 3: Acquire semaphore to limit concurrent API calls
    async with _get_semaphore():
        for attempt in range(1, MAX_RETRIES + 1):
            heartbeat_task: asyncio.Task | None = None
            try:
                mode = f"edits({len(ref_blobs)}图垫图)" if ref_blobs else "generations"
                logger.info(f"[{progress_label}] 开始调用 Image2 API [{mode}]（尝试 {attempt}/{MAX_RETRIES}）")
                t0 = time.time()

                async def _heartbeat(label: str, start_ts: float) -> None:
                    try:
                        while True:
                            await asyncio.sleep(30)
                            waited = int(time.time() - start_ts)
                            logger.info(f"[{label}] 等待中... 已等待 {waited}s（上游可能排队，继续等）")
                    except asyncio.CancelledError:
                        return

                heartbeat_task = asyncio.create_task(_heartbeat(progress_label, t0))
                timeout = httpx.Timeout(connect=30, read=600, write=120, pool=30)
                limits = httpx.Limits(max_connections=1, max_keepalive_connections=0)
                async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                    if ref_blobs:
                        if len(ref_blobs) == 1:
                            files = [("image", (ref_blobs[0][0], io.BytesIO(ref_blobs[0][1]), "image/png"))]
                        else:
                            files = [
                                ("image[]", (name, io.BytesIO(blob), "image/png"))
                                for name, blob in ref_blobs
                            ]
                        resp = await client.post(
                            f"{IMAGE_API_BASE_URL}/images/edits",
                            files=files,
                            data={"model": IMAGE_MODEL, "prompt": full_prompt, "size": image_size},
                            headers=_image_auth_headers(api_key),
                        )
                    else:
                        resp = await client.post(
                            f"{IMAGE_API_BASE_URL}/images/generations",
                            json={"model": IMAGE_MODEL, "prompt": full_prompt, "size": image_size},
                            headers=_image_auth_headers(api_key, json_content=True),
                        )
                    resp.raise_for_status()
                    data = resp.json()
                heartbeat_task.cancel()
                elapsed = time.time() - t0
                logger.info(f"[{progress_label}] API 返回成功，耗时 {elapsed:.1f}s")

                image_entry = data["data"][0]

                if image_entry.get("b64_json"):
                    image_bytes = base64.b64decode(image_entry["b64_json"])
                elif image_entry.get("url"):
                    async with httpx.AsyncClient(timeout=120) as client:
                        img_resp = await client.get(image_entry["url"])
                        img_resp.raise_for_status()
                        image_bytes = img_resp.content
                else:
                    raise RuntimeError("No b64_json or url in image response")

                image_bytes = normalize_image_bytes(image_bytes)
                chapter_dir = OUTPUT_DIR / f"chapter_{chapter_id}"
                chapter_dir.mkdir(parents=True, exist_ok=True)
                filename = f"panel_{image_number:02d}_{uuid.uuid4().hex[:8]}.png"
                filepath = chapter_dir / filename
                filepath.write_bytes(image_bytes)
                logger.info(f"[{progress_label}] 已保存到 {filepath}")
                return f"manga_outputs/chapter_{chapter_id}/{filename}"

            except Exception as e:
                last_err = e
                if heartbeat_task is not None:
                    heartbeat_task.cancel()
                logger.error(f"[{progress_label}] 尝试 {attempt} 失败: {e}")
                if attempt < MAX_RETRIES:
                    # Phase 3: Exponential backoff with jitter
                    backoff = RETRY_DELAY * (2 ** (attempt - 1))
                    logger.info(f"[{progress_label}] {backoff}秒后重试...")
                    await asyncio.sleep(backoff)

    raise RuntimeError(f"第{image_number}张图片生成失败（已重试{MAX_RETRIES}次）: {last_err}")


async def generate_image_candidates(
    prompt: str,
    chapter_id: int,
    image_number: int,
    n: int = 4,
    all_scenes: list[str] | None = None,
    character_profiles: str = "",
    ref_image_paths: list[str] | None = None,
    color_mode: str = "bw",
    api_key: str | None = None,
    art_style: str | None = None,
    aspect_ratio: str | None = None,
) -> list[str]:
    """Phase 4: Generate N candidate images for one panel slot concurrently.
    
    Returns list of file paths (relative). Caller saves to ImageCandidate table.
    """
    tasks = [
        generate_manga_image(
            prompt=prompt,
            chapter_id=chapter_id,
            image_number=image_number,
            all_scenes=all_scenes,
            character_profiles=character_profiles,
            ref_image_paths=ref_image_paths,
            color_mode=color_mode,
            api_key=api_key,
            art_style=art_style,
            aspect_ratio=aspect_ratio,
        )
        for _ in range(n)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    paths: list[str] = []
    for r in results:
        if isinstance(r, str):
            paths.append(r)
        else:
            logger.error(f"Candidate generation failed: {r}")
    if not paths:
        raise RuntimeError(f"All {n} candidate images failed to generate")
    return paths
