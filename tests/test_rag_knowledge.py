"""Tests del knowledge base RAG.

Verifican que (1) todos los archivos del knowledge base existen, (2) están
registrados en ``COLLECTIONS``, (3) el fallback de consulta devuelve contenido
relevante por palabras clave, y (4) los anti-patrones documentados están bien
presentes en el corpus (lo que el LLM va a evitar).
"""

from __future__ import annotations

from pathlib import Path

import pytest


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "rag" / "knowledge"


def test_all_knowledge_files_exist(make_settings):
    make_settings()
    from rag.store import COLLECTIONS

    for files in COLLECTIONS.values():
        for fname in files:
            assert (KNOWLEDGE_DIR / fname).exists(), f"Falta {fname}"


def test_collections_registered(make_settings):
    make_settings()
    from rag.store import COLLECTIONS

    assert {"filosofia", "visual", "brand", "platforms", "guion", "algoritmo"} <= set(
        COLLECTIONS.keys()
    )


def test_fallback_query_returns_relevant_chunk(make_settings):
    make_settings(MOCK_MODE="true")
    from rag.store import get_rag_store

    rag = get_rag_store()
    result = rag.query("filosofia", "resiliencia sub-ángulo")
    assert result
    # Al menos un chunk debería mencionar resiliencia.
    assert any("resiliencia" in chunk.lower() for chunk in result)


def test_fallback_query_guion_collection(make_settings):
    make_settings(MOCK_MODE="true")
    from rag.store import get_rag_store

    rag = get_rag_store()
    result = rag.query("guion", "hook arquitectura plantilla")
    assert result
    assert any("hook" in chunk.lower() for chunk in result)


def test_fallback_query_algoritmo_collection(make_settings):
    make_settings(MOCK_MODE="true")
    from rag.store import get_rag_store

    rag = get_rag_store()
    result = rag.query("algoritmo", "Instagram save share")
    assert result
    assert any("instagram" in chunk.lower() or "save" in chunk.lower() for chunk in result)


@pytest.mark.parametrize(
    "banned",
    [
        "vibras",
        "manifestar",
        "tu mejor versión",
        "todo pasa por algo",
        "cree en ti",
    ],
)
def test_brand_voice_documents_banned_phrases(banned):
    text = (KNOWLEDGE_DIR / "brand-voice.md").read_text(encoding="utf-8").lower()
    assert banned.lower() in text, (
        f"El anti-patrón '{banned}' debe aparecer documentado en brand-voice.md "
        "para que el LLM lo reconozca como prohibido"
    )


def test_filosofia_covers_all_themes():
    text = (KNOWLEDGE_DIR / "filosofia-es.md").read_text(encoding="utf-8").lower()
    for theme in ("resiliencia", "calma", "claridad", "propósito", "gratitud",
                  "presencia", "coraje", "sabiduría"):
        assert theme.lower() in text, f"Tema '{theme}' ausente en filosofia-es.md"


def test_visual_has_palette_per_theme():
    text = (KNOWLEDGE_DIR / "temas-visuales.md").read_text(encoding="utf-8")
    # La tabla de paletas usa HEX. Comprobamos algunos códigos concretos.
    for hex_code in ("#1F2A38", "#2C4A52", "#E6C893", "#3E5641"):
        assert hex_code in text, f"HEX {hex_code} ausente en temas-visuales.md"
