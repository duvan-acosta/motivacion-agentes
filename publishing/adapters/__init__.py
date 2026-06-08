"""Adaptadores por plataforma."""

from publishing.adapters.meta_instagram import MetaInstagramAdapter
from publishing.adapters.tiktok import TikTokAdapter
from publishing.adapters.twitter import TwitterAdapter
from publishing.adapters.youtube import YouTubeAdapter

__all__ = [
    "MetaInstagramAdapter",
    "TikTokAdapter",
    "YouTubeAdapter",
    "TwitterAdapter",
]
