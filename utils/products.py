"""Catálogo de productos y generación de URLs con UTM por plataforma.

Centraliza dos decisiones:
1. ¿Qué producto promueve hoy el sistema? (catálogo + ``active_product_id``).
2. ¿Cómo debe verse la URL que se publica en cada plataforma? (tracking UTM).

El catálogo vive en ``config/products.yaml`` y se recarga en cada llamada para
permitir cambios sin reiniciar (útil cuando un editor humano mueve el producto
activo desde el panel web).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from utils.config import load_yaml


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    short_name: str
    url: str
    description: str
    price_usd: float
    cta_style: str  # short | full | question | invitation

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Product":
        return cls(
            id=str(data.get("id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            short_name=str(data.get("short_name", "")).strip(),
            url=str(data.get("url", "")).strip(),
            description=str(data.get("description", "")).strip(),
            price_usd=float(data.get("price_usd", 0) or 0),
            cta_style=str(data.get("cta_style", "short")).strip().lower(),
        )


def _load_catalog() -> dict[str, Any]:
    return load_yaml("config/products.yaml") or {}


def get_active_product() -> Product | None:
    """Devuelve el producto activo del catálogo, o ``None`` si no hay ninguno."""
    catalog = _load_catalog()
    active_id = catalog.get("active_product_id")
    if not active_id:
        return None
    for raw in catalog.get("products", []) or []:
        if raw.get("id") == active_id:
            product = Product.from_dict(raw)
            return product if product.url and product.id else None
    return None


def get_utm_for_platform(platform: str, content_id: str | None = None) -> dict[str, str]:
    """Devuelve los parámetros UTM aplicables a ``platform``."""
    catalog = _load_catalog()
    utm = catalog.get("utm", {}) or {}
    sources = utm.get("source_by_platform", {}) or {}
    source = sources.get(platform.lower(), platform.lower() or "direct")
    params = {
        "utm_source": source,
        "utm_medium": str(utm.get("medium", "organic")),
        "utm_campaign": str(utm.get("campaign", "daily_post")),
    }
    if content_id:
        params["utm_content"] = content_id
    return params


def build_tracked_url(base_url: str, platform: str, content_id: str | None = None) -> str:
    """Inyecta los UTM en ``base_url`` preservando cualquier query existente."""
    if not base_url:
        return base_url
    parsed = urlparse(base_url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    existing.update(get_utm_for_platform(platform, content_id))
    new_query = urlencode(existing)
    return urlunparse(parsed._replace(query=new_query))


def render_cta(product: Product, platform: str, content_id: str | None = None) -> str:
    """Genera el bloque de CTA a anexar al caption de la plataforma indicada.

    El estilo del CTA varía según ``product.cta_style`` y la plataforma:

    - Instagram / Facebook: CTA con la frase completa y la indicación
      «link en bio» (Meta penaliza URLs en el caption).
    - TikTok: igual a Meta, con «link en bio».
    - YouTube: URL clicable porque la descripción la admite.
    - Twitter/X: URL clicable y mensaje muy breve.
    """
    tracked = build_tracked_url(product.url, platform, content_id)
    platform = platform.lower()
    short = product.short_name or product.name
    style = product.cta_style or "short"

    if style == "question":
        body = (
            f"¿Quieres llevar esto contigo todo el mes? Tengo {short} "
            "preparado para acompañarte."
        )
    elif style == "invitation":
        body = (
            f"Si esto te resonó, dejé {short} en mi tienda para llevarlo "
            "donde lo necesites."
        )
    elif style == "full":
        body = (
            f"Te dejo {short}: {product.description}"
        )
    else:  # short
        body = f"Encuentra {short} en mi tienda."

    if platform in {"instagram", "facebook", "tiktok"}:
        return f"{body} (link en bio)"
    if platform == "twitter":
        return f"{body} {tracked}"
    if platform == "youtube":
        return f"{body}\n\n{tracked}"
    return f"{body} {tracked}"


def cta_context_for_prompt() -> dict[str, Any]:
    """Pequeño bloque de contexto que el ``ContentCreatorAgent`` inyecta en su
    prompt para que el LLM cierre el caption alineado con el producto activo.
    """
    product = get_active_product()
    if not product:
        return {"has_product": False}
    return {
        "has_product": True,
        "product_name": product.name,
        "product_short_name": product.short_name,
        "product_description": product.description,
        "cta_style": product.cta_style,
    }
