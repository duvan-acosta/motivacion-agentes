"""Tests del CRUD de productos vía web.services.product_service.

Se aísla el archivo YAML monkey-patcheando ``PRODUCTS_FILE`` a un tmp.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_catalog(tmp_path, monkeypatch):
    """Reapunta PRODUCTS_FILE a un YAML temporal con un producto base."""
    fpath = tmp_path / "products.yaml"
    fpath.write_text(
        yaml.safe_dump(
            {
                "products": [
                    {
                        "id": "wallpapers_pack",
                        "name": "Wallpapers",
                        "short_name": "los wallpapers",
                        "url": "https://example.com/w",
                        "description": "30 fondos",
                        "price_usd": 7,
                        "cta_style": "invitation",
                    }
                ],
                "active_product_id": "wallpapers_pack",
                "utm": {"medium": "organic", "campaign": "daily_post"},
            }
        ),
        encoding="utf-8",
    )
    from web.services import product_service

    monkeypatch.setattr(product_service, "PRODUCTS_FILE", fpath)
    return fpath


def test_list_returns_catalog(temp_catalog):
    from web.services import product_service

    data = product_service.list_products()
    assert data["active_product_id"] == "wallpapers_pack"
    assert len(data["products"]) == 1


def test_upsert_creates_new_product(temp_catalog):
    from web.services import product_service

    res = product_service.upsert_product({
        "id": "journal_30dias",
        "name": "Journal",
        "short_name": "el journal",
        "url": "https://example.com/j",
        "description": "PDF",
        "price_usd": 12,
        "cta_style": "question",
    })
    assert res["ok"] is True
    products = product_service.list_products()["products"]
    assert any(p["id"] == "journal_30dias" for p in products)


def test_upsert_updates_existing_product(temp_catalog):
    from web.services import product_service

    res = product_service.upsert_product({
        "id": "wallpapers_pack",
        "name": "Wallpapers v2",
        "short_name": "los wallpapers",
        "url": "https://example.com/w2",
        "description": "Renombrado",
        "price_usd": 9,
        "cta_style": "invitation",
    })
    assert res["ok"] is True
    products = product_service.list_products()["products"]
    wp = next(p for p in products if p["id"] == "wallpapers_pack")
    assert wp["name"] == "Wallpapers v2"
    assert wp["price_usd"] == 9


def test_upsert_rejects_invalid_url(temp_catalog):
    from web.services import product_service

    res = product_service.upsert_product({
        "id": "bad", "name": "X", "url": "no-es-url", "cta_style": "short",
    })
    assert res["ok"] is False
    assert "URL" in res["message"]


def test_upsert_rejects_invalid_id(temp_catalog):
    from web.services import product_service

    res = product_service.upsert_product({
        "id": "ID con espacios", "name": "X", "url": "https://x.test",
    })
    assert res["ok"] is False


def test_upsert_rejects_invalid_cta_style(temp_catalog):
    from web.services import product_service

    res = product_service.upsert_product({
        "id": "x", "name": "X", "url": "https://x.test", "cta_style": "shouting",
    })
    assert res["ok"] is False


def test_delete_removes_product_and_clears_active(temp_catalog):
    from web.services import product_service

    res = product_service.delete_product("wallpapers_pack")
    assert res["ok"] is True
    data = product_service.list_products()
    assert data["products"] == []
    assert data["active_product_id"] is None


def test_delete_unknown_returns_error(temp_catalog):
    from web.services import product_service

    res = product_service.delete_product("ghost")
    assert res["ok"] is False


def test_set_active_unknown_id_fails(temp_catalog):
    from web.services import product_service

    res = product_service.set_active("does_not_exist")
    assert res["ok"] is False


def test_set_active_none_clears(temp_catalog):
    from web.services import product_service

    res = product_service.set_active(None)
    assert res["ok"] is True
    assert product_service.list_products()["active_product_id"] is None


def test_save_preserves_utm_block(temp_catalog):
    from web.services import product_service

    product_service.upsert_product({
        "id": "new_one", "name": "N", "url": "https://x.test", "cta_style": "short",
    })
    raw = yaml.safe_load(Path(temp_catalog).read_text(encoding="utf-8"))
    assert raw.get("utm", {}).get("medium") == "organic"
