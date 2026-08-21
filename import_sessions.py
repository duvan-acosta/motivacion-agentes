"""
import_sessions.py — Recoge los archivos de cookies descargados por la extensión Chrome.

La extensión descarga archivos me_session_<plataforma>.json a la carpeta Descargas.
Este script los mueve a data/sessions/ con el nombre correcto.

Uso:
    python import_sessions.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SESSIONS_DIR = Path("data/sessions")
GOOGLE_DOMAINS = {".google.com", "accounts.google.com", ".googleapis.com", ".youtube.com"}

VALID_PLATFORMS = {"google", "youtube", "tiktok", "instagram", "twitter", "facebook"}


def find_downloads_dir() -> Path:
    candidates = [
        Path.home() / "Downloads",
        Path.home() / "Descargas",
        Path("C:/Users") / Path.home().name / "Downloads",
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path.home()


def import_file(src: Path) -> str:
    """Importa un archivo me_session_<plataforma>.json. Devuelve nombre de plataforma."""
    platform = src.stem.replace("me_session_", "")
    if platform not in VALID_PLATFORMS:
        return ""

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        cookies = json.loads(src.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  ERROR leyendo {src.name}: {exc}")
        return ""

    # Guardar sesión de la plataforma
    out = SESSIONS_DIR / f"{platform}_session.json"
    out.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [{platform}] {len(cookies)} cookies -> {out}")

    # Compartir cookies Google entre plataformas
    g_cookies = [c for c in cookies if any(d in c.get("domain", "") for d in GOOGLE_DOMAINS)]
    if g_cookies:
        g_file = SESSIONS_DIR / "google_session.json"
        existing: list = []
        if g_file.exists():
            try:
                existing = json.loads(g_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        g_keys = {(c["name"], c.get("domain", "")) for c in g_cookies}
        merged = g_cookies + [c for c in existing if (c["name"], c.get("domain", "")) not in g_keys]
        g_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [google_session] {len(g_cookies)} cookies Google -> {g_file}")

    return platform


def main() -> None:
    downloads = find_downloads_dir()
    files = sorted(downloads.glob("me_session_*.json"))

    print("\n" + "="*46)
    print("  Mental Equilibrio -- Importar Sesiones")
    print("="*46)
    print(f"\nBuscando en: {downloads}")

    if not files:
        print("\nNo se encontraron archivos me_session_*.json en Descargas.")
        print("Asegúrate de haber hecho clic en 'Exportar' con la extensión de Chrome.")
        sys.exit(1)

    print(f"\nEncontrados: {len(files)} archivo(s)\n")
    imported = []
    for f in files:
        platform = import_file(f)
        if platform:
            imported.append(platform)

    if imported:
        print(f"\nImportadas: {', '.join(imported)}")
        print("\nPara produccion Docker:")
        print("  docker cp data/sessions motivacion-agentes-scheduler-1:/app/data/sessions")
    else:
        print("\nNo se importó ninguna sesión. Revisa los archivos.")
        sys.exit(1)


if __name__ == "__main__":
    main()
