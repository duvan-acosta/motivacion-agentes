"""Servicio CRUD sobre el catálogo de productos (config/products.yaml).

Reescribe el archivo preservando su forma (no tocando claves desconocidas
como ``utm``). El YAML es la fuente de verdad para ``utils.products``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from utils.config import PROJECT_ROOT

PRODUCTS_FILE = PROJECT_ROOT / "config" / "products.yaml"

VALID_CTA_STYLES = {"short", "full", "question", "invitation"}
ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _load() -> dict[str, Any]:
    if not PRODUCTS_FILE.exists():
        return {"products": [], "active_product_id": None, "utm": {}}
    with PRODUCTS_FILE.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("products", [])
    data.setdefault("active_product_id", None)
    data.setdefault("utm", {})
    return data


def _save(data: dict[str, Any]) -> None:
    PRODUCTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PRODUCTS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, indent=2)


def list_products() -> dict[str, Any]:
    data = _load()
    return {
        "active_product_id": data.get("active_product_id"),
        "products": data.get("products", []),
    }


def _validate(payload: dict[str, Any], require_id: bool = True) -> tuple[bool, str]:
    if require_id:
        pid = (payload.get("id") or "").strip()
        if not pid:
            return False, "El campo 'id' es obligatorio"
        if not ID_PATTERN.match(pid):
            return False, "El 'id' solo admite minúsculas, números y guion bajo"
    if not (payload.get("name") or "").strip():
        return False, "El campo 'name' es obligatorio"
    url = (payload.get("url") or "").strip()
    if not url or not url.startswith(("http://", "https://")):
        return False, "La URL debe empezar por http:// o https://"
    cta = (payload.get("cta_style") or "short").strip().lower()
    if cta not in VALID_CTA_STYLES:
        return False, f"cta_style inválido. Usa uno de: {sorted(VALID_CTA_STYLES)}"
    return True, ""


def _normalise(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": (payload.get("id") or "").strip(),
        "name": (payload.get("name") or "").strip(),
        "short_name": (payload.get("short_name") or payload.get("name") or "").strip(),
        "url": (payload.get("url") or "").strip(),
        "description": (payload.get("description") or "").strip(),
        "price_usd": float(payload.get("price_usd") or 0),
        "cta_style": (payload.get("cta_style") or "short").strip().lower(),
    }


def upsert_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Crea o actualiza un producto (match por ``id``)."""
    ok, msg = _validate(payload)
    if not ok:
        return {"ok": False, "message": msg}

    data = _load()
    products = data.get("products", []) or []
    normalised = _normalise(payload)
    for i, p in enumerate(products):
        if p.get("id") == normalised["id"]:
            products[i] = normalised
            break
    else:
        products.append(normalised)
    data["products"] = products
    _save(data)
    return {"ok": True, "message": "Producto guardado", "id": normalised["id"]}


def delete_product(product_id: str) -> dict[str, Any]:
    data = _load()
    products = [p for p in (data.get("products") or []) if p.get("id") != product_id]
    if len(products) == len(data.get("products", [])):
        return {"ok": False, "message": f"Producto '{product_id}' no encontrado"}
    data["products"] = products
    if data.get("active_product_id") == product_id:
        data["active_product_id"] = None
    _save(data)
    return {"ok": True, "message": "Producto eliminado", "id": product_id}


def set_active(product_id: str | None) -> dict[str, Any]:
    data = _load()
    if product_id:
        ids = {p.get("id") for p in (data.get("products") or [])}
        if product_id not in ids:
            return {"ok": False, "message": f"Producto '{product_id}' no existe"}
    data["active_product_id"] = product_id
    _save(data)
    return {
        "ok": True,
        "message": "Producto activo actualizado" if product_id else "Sin producto activo",
        "active_product_id": product_id,
    }
