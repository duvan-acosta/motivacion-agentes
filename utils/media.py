"""Utilidades de medios."""

from __future__ import annotations

import logging
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from utils.config import ensure_dir, get_settings

logger = logging.getLogger(__name__)

THEME_GRADIENTS = {
    "resiliencia": ((30, 40, 60), (80, 100, 130)),
    "calma": ((20, 50, 70), (60, 120, 150)),
    "claridad": ((40, 30, 60), (200, 150, 80)),
    "propósito": ((25, 45, 35), (70, 110, 90)),
    "gratitud": ((50, 30, 20), (180, 120, 60)),
    "presencia": ((30, 35, 40), (90, 100, 110)),
    "coraje": ((20, 25, 50), (60, 80, 140)),
    "sabiduría": ((15, 15, 35), (50, 50, 90)),
}


def fetch_pexels_photo(keywords: list[str], width: int = 1080, height: int = 1080) -> Image.Image | None:
    settings = get_settings()
    if not settings.has_pexels() or settings.demo_mode:
        return None
    query = " ".join(keywords[:2]) or "peaceful nature"
    headers = {"Authorization": settings.pexels_api_key}
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        url = photos[0]["src"].get("large2x") or photos[0]["src"]["large"]
        img_resp = requests.get(url, timeout=60)
        img_resp.raise_for_status()
        from io import BytesIO

        return Image.open(BytesIO(img_resp.content)).convert("RGB")
    except Exception as exc:
        logger.warning("Pexels photo falló: %s", exc)
        return None


def create_gradient_background(width: int, height: int, theme: str) -> Image.Image:
    top, bottom = THEME_GRADIENTS.get(theme, ((25, 35, 50), (70, 90, 120)))
    img = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    return img


def _load_font(size: int, font_name: str, fallback: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        f"C:/Windows/Fonts/{font_name.replace(' ', '')}.ttf",
        f"C:/Windows/Fonts/{fallback.replace(' ', '')}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_text_overlay(
    background: Image.Image,
    message: str,
    visual_spec: dict,
) -> Image.Image:
    img = background.copy()
    width, height = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    opacity = int(visual_spec.get("gradient_opacity", 0.55) * 255)
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    for y in range(height // 2, height):
        alpha = int(opacity * (y - height // 2) / (height // 2))
        gdraw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), gradient).convert("RGB")
    draw = ImageDraw.Draw(img)

    base_size = max(28, min(64, 900 // max(len(message.split()), 1)))
    font = _load_font(
        base_size,
        visual_spec.get("font_family", "Playfair Display"),
        visual_spec.get("fallback_font", "DejaVu Serif"),
    )
    max_width = int(width * 0.85)
    lines = wrap_text(message, font, max_width, draw)
    max_lines = visual_spec.get("max_lines", 6)
    lines = lines[:max_lines]

    line_height = base_size + 12
    total_height = len(lines) * line_height
    y_start = (height - total_height) // 2

    color = visual_spec.get("text_color", "#FFFFFF")
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        y = y_start + i * line_height
        draw.text((x + 2, y + 2), line, font=font, fill="#000000")
        draw.text((x, y), line, font=font, fill=color)

    return img


def resize_cover(img: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))
