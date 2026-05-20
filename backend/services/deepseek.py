import json
import os
import re
from typing import AsyncGenerator

import httpx
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

# ─── Art Style Presets ───────────────────────────────────────

ART_STYLE_PROMPTS: dict[str, str] = {
    "shonen": (
        "少年漫画风格，动感十足，夸张的动作线，粗犷有力的线条，"
        "大眼睛的热血少年形象，强烈的明暗对比，网点纹理"
    ),
    "shojo": (
        "少女漫画风格，细腻柔美，大而闪亮的眼睛布满高光，"
        "花朵与星星点缀背景，精致的服饰细节，柔和的线条，浪漫氛围"
    ),
    "chibi": (
        "Q版/萌系漫画风格，2-3头身可爱比例，圆润的大头小身，"
        "表情夸张可爱，简洁明快的线条，活泼轻松的画面氛围"
    ),
    "ink": (
        "水墨漫画风格，毛笔线条，浓淡相宜的墨色，留白构图，"
        "东方美学意境，简练洒脱的笔触，烟雾与远山的层次感"
    ),
    "cel": (
        "赛璐珞动画风格，平整干净的色块填充，清晰的黑色轮廓线，"
        "简洁的阴影（2-tone shading），日式动画经典视觉语言，"
        "鲜艳饱和的配色，高光与反光明显"
    ),
}

# ─── Aspect Ratio → Image Size Mapping ──────────────────────

ASPECT_RATIO_SIZES: dict[str, str] = {
    "portrait": "1024x1536",   # 竖版（默认）
    "landscape": "1536x1024",  # 横版
    "square": "1024x1024",     # 单格特写/正方形
}

DEFAULT_ASPECT_RATIO = "portrait"

NOVEL_SYSTEM_PROMPT = """你是一位才华横溢、文笔细腻的网络小说家。用户会和你讨论小说的主题、风格、角色等。

当用户要求你创作小说时，请遵循以下要求：

## ★★★ 字数要求（最高优先级）★★★
- 每一话必须 4000-6000 中文字。这是硬性要求，不可商量。
- 绝对禁止低于 3500 字。如果你感觉写完了但字数不够，必须回去扩写场景、增加对话、深化心理描写，直到达到 4000 字以上。
- 宁可 5000-6000 字，也不要只写 2000 字就结束。

## 结构指导（确保内容充实）
一话内容应包含 3-5 个完整场景，每个场景至少 800-1500 字，包含：
- 场景转换时的环境描写（视觉、听觉、嗅觉、触觉），至少 150 字
- 人物之间的对话（自然生动，有潜台词，每段对话至少 5-8 个来回）
- 角色的心理活动和内心独白（每个场景至少一段）
- 微表情、小动作、肢体语言的细节描写

## 写作风格
- 描写要细腻丰富，注重氛围营造
- 节奏有张有弛，关键情感节点放慢节奏
- 人物描写立体鲜活，注重微表情、小动作、心理独白
- 避免流水账，避免大段无意义的抽象拒述

请直接输出小说正文，不要加额外说明或字数统计。"""


def _deepseek_auth_headers(api_key: str | None = None) -> dict[str, str]:
    key = (api_key or DEEPSEEK_API_KEY or "").strip()
    if not key:
        from .errors import MissingApiKeyError
        raise MissingApiKeyError("DeepSeek")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _loads_json_lenient(text: str):
    return json.loads(text, strict=False)


def _extract_json_array(raw: str) -> list:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        return _loads_json_lenient(raw)
    except json.JSONDecodeError as first_error:
        match = re.search(r"\[[\s\S]*\]", raw)
        if not match:
            raise ValueError("Scene split response did not contain a JSON array") from first_error
        try:
            return _loads_json_lenient(match.group(0))
        except json.JSONDecodeError as second_error:
            raise ValueError("Scene split response was not valid JSON") from second_error


