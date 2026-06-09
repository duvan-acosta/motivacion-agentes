"""Utilidades de medios."""

from __future__ import annotations

import logging
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from utils.config import ensure_dir, get_settings

logger = logging.getLogger(__name__)

def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) != 6:
        return (40, 40, 50)
    return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


# Paletas alineadas con rag/knowledge/temas-visuales.md.
# Gradiente: (sombra → dominante), de arriba a abajo.
THEME_GRADIENTS_HEX: dict[str, tuple[str, str]] = {
    "resiliencia": ("#0B1117", "#1F2A38"),
    "calma": ("#10202A", "#2C4A52"),
    "claridad": ("#3B2F1F", "#E6C893"),
    "propósito": ("#1A2519", "#3E5641"),
    "proposito": ("#1A2519", "#3E5641"),
    "gratitud": ("#5C3A28", "#C57B57"),
    "presencia": ("#13151B", "#2A2D34"),
    "coraje": ("#1A0C13", "#3C1F2B"),
    "sabiduría": ("#0A0E1A", "#1A2238"),
    "sabiduria": ("#0A0E1A", "#1A2238"),
}

THEME_GRADIENTS = {k: (_hex_to_rgb(s), _hex_to_rgb(d)) for k, (s, d) in THEME_GRADIENTS_HEX.items()}


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


def render_wallpaper_overlay(
    background: Image.Image,
    message: str,
    visual_spec: dict,
    brand_name: str = "Mental Equilibrio",
) -> Image.Image:
    """Overlay específico para wallpaper móvil 4K vertical (2160×3840).

    Distinto al ``render_text_overlay`` porque:
    - Tipografía proporcional al lienzo (96-130 px).
    - Wrap más estrecho (~1500 px) para mantener look editorial.
    - Texto entre y=1400 y y=2600 (safe zone: fuera del notch superior
      y del home indicator inferior de iOS).
    - Pie de marca discreto cerca del borde inferior.
    - Gradiente más sutil (opacity 0.35) para no ahogar la imagen base.
    """
    img = background.copy()
    width, height = img.size

    # Gradiente sutil de oscurecimiento solo en el tercio central para legibilidad.
    opacity = int(visual_spec.get("gradient_opacity", 0.55) * 0.6 * 255)
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    band_top = int(height * 0.30)
    band_bottom = int(height * 0.72)
    for y in range(band_top, band_bottom):
        # Curva tipo bell: máximo en el centro, 0 en los bordes.
        progress = (y - band_top) / max(1, band_bottom - band_top)
        alpha = int(opacity * (1 - abs(2 * progress - 1)))
        gdraw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), gradient).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Tipografía mensaje principal — proporcional al alto del lienzo.
    word_count = max(1, len(message.split()))
    base_size = max(72, min(140, int(2400 / word_count)))
    font = _load_font(
        base_size,
        visual_spec.get("font_family", "Playfair Display"),
        visual_spec.get("fallback_font", "DejaVu Serif"),
    )

    max_width = int(width * 0.78)  # ~1685 px, deja márgenes generosos
    lines = wrap_text(message, font, max_width, draw)
    max_lines = visual_spec.get("max_lines", 6)
    lines = lines[:max_lines]

    line_height = int(base_size * 1.25)
    total_height = len(lines) * line_height
    y_start = (height - total_height) // 2  # centro vertical, dentro de safe zone

    color = visual_spec.get("text_color", "#FFFFFF")
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        y = y_start + i * line_height
        # Sombra suave para legibilidad sobre cualquier fondo.
        draw.text((x + 4, y + 4), line, font=font, fill="#000000")
        draw.text((x, y), line, font=font, fill=color)

    # Pie de marca discreto en la zona inferior segura (fuera del home indicator).
    brand_font = _load_font(58, "Inter", "DejaVu Sans")
    brand_bbox = draw.textbbox((0, 0), brand_name, font=brand_font)
    brand_w = brand_bbox[2] - brand_bbox[0]
    brand_x = (width - brand_w) // 2
    brand_y = height - 380  # safe zone para iOS home indicator
    draw.text((brand_x + 2, brand_y + 2), brand_name, font=brand_font, fill="#000000")
    draw.text((brand_x, brand_y), brand_name, font=brand_font, fill="#E0E0E0")

    return img


def resize_cover(img: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))
