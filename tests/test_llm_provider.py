"""Tests del soporte de proveedores LLM OpenAI-compatibles (DeepSeek, etc.)."""

from __future__ import annotations


def test_llm_kwargs_openai_native(make_settings):
    s = make_settings(OPENAI_API_KEY="sk-test", OPENAI_BASE_URL="")
    kwargs = s.llm_kwargs()
    assert kwargs["api_key"] == "sk-test"
    assert "base_url" not in kwargs


def test_llm_kwargs_with_custom_base_url(make_settings):
    s = make_settings(
        OPENAI_API_KEY="sk-deepseek",
        OPENAI_BASE_URL="https://api.deepseek.com",
    )
    kwargs = s.llm_kwargs()
    assert kwargs["api_key"] == "sk-deepseek"
    assert kwargs["base_url"] == "https://api.deepseek.com"


def test_llm_kwargs_strips_trailing_slash(make_settings):
    s = make_settings(
        OPENAI_API_KEY="sk-x",
        OPENAI_BASE_URL="https://api.deepseek.com/",
    )
    assert s.llm_kwargs()["base_url"] == "https://api.deepseek.com"


def test_is_native_openai_true_when_no_base_url(make_settings):
    s = make_settings(OPENAI_API_KEY="sk-test", OPENAI_BASE_URL="")
    assert s.is_native_openai() is True


def test_is_native_openai_false_with_custom_endpoint(make_settings):
    s = make_settings(
        OPENAI_API_KEY="sk-x", OPENAI_BASE_URL="https://api.deepseek.com"
    )
    assert s.is_native_openai() is False


def test_is_native_openai_false_without_key(make_settings):
    s = make_settings(OPENAI_API_KEY="", OPENAI_BASE_URL="")
    assert s.is_native_openai() is False


def test_use_mock_false_when_deepseek_key_configured(make_settings):
    """Con key DeepSeek el sistema NO usa mock (la key existe, aunque el
    endpoint sea custom)."""
    s = make_settings(
        OPENAI_API_KEY="sk-deepseek",
        OPENAI_BASE_URL="https://api.deepseek.com",
        MOCK_MODE="true",
    )
    assert s.use_mock() is False


def test_rag_falls_back_to_keywords_with_custom_endpoint(make_settings, tmp_path, monkeypatch):
    """Con DeepSeek, el RAG debe ir por fallback de keywords sin intentar
    llamar a embeddings (DeepSeek no los soporta)."""
    make_settings(
        OPENAI_API_KEY="sk-deepseek",
        OPENAI_BASE_URL="https://api.deepseek.com",
        CHROMA_PERSIST_DIR=str(tmp_path / "chroma"),
    )
    from rag.store import RAGStore

    store = RAGStore()
    embeddings = store._get_embeddings(["texto de prueba"])
    assert embeddings is None  # no debería intentar llamar a OpenAI embeddings