def _extract_json_object(raw: str) -> dict:
    """Extract the first JSON object from a string (handles markdown code fences)."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    try:
        return _loads_json_lenient(raw)
    except json.JSONDecodeError as first_error:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("Response did not contain a JSON object") from first_error
        try:
            return _loads_json_lenient(match.group(0))
        except json.JSONDecodeError as second_error:
            raise ValueError("Response was not valid JSON") from second_error


# ─── Structured storyboard JSON schema ──────────────────────────────────────
#
# Each page:
# {
#   "page": 1,
#   "panels": [
#     {
#       "panel_number": 1,
#       "frame_size": "大宽格",
#       "shot_type": "远景",
#       "character_names": ["雪奈", "林昊"],
#       "location_name": "雪夜城堡-庭院",
#       "action": "雪奈仰头凝视城堡，林昊站在她身后",
#       "dialogue": [{"speaker": "雪奈", "text": "终于到了..."}],
#       "sfx": ["嗡——"]
#     }
#   ]
# }


def _structured_scene_split_prompt(page_count: int = 10) -> str:
    return f"""你是一位专业漫画分镜师。请将小说内容拆分为恰好{page_count}页漫画，输出严格的 JSON 格式。

## 输出格式
输出一个 JSON 数组，恰好 {page_count} 个元素，每个元素代表一页，格式如下：
{{
  "page": 页码（整数，从1开始）,
  "panels": [
    {{
      "panel_number": 格子编号（整数，从1开始）,
      "frame_size": "大宽格"|"宽格"|"中格"|"窄格"|"特写格",
      "shot_type": "远景"|"全景"|"中景"|"近景"|"特写"|"极特写",
      "character_names": ["小说中出现的角色名，使用原文名字，可以是空数组"],
      "location_name": "场景名称（如：学校走廊、雪夜庭院、破旧仓库），如无明显场景可为空字符串",
      "action": "这一格的画面描述：人物动作、表情、姿势、构图",
      "dialogue": [{{"speaker": "角色名", "text": "台词内容"}}],
      "sfx": ["音效字，如：嗡——、铿！、唰、咔嚓，无则为空数组"]
    }}
  ]
}}

## 规则
- 每页必须有 4-6 个格子（panel）
- character_names 必须使用小说原文中的角色名（不能用"男主"、"她"等代词，用真实名字）
- location_name 用简洁的中文描述，格式：大场景-小场景（如"魔法学院-图书馆"）
- 每页至少一个有台词的格子（dialogue 非空）
- 请严格输出 JSON，不要输出任何其他文字

示例输出（仅格式参考，内容必须基于小说实际内容）：
[
  {{
    "page": 1,
    "panels": [
      {{
        "panel_number": 1,
        "frame_size": "大宽格",
        "shot_type": "远景",
        "character_names": [],
        "location_name": "魔法学院-入口",
        "action": "黄昏下的魔法学院全景，尖塔上旗帜飘扬",
        "dialogue": [],
        "sfx": ["呼——"]
      }},
      {{
        "panel_number": 2,
        "frame_size": "中格",
        "shot_type": "近景",
        "character_names": ["艾拉"],
        "location_name": "魔法学院-入口",
        "action": "艾拉仰头凝视学院，眼神中充满期待",
        "dialogue": [{{"speaker": "艾拉", "text": "终于来了..."}}],
        "sfx": []
      }}
    ]
  }}
]

