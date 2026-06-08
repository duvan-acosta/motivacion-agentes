"""Tests de configuración y selección de modo."""

from __future__ import annotations


def test_demo_mode_forces_mock(make_settings):
    settings = make_settings(DEMO_MODE="true")
    assert settings.use_mock() is True


def test_mock_mode_without_openai(make_settings):
    settings = make_settings(DEMO_MODE="false", MOCK_MODE="true")
    assert settings.use_mock() is True


def test_real_mode_with_openai(make_settings):
    settings = make_settings(DEMO_MODE="false", MOCK_MODE="true", OPENAI_API_KEY="sk-test")
    assert settings.has_openai() is True
    assert settings.use_mock() is False


def test_no_credentials_by_default(make_settings):
    settings = make_settings()
    assert settings.has_meta() is False
    assert settings.has_tiktok() is False
    assert settings.has_youtube() is False
    assert settings.has_x() is False
    assert settings.has_media_host() is False


def test_media_host_detection(make_settings):
    s3 = make_settings(
        MEDIA_HOST_PROVIDER="s3",
        S3_BUCKET="b",
        AWS_ACCESS_KEY_ID="k",
        AWS_SECRET_ACCESS_KEY="s",
    )
    assert s3.has_media_host() is True

    base = make_settings(MEDIA_HOST_PROVIDER="base_url", MEDIA_PUBLIC_BASE_URL="https://x.test")
    assert base.has_media_host() is True

    none = make_settings(MEDIA_HOST_PROVIDER="none")
    assert none.has_media_host() is False
