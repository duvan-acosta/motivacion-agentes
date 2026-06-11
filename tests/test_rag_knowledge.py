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
        "mejor versión",
        "todo pasa por algo",
        "cree en ti",
    ],
)
def test_corpus_documents_banned_phrases(banned):
    """El anti-patrón debe aparecer en algún archivo del knowledge (filosofia o
    brand) para que el LLM lo reconozca como prohibido al recibir el contexto.
    """
    corpus = " ".join(
        (KNOWLEDGE_DIR / fname).read_text(encoding="utf-8").lower()
        for fname in ("filosofia-es.md", "brand-voice.md")
    )
    assert banned.lower() in corpus, (
        f"El anti-patrón '{banned}' no aparece en el corpus RAG; el LLM no lo "
        "reconocerá como prohibido"
    )


def _normalize(text: str) -> str:
    """Minúsculas, sin acentos y con '_' como espacio para comparar temas.

    Los temas en brand.yaml usan snake_case (``amor_propio``) y el corpus los
    titula con espacios y acentos (``Amor propio``, ``Límites``).
    """
    import unicodedata

    text = text.replace("_", " ").lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def test_filosofia_covers_all_themes():
    """Cada tema que el DirectorAgent rota (brand.yaml) debe existir en el corpus.

    Leer la lista desde brand.yaml evita que el test se desincronice cuando se
    reorienta la marca (la fuente de verdad es ``themes_rotation``).
    """
    import yaml

    brand = yaml.safe_load((KNOWLEDGE_DIR.parent.parent / "config" / "brand.yaml").read_text(encoding="utf-8"))
    themes = brand.get("content", {}).get("themes_rotation", [])
    assert themes, "themes_rotation vacío en brand.yaml"

    text = _normalize((KNOWLEDGE_DIR / "filosofia-es.md").read_text(encoding="utf-8"))
    for theme in themes:
        assert _normalize(theme) in text, f"Tema '{theme}' ausente en filosofia-es.md"


def test_visual_has_palette_per_theme():
    text = (KNOWLEDGE_DIR / "temas-visuales.md").read_text(encoding="utf-8")
    # La tabla de paletas usa HEX. Comprobamos algunos códigos concretos.
    for hex_code in ("#1F2A38", "#2C4A52", "#E6C893", "#3E5641"):
        assert hex_code in text, f"HEX {hex_code} ausente en temas-visuales.md"