请直接输出 JSON 数组，不要包含任何解释文字："""


async def chat_stream(messages: list[dict], api_key: str | None = None) -> AsyncGenerator[str, None]:
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "system", "content": NOVEL_SYSTEM_PROMPT}] + messages,
        "stream": True,
        "max_tokens": 16384,
    }
    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream(
            "POST",
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=_deepseek_auth_headers(api_key),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def generate_novel(messages: list[dict], api_key: str | None = None) -> str:
    full_messages = [{"role": "system", "content": NOVEL_SYSTEM_PROMPT}] + messages
    full_messages.append({
        "role": "user",
        "content": "请根据我们的讨论，创作这一话的完整小说内容。请直接输出小说正文。",
    })
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": full_messages,
        "stream": False,
        "max_tokens": 16384,
    }
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=_deepseek_auth_headers(api_key),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def split_scenes_structured(
    chat_messages: list[dict],
    character_profiles: str = "",
    page_count: int = 10,
    api_key: str | None = None,
) -> list[dict]:
    """Split novel into structured storyboard JSON pages.

    Returns a list of page dicts, each containing a 'panels' list.
    """
    scene_prompt = _structured_scene_split_prompt(page_count)
    if character_profiles:
        scene_prompt += f"\n\n【角色外貌设定，分镜中必须使用这些角色的真实名字】\n{character_profiles}"

    messages = chat_messages + [{"role": "user", "content": scene_prompt}]
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"你是漫画分镜专家。严格输出 JSON 数组，恰好 {page_count} 个元素，"
                    "每个元素是一页漫画对象（含 page 和 panels 字段）。"
                    "panels 数组每页 4-6 个格子。绝对不输出 JSON 以外的任何内容。"
                ),
            }
        ] + messages,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=_deepseek_auth_headers(api_key),
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]

    pages = _extract_json_array(raw)
    if not isinstance(pages, list):
        raise ValueError("Structured scene split did not return a JSON array")
    if len(pages) != page_count:
        raise ValueError(f"Expected {page_count} pages, got {len(pages)}")
    return pages


async def split_scenes(
    chat_messages: list[dict],
    character_profiles: str = "",
    page_count: int = 10,
    api_key: str | None = None,
) -> list[str]:
    """Legacy: return list of plain strings (one per page).

    Internally calls split_scenes_structured and serialises back to strings
    so the old generate-scenes flow still works.
    """
    pages = await split_scenes_structured(
        chat_messages, character_profiles, page_count, api_key
    )
    result: list[str] = []
    for page_obj in pages:
        if isinstance(page_obj, str):
            result.append(page_obj)
            continue
        panels = page_obj.get("panels", [])
        parts: list[str] = [f"第{page_obj.get('page', len(result)+1)}页："]
        for panel in panels:
            pn = panel.get("panel_number", "?")
            fs = panel.get("frame_size", "")
            label = f"【第{pn}格（{fs}）】" if fs else f"【第{pn}格】"
            action = panel.get("action", "")
            chars = panel.get("character_names", [])
            chars_str = f"出场：{'、'.join(chars)}。" if chars else ""
            loc = panel.get("location_name", "")
            loc_str = f"场景：{loc}。" if loc else ""
            dlg_parts = [f"「{d['speaker']}：{d['text']}」" for d in panel.get("dialogue", [])]
            dlg_str = " ".join(dlg_parts)
            sfx_parts = panel.get("sfx", [])
            sfx_str = f" 音效：{''.join(sfx_parts)}" if sfx_parts else ""
            parts.append(f"{label}{chars_str}{loc_str}{action}{dlg_str}{sfx_str}")
        result.append("".join(parts))
    return result


# ─── Auto-extract characters from novel text ─────────────────────────────────

EXTRACT_CHARACTERS_PROMPT = """你是一个角色信息提取助手。请从小说文本中提取所有出现的角色信息。

## 输出格式
输出一个 JSON 数组，每个元素是一个角色对象：
[
  {{
    "name": "角色的真实名字（使用小说中的原文名，不用称谓或代词）",
    "role": "protagonist"|"supporting"|"antagonist"|"background",
    "aliases": ["其他称呼", "绰号", "如无则为空数组"],
    "description": "外貌描述：发型、发色、眼睛、身材、衣着等视觉特征，尽量具体",
    "core_appearance": {{
      "hair": "发型发色描述",
      "eyes": "眼睛颜色形状",
      "build": "身材描述",
      "features": "显著特征（如疤痕、眼镜等）",
      "clothing": "常见服装"
    }},
    "confidence": 0.9
  }}
]

## 规则
- 只提取有名字或有显著描述的角色，忽略泛泛的"路人甲"
- name 必须用原文名字（如"艾拉"而非"女主"）
- confidence 表示你对这个角色身份的把握程度（0-1），路人写 0.5，主要角色写 0.9-1.0
- 如果小说中没有明确名字，用文中最常用的称呼
- aliases 包含文中的其他称呼（如"殿下"、"小姐"、"阿明"等）
- 输出 JSON 数组，不要输出其他文字"""

EXTRACT_LOCATIONS_PROMPT = """你是一个场景信息提取助手。请从小说文本中提取所有出现的场景/地点信息。

## 输出格式
输出一个 JSON 数组，每个元素是一个场景对象：
[
  {{
    "name": "场景名称（简洁明确，如：魔法学院图书馆）",
    "parent_name": "父场景名称（如：图书馆的父场景是魔法学院），如果是顶级场景则为空字符串",
    "description": "场景的视觉描述：环境、光线、氛围、标志性物品等",
    "confidence": 0.9
  }}
]

