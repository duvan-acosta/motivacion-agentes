"""Tests del contenido de modo demo."""

from __future__ import annotations

from utils.demo_mode import demo_tweet, demo_youtube_meta, pick_demo_content

REQUIRED_KEYS = {"theme", "message", "caption", "hashtags", "visual_keywords", "script", "content_id"}


def test_pick_demo_content_has_required_keys():
    content = pick_demo_content()
    assert REQUIRED_KEYS.issubset(content.keys())
    assert isinstance(content["hashtags"], list) and content["hashtags"]


def test_pick_demo_content_respects_theme():
    content = pick_demo_content("calma")
    assert content["theme"] == "calma"


def test_demo_youtube_meta():
    meta = demo_youtube_meta("Un mensaje", "resiliencia")
    assert {"title", "description", "tags"}.issubset(meta.keys())
    assert "resiliencia" in meta["tags"]


def test_demo_tweet_respects_length():
    long_msg = "palabra " * 100
    tweet = demo_tweet(long_msg, "calma")
    assert len(tweet) <= 280
