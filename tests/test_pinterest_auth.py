"""Tests de resolución de credenciales de Pinterest (estático vs refresh)."""

from __future__ import annotations


def test_resolve_static_token(make_settings):
    s = make_settings(PINTEREST_ACCESS_TOKEN="static_tok", PINTEREST_BOARD_ID="b")
    from utils.pinterest_auth import resolve_access_token

    assert resolve_access_token(s) == "static_tok"


def test_resolve_prefers_refresh(make_settings, monkeypatch):
    s = make_settings(
        PINTEREST_BOARD_ID="b",
        PINTEREST_ACCESS_TOKEN="viejo",
        PINTEREST_REFRESH_TOKEN="rt",
        PINTEREST_APP_ID="aid",
        PINTEREST_APP_SECRET="sec",
    )

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "fresco"}

    import utils.pinterest_auth as pa

    monkeypatch.setattr(pa.requests, "post", lambda *a, **k: _Resp())
    assert pa.resolve_access_token(s) == "fresco"


def test_resolve_none_without_credentials(make_settings):
    s = make_settings(PINTEREST_BOARD_ID="b")  # sin token ni refresh
    from utils.pinterest_auth import resolve_access_token

    assert resolve_access_token(s) is None


def test_has_pinterest_modes(make_settings):
    sin = make_settings(PINTEREST_BOARD_ID="b")
    assert sin.has_pinterest() is False

    estatico = make_settings(PINTEREST_BOARD_ID="b", PINTEREST_ACCESS_TOKEN="t")
    assert estatico.has_pinterest() is True

    refresh = make_settings(
        PINTEREST_BOARD_ID="b",
        PINTEREST_REFRESH_TOKEN="rt",
        PINTEREST_APP_ID="a",
        PINTEREST_APP_SECRET="s",
    )
    assert refresh.has_pinterest() is True

    # board_id es obligatorio aunque haya token.
    sin_board = make_settings(PINTEREST_ACCESS_TOKEN="t")
    assert sin_board.has_pinterest() is False


def test_auto_publish_list(make_settings):
    vacio = make_settings()
    assert vacio.auto_publish_list() == []

    uno = make_settings(AUTO_PUBLISH_PLATFORMS="pinterest")
    assert uno.auto_publish_list() == ["pinterest"]

    varios = make_settings(AUTO_PUBLISH_PLATFORMS="Pinterest, instagram ")
    assert varios.auto_publish_list() == ["pinterest", "instagram"]