## 规则
- 只提取有实质描述的场景，忽略极简一笔带过的
- name 用简洁的中文，格式建议：大场所-具体位置（如：皇宫-御花园）
- parent_name 用于建立层级关系，如"皇宫"是"皇宫-御花园"的父场景
- 同一个场景不要重复提取
- 输出 JSON 数组，不要输出其他文字"""


async def extract_characters(
    novel_text: str,
    existing_names: list[str] | None = None,
    api_key: str | None = None,
) -> list[dict]:
    """Extract characters from novel text, returning structured JSON list."""
    extra = ""
    if existing_names:
        extra = f"\n\n【已有角色库（这些角色已存在，请合并观察而非重复创建）】：{', '.join(existing_names)}"

    messages = [
        {"role": "system", "content": EXTRACT_CHARACTERS_PROMPT},
        {"role": "user", "content": f"请从以下小说文本中提取角色信息：{extra}\n\n---\n{novel_text}\n---\n\n输出 JSON 数组："},
    ]
    payload = {"model": DEEPSEEK_MODEL, "messages": messages, "stream": False}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=_deepseek_auth_headers(api_key),
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

    result = _extract_json_array(raw)
    if not isinstance(result, list):
        raise ValueError("Character extraction did not return a JSON array")
    return result


async def extract_locations(
    novel_text: str,
    existing_names: list[str] | None = None,
    api_key: str | None = None,
) -> list[dict]:
    """Extract locations from novel text, returning structured JSON list."""
    extra = ""
    if existing_names:
        extra = f"\n\n【已有场景库（请合并已有场景，避免重复）】：{', '.join(existing_names)}"

    messages = [
        {"role": "system", "content": EXTRACT_LOCATIONS_PROMPT},
        {"role": "user", "content": f"请从以下小说文本中提取场景信息：{extra}\n\n---\n{novel_text}\n---\n\n输出 JSON 数组："},
    ]
    payload = {"model": DEEPSEEK_MODEL, "messages": messages, "stream": False}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=_deepseek_auth_headers(api_key),
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

    result = _extract_json_array(raw)
    if not isinstance(result, list):
        raise ValueError("Location extraction did not return a JSON array")
    return result



# ─── Phase 3: Chapter Summary ────────────────────────────────

CHAPTER_SUMMARY_PROMPT = """你是一位专业的小说编辑。请为给定的这一话小说内容生成一段简洁的"前情提要"摘要。

## 要求
- 摘要长度：150-300 字
- 包含本话的核心事件、人物行动、情感转折
- 使用第三人称客观叙述
- 不要剧透太多细节，保持悬念感
- 结尾用一句话点明本话的情绪基调或关键悬念
- 直接输出摘要正文，不要加标题或说明"""


async def generate_chapter_summary(
    novel_content: str,
    chapter_number: int,
    api_key: str | None = None,
) -> str:
    """Generate a concise summary for a chapter. Used as 「前情提要」for the next chapter."""
    messages = [
        {"role": "system", "content": CHAPTER_SUMMARY_PROMPT},
        {
            "role": "user",
            "content": f"请为第{chapter_number}话的内容生成前情提要：\n\n---\n{novel_content[:8000]}\n---\n\n直接输出摘要：",
        },
    ]
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False,
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=_deepseek_auth_headers(api_key),
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


def build_recap_injection(previous_summaries: list[tuple[int, str]]) -> str:
    """Build a 「前情提要」block to inject at the start of chat history.

    Args:
        previous_summaries: list of (chapter_number, summary_text) tuples, in order.
    Returns:
        A formatted recap string to inject as a system/user message.
    """
    if not previous_summaries:
        return ""
    lines = ["【前情提要 — 请严格遵守以下已发生的剧情，不得矛盾或遗忘】"]
    for ch_num, summary in previous_summaries[-5:]:  # Keep last 5 chapters max
        lines.append(f"\n▶ 第{ch_num}话：{summary}")
    lines.append("\n【以上是已发生的故事，请在此基础上继续创作下一话】")
    return "\n".join(lines)
