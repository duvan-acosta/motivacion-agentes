"""Tests del catálogo de productos, UTM tracking y renderizado de CTA."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from utils.products import (
    Product,
    build_tracked_url,
    cta_context_for_prompt,
    get_active_product,
    get_utm_for_platform,
    render_cta,
)


def test_get_active_product_returns_configured(make_settings):
    make_settings()
    product = get_active_product()
    assert product is not None
    # El default del repo es wallpapers_pack.
    assert product.id == "wallpapers_pack"
    assert product.url.startswith("http")
    assert product.short_name


def test_utm_for_known_platform_uses_alias(make_settings):
    make_settings()
    utm = get_utm_for_platform("instagram", content_id="msg_test_123")
    assert utm["utm_source"] == "ig"
    assert utm["utm_medium"] == "organic"
    assert utm["utm_campaign"] == "daily_post"
    assert utm["utm_content"] == "msg_test_123"


def test_utm_for_unknown_platform_falls_back(make_settings):
    make_settings()
    utm = get_utm_for_platform("threads")
    assert utm["utm_source"] == "threads"


def test_build_tracked_url_appends_utm(make_settings):
    make_settings()
    url = build_tracked_url("https://stan.store/x/p/wallpapers", "tiktok", "msg_abc")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs["utm_source"] == ["tt"]
    assert qs["utm_content"] == ["msg_abc"]
    assert parsed.netloc == "stan.store"


def test_build_tracked_url_preserves_existing_query(make_settings):
    make_settings()
    url = build_tracked_url(
        "https://example.com/p?ref=preview", "youtube", None
    )
    qs = parse_qs(urlparse(url).query)
    assert qs["ref"] == ["preview"]
    assert qs["utm_source"] == ["yt"]


def test_build_tracked_url_handles_empty(make_settings):
    make_settings()
    assert build_tracked_url("", "instagram") == ""


@pytest.mark.parametrize(
    "platform,expected_marker",
    [
        ("instagram", "link en bio"),
        ("facebook", "link en bio"),
        ("tiktok", "link en bio"),
    ],
)
def test_render_cta_meta_platforms_use_bio_link(make_settings, platform, expected_marker):
    make_settings()
    product = get_active_product()
    cta = render_cta(product, platform, content_id="msg_test")
    assert expected_marker in cta.lower()
    # Las plataformas de Meta no llevan URL clicable en el caption.
    assert "http" not in cta


def test_render_cta_twitter_includes_tracked_url(make_settings):
    make_settings()
    product = get_active_product()
    cta = render_cta(product, "twitter", content_id="msg_test")
    assert "http" in cta
    assert "utm_source=x" in cta
    assert "utm_content=msg_test" in cta


def test_render_cta_youtube_includes_url(make_settings):
    make_settings()
    product = get_active_product()
    cta = render_cta(product, "youtube", content_id="msg_test")
    assert "http" in cta
    assert "utm_source=yt" in cta


def test_cta_context_returns_active_product_info(make_settings):
    make_settings()
    ctx = cta_context_for_prompt()
    assert ctx["has_product"] is True
    assert "product_name" in ctx
    assert "cta_style" in ctx


def test_product_from_dict_normalises_fields():
    p = Product.from_dict(
        {
            "id": " test ",
            "name": " Producto ",
            "short_name": "el producto",
            "url": " https://example.com ",
            "description": "desc",
            "price_usd": "9",
            "cta_style": "Question",
        }
    )
    assert p.id == "test"
    assert p.name == "Producto"
    assert p.price_usd == 9.0
    assert p.cta_style == "question"
