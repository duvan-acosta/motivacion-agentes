"""Test end-to-end del workflow en modo demo (sin APIs).

Requiere langgraph y Pillow. El nodo de video puede fallar sin ffmpeg/moviepy;
el workflow está diseñado para capturar ese error y continuar, así que aquí solo
verificamos que el paquete se genera y el contenido demo fluye.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("PIL")


def test_run_generation_demo_creates_package(make_settings):
    make_settings(DEMO_MODE="true")
    from graph.workflow import run_generation

    result = run_generation("resiliencia")

    assert result.get("theme") == "resiliencia"
    assert result.get("message")
    package_path = result.get("package_path")
    assert package_path

    from pathlib import Path

    pkg = Path(package_path)
    assert pkg.exists()
    assert (pkg / "status.json").exists()
    assert (pkg / "source" / "message.txt").exists()

    status = json.loads((pkg / "status.json").read_text(encoding="utf-8"))
    assert status["status"] in {"ready", "pending"}
