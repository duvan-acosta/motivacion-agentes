"""Servicio de paquetes de contenido."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from utils.config import get_settings


def _parse_package_id(package_id: str) -> tuple[str, str]:
    if "/" in package_id:
        date_part, name = package_id.split("/", 1)
        return date_part, name
    raise ValueError("ID de paquete inválido — use FECHA/nombre")


def resolve_package_path(package_id: str) -> Path:
    date_part, name = _parse_package_id(package_id)
    path = get_settings().queue_path / date_part / name
    if not path.is_dir():
        raise FileNotFoundError(f"Paquete no encontrado: {package_id}")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _find_thumbnail(pkg: Path) -> str | None:
    candidates = [
        pkg / "instagram" / "feed.jpg",
        pkg / "facebook" / "post.jpg",
        pkg / "twitter" / "image.jpg",
        pkg / "youtube" / "thumbnail.jpg",
    ]
    for c in candidates:
        if c.exists():
            return str(c.relative_to(get_settings().project_root)).replace("\\", "/")
    return None


def _package_summary(date_dir: Path, pkg: Path) -> dict[str, Any]:
    status_data = _read_json(pkg / "status.json")
    meta = _read_json(pkg / "source" / "metadata.json")
    manifest = _read_json(pkg / "manifest.json")
    status = status_data.get("status", "unknown")
    package_id = f"{date_dir.name}/{pkg.name}"
    return {
        "id": package_id,
        "date": date_dir.name,
        "name": pkg.name,
        "status": status,
        "theme": meta.get("theme", "-"),
        "generated_at": manifest.get("generated_at") or status_data.get("validated_at"),
        "thumbnail": _find_thumbnail(pkg),
        "platforms": list(status_data.get("platforms", {}).keys()),
    }


def list_packages(limit: int = 100) -> list[dict[str, Any]]:
    base = get_settings().queue_path
    if not base.exists():
        return []

    packages: list[dict[str, Any]] = []
    for date_dir in sorted(base.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for pkg in sorted(date_dir.iterdir(), reverse=True):
            if not pkg.is_dir():
                continue
            packages.append(_package_summary(date_dir, pkg))
            if len(packages) >= limit:
                return packages
    return packages


def get_package_detail(package_id: str) -> dict[str, Any]:
    path = resolve_package_path(package_id)
    status_data = _read_json(path / "status.json")
    meta = _read_json(path / "source" / "metadata.json")
    manifest = _read_json(path / "manifest.json")

    captions: dict[str, str] = {}
    caption_files = {
        "instagram": path / "instagram" / "caption.txt",
        "tiktok": path / "tiktok" / "caption.txt",
        "facebook": path / "facebook" / "caption.txt",
    }
    for platform, fpath in caption_files.items():
        if fpath.exists():
            captions[platform] = fpath.read_text(encoding="utf-8").strip()

    hashtags = ""
    ht = path / "instagram" / "hashtags.txt"
    if ht.exists():
        hashtags = ht.read_text(encoding="utf-8").strip()

    message = ""
    msg = path / "source" / "message.txt"
    if msg.exists():
        message = msg.read_text(encoding="utf-8").strip()

    images: list[dict[str, str]] = []
    for pattern in [
        "instagram/feed.jpg",
        "facebook/post.jpg",
        "twitter/image.jpg",
        "youtube/thumbnail.jpg",
    ]:
        img = path / pattern
        if img.exists():
            rel = str(img.relative_to(get_settings().project_root)).replace("\\", "/")
            images.append({"path": rel, "label": pattern.split("/")[-1]})

    return {
        "id": package_id,
        "name": path.name,
        "path": str(path),
        "status": status_data.get("status", "unknown"),
        "platforms": status_data.get("platforms", {}),
        "theme": meta.get("theme", "-"),
        "message": message,
        "captions": captions,
        "hashtags": hashtags,
        "manifest": manifest,
        "images": images,
        "generated_at": manifest.get("generated_at"),
    }


def count_by_status() -> dict[str, int]:
    counts = {"total": 0, "ready": 0, "pending": 0, "published": 0, "manual": 0, "failed": 0}
    for pkg in list_packages(limit=1000):
        counts["total"] += 1
        st = pkg.get("status", "unknown")
        if st in counts:
            counts[st] += 1
    return counts


def create_package_zip(package_id: str) -> tuple[str, BytesIO]:
    path = resolve_package_path(package_id)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in path.rglob("*"):
            if file.is_file():
                arcname = f"{path.name}/{file.relative_to(path)}"
                zf.write(file, arcname)
    buffer.seek(0)
    return f"{path.name}.zip", buffer
