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
    """Carga una fuente por nombre buscando en paths estándar.

    Soporta los nombres principales que usa la marca: ``Lora`` (humanista
    serif moderna, instalada vía ``fonts-lora`` en el contenedor),
    ``DejaVu Serif``, ``DejaVu Sans``, ``Inter``, ``Playfair Display``.
    """
    n = font_name.replace(" ", "")
    fb = fallback.replace(" ", "")
    candidates = [
        # Linux — paths instalados por apt en Debian Bookworm
        f"/usr/share/fonts/truetype/vollkorn/{n}-Bold.ttf",
        f"/usr/share/fonts/truetype/vollkorn/{n}-Regular.ttf",
        f"/usr/share/fonts/truetype/cabin/{n}-Bold.ttf",
        f"/usr/share/fonts/truetype/cabin/{n}-Regular.ttf",
        f"/usr/share/fonts/truetype/{n.lower()}/{n}-Bold.ttf",
        f"/usr/share/fonts/truetype/{n.lower()}/{n}-Regular.ttf",
        # Vollkorn explícito (serif moderna humanista, fuente principal de marca)
        "/usr/share/fonts/truetype/vollkorn/Vollkorn-Bold.ttf",
        "/usr/share/fonts/truetype/vollkorn/Vollkorn-Regular.ttf",
        # Cabin (humanist sans para pie de marca / soporte) — en opentype/
        "/usr/share/fonts/opentype/cabin/Cabin-SemiBold.otf",
        "/usr/share/fonts/opentype/cabin/Cabin-Regular.otf",
        f"/usr/share/fonts/opentype/cabin/{n}-SemiBold.otf",
        f"/usr/share/fonts/opentype/cabin/{n}-Regular.otf",
        # Windows
        f"C:/Windows/Fonts/{n}.ttf",
        f"C:/Windows/Fonts/{n}-Bold.ttf",
        f"C:/Windows/Fonts/{fb}.ttf",
        # Fallbacks universales
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
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
    brand_name: str = "Mental Equilibrio",
) -> Image.Image:
    """Overlay para formatos de red social (1080×1080 feed, 1200×675 X,
    1280×720 YouTube thumb).

    Mismo enfoque adaptativo que render_wallpaper_overlay:
    - Caja semi-transparente con opacidad según luminance del fondo.
    - Vollkorn (serif moderna humanista) sobre crema #FAF3E7.
    - Stroke negro 2px para legibilidad redundante.
    - Pie de marca discreto y adaptativo.
    Sin el gradiente "abajo→arriba" del render anterior (era poco editorial
    y no resolvía contraste sobre fondos claros).
    """
    img = background.copy().convert("RGBA")
    width, height = img.size
    measure_draw = ImageDraw.Draw(img)

    # Tipografía adaptativa al tamaño del lienzo.
    # En 1080 cuadrado, ~48-72 px; en 1200×675, ~44-64 px (lienzo más bajo).
    word_count = max(1, len(message.split()))
    canvas_factor = min(width, height) / 1080
    base_size = max(36, min(72, int(900 * canvas_factor / word_count)))
    base_size = int(base_size * 1.15)  # leve subida para más impacto en feed
    font = _load_font(
        base_size,
        visual_spec.get("font_family", "Vollkorn"),
        visual_spec.get("fallback_font", "DejaVu Serif"),
    )

    max_width = int(width * 0.82)
    lines = wrap_text(message, font, max_width, measure_draw)
    max_lines = visual_spec.get("max_lines", 6)
    lines = lines[:max_lines]

    line_height = int(base_size * 1.22)
    total_height = len(lines) * line_height
    y_start = max(40, (height - total_height) // 2)

    # Calcular bbox global del texto.
    positions: list[tuple[str, int, int]] = []
    text_x_min, text_x_max = width, 0
    for i, line in enumerate(lines):
        bbox = measure_draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        y = y_start + i * line_height
        positions.append((line, x, y))
        text_x_min = min(text_x_min, x)
        text_x_max = max(text_x_max, x + text_w)
    text_y_max = y_start + total_height

    # Caja semi-transparente con opacidad adaptativa.
    pad_x, pad_y = int(width * 0.04), int(height * 0.03)
    box_left = max(20, text_x_min - pad_x)
    box_top = max(20, y_start - pad_y)
    box_right = min(width - 20, text_x_max + pad_x)
    box_bottom = min(height - 20, text_y_max + pad_y)

    text_region = img.convert("L").crop((box_left, box_top, box_right, box_bottom))
    pixel_data = list(text_region.getdata())
    avg_luminance = sum(pixel_data) / max(1, len(pixel_data))
    if avg_luminance > 150:
        box_alpha = 140
    elif avg_luminance > 80:
        box_alpha = 100
    else:
        box_alpha = 60

    box_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(box_layer)
    box_draw.rectangle(
        [box_left, box_top, box_right, box_bottom],
        fill=(0, 0, 0, box_alpha),
    )
    img = Image.alpha_composite(img, box_layer)
    draw = ImageDraw.Draw(img)

    # Texto crema cálido con stroke negro 2px.
    color = visual_spec.get("text_color", "#FAF3E7")
    for line, x, y in positions:
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), line, font=font, fill="#000000")
        draw.text((x, y), line, font=font, fill=color)

    # Pie de marca discreto (proporcional al lienzo) si hay espacio.
    if height >= 600:
        brand_size = max(18, int(min(width, height) * 0.025))
        brand_font = _load_font(brand_size, "Cabin", "DejaVu Sans")
        brand_bbox = draw.textbbox((0, 0), brand_name, font=brand_font)
        brand_w = brand_bbox[2] - brand_bbox[0]
        brand_x = (width - brand_w) // 2
        brand_y = height - int(brand_size * 2.2)
        brand_region = img.convert("L").crop(
            (brand_x - 10, brand_y - 5, brand_x + brand_w + 10, brand_y + brand_size + 5)
        )
        brand_data = list(brand_region.getdata())
        brand_lum = sum(brand_data) / max(1, len(brand_data))
        brand_color = "#1A1A1A" if brand_lum > 150 else "#E0E0E0"
        brand_stroke = "#FFFFFF" if brand_lum > 150 else "#000000"
        draw.text((brand_x + 1, brand_y + 1), brand_name, font=brand_font, fill=brand_stroke)
        draw.text((brand_x, brand_y), brand_name, font=brand_font, fill=brand_color)

    return img.convert("RGB")


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
    img = background.copy().convert("RGBA")
    width, height = img.size
    measure_draw = ImageDraw.Draw(img)

    # Tipografía mensaje principal — proporcional al alto del lienzo.
    # +30% vs versión anterior (76→94, 140→182) para look más impactante en móvil.
    word_count = max(1, len(message.split()))
    base_size = max(94, min(182, int(3120 / word_count)))
    font = _load_font(
        base_size,
        visual_spec.get("font_family", "Vollkorn"),  # serif humanista, distintiva
        visual_spec.get("fallback_font", "DejaVu Serif"),
    )

    max_width = int(width * 0.78)  # ~1685 px, deja márgenes generosos
    lines = wrap_text(message, font, max_width, measure_draw)
    max_lines = visual_spec.get("max_lines", 6)
    lines = lines[:max_lines]

    line_height = int(base_size * 1.25)
    total_height = len(lines) * line_height
    y_start = (height - total_height) // 2  # centro vertical, dentro de safe zone

    # Calcular el bbox global del bloque de texto + posiciones individuales.
    positions: list[tuple[str, int, int]] = []
    text_x_min, text_x_max = width, 0
    for i, line in enumerate(lines):
        bbox = measure_draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        y = y_start + i * line_height
        positions.append((line, x, y))
        text_x_min = min(text_x_min, x)
        text_x_max = max(text_x_max, x + text_w)
    text_y_min = y_start
    text_y_max = y_start + total_height

    # Padding generoso para la caja.
    pad_x, pad_y = 70, 50
    box_left = max(40, text_x_min - pad_x)
    box_top = max(40, text_y_min - pad_y)
    box_right = min(width - 40, text_x_max + pad_x)
    box_bottom = min(height - 40, text_y_max + pad_y)

    # Análisis del brillo del fondo en la zona del texto (luminance media).
    # Permite adaptar la opacidad de la caja: fondo claro → caja más oscura.
    text_region = img.convert("L").crop((box_left, box_top, box_right, box_bottom))
    pixel_data = list(text_region.getdata())
    avg_luminance = sum(pixel_data) / max(1, len(pixel_data))  # 0 negro · 255 blanco
    # Opacidad sutil: fondo claro → alpha 140; medio → 100; oscuro → 60.
    # Bajada vs versión anterior para no ahogar la foto.
    if avg_luminance > 150:
        box_alpha = 140
    elif avg_luminance > 80:
        box_alpha = 100
    else:
        box_alpha = 60

    # Rectángulo recto (sin bordes redondeados, look más editorial directo).
    box_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(box_layer)
    box_draw.rectangle(
        [box_left, box_top, box_right, box_bottom],
        fill=(0, 0, 0, box_alpha),
    )
    img = Image.alpha_composite(img, box_layer)
    draw = ImageDraw.Draw(img)

    # Texto en blanco crema cálido (no blanco puro) con stroke negro ligero.
    color = visual_spec.get("text_color", "#FAF3E7")
    for line, x, y in positions:
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), line, font=font, fill="#000000")
        draw.text((x, y), line, font=font, fill=color)

    # Pie de marca discreto en la zona inferior segura (fuera del home indicator).
    brand_font = _load_font(58, "Cabin", "DejaVu Sans")
    brand_bbox = draw.textbbox((0, 0), brand_name, font=brand_font)
    brand_w = brand_bbox[2] - brand_bbox[0]
    brand_x = (width - brand_w) // 2
    brand_y = height - 380  # safe zone para iOS home indicator
    # Mismo análisis para el pie de marca, en su zona específica.
    brand_region = img.convert("L").crop(
        (brand_x - 20, brand_y - 10, brand_x + brand_w + 20, brand_y + 70)
    )
    brand_data = list(brand_region.getdata())
    brand_lum = sum(brand_data) / max(1, len(brand_data))
    if brand_lum > 150:
        brand_color = "#1A1A1A"  # texto oscuro sobre fondo claro
        brand_stroke = "#FFFFFF"
    else:
        brand_color = "#E0E0E0"
        brand_stroke = "#000000"
    draw.text((brand_x + 2, brand_y + 2), brand_name, font=brand_font, fill=brand_stroke)
    draw.text((brand_x, brand_y), brand_name, font=brand_font, fill=brand_color)

    return img.convert("RGB")


def resize_cover(img: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))
