"""RAG vector store con ChromaDB."""

from __future__ import annotations

import logging
from typing import Any

from utils.config import ensure_dir, get_settings

logger = logging.getLogger(__name__)

COLLECTIONS = {
    "filosofia": ["filosofia-es.md"],
    "visual": ["temas-visuales.md"],
    "brand": ["brand-voice.md"],
    "platforms": ["platforms-specs.yaml"],
    "guion": ["guion-video.md"],
    "algoritmo": ["algoritmo-plataformas.md"],
}


class RAGStore:
    """Almacén vectorial local con fallback sin embeddings."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self._collections: dict[str, Any] = {}
        self._file_cache: dict[str, str] = {}
        self._load_file_cache()

    def _load_file_cache(self) -> None:
        knowledge = self.settings.knowledge_path
        for files in COLLECTIONS.values():
            for name in files:
                path = knowledge / name
                if path.exists():
                    self._file_cache[name] = path.read_text(encoding="utf-8")

    def _get_client(self):
        if self._client is not None:
            return self._client
        if self.settings.use_mock():
            return None
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            ensure_dir(self.settings.chroma_path)
            self._client = chromadb.PersistentClient(
                path=str(self.settings.chroma_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            return self._client
        except Exception as exc:
            logger.warning("ChromaDB no disponible, usando fallback: %s", exc)
            return None

    def _chunk_text(self, text: str, chunk_size: int = 500) -> list[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < chunk_size:
                current = f"{current}\n\n{para}".strip()
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        return chunks or [text[:chunk_size]]

    def _get_embeddings(self, texts: list[str]) -> list[list[float]] | None:
        if self.settings.use_mock():
            return None
        # Proveedores OpenAI-compatibles (DeepSeek, Groq) no ofrecen embeddings.
        if not self.settings.is_native_openai():
            return None
        try:
            from langchain_openai import OpenAIEmbeddings

            embedder = OpenAIEmbeddings(
                model=self.settings.openai_embedding_model,
                api_key=self.settings.openai_api_key,
            )
            return embedder.embed_documents(texts)
        except Exception as exc:
            logger.warning("Embeddings no disponibles: %s", exc)
            return None

    def initialize(self) -> None:
        client = self._get_client()
        if client is None:
            logger.info("RAG en modo fallback (sin ChromaDB/embeddings)")
            return

        for collection_name, files in COLLECTIONS.items():
            collection = client.get_or_create_collection(name=collection_name)
            if collection.count() > 0:
                self._collections[collection_name] = collection
                continue

            ids: list[str] = []
            documents: list[str] = []
            for fname in files:
                content = self._file_cache.get(fname, "")
                if not content:
                    continue
                for i, chunk in enumerate(self._chunk_text(content)):
                    ids.append(f"{fname}_{i}")
                    documents.append(chunk)

            if not documents:
                continue

            embeddings = self._get_embeddings(documents)
            if embeddings:
                collection.add(ids=ids, documents=documents, embeddings=embeddings)
            else:
                collection.add(ids=ids, documents=documents)

            self._collections[collection_name] = collection
            logger.info("Colección RAG '%s' indexada (%d chunks)", collection_name, len(documents))

    def query(self, collection_name: str, query_text: str, n_results: int = 4) -> list[str]:
        client = self._get_client()
        if client is None or collection_name not in COLLECTIONS:
            return self._fallback_query(collection_name, query_text, n_results)

        collection = client.get_or_create_collection(name=collection_name)
        if collection.count() == 0:
            self.initialize()
            collection = client.get_or_create_collection(name=collection_name)

        if self.settings.use_mock() or not self.settings.is_native_openai():
            return self._fallback_query(collection_name, query_text, n_results)

        try:
            from langchain_openai import OpenAIEmbeddings

            embedder = OpenAIEmbeddings(
                model=self.settings.openai_embedding_model,
                api_key=self.settings.openai_api_key,
            )
            q_emb = embedder.embed_query(query_text)
            results = collection.query(query_embeddings=[q_emb], n_results=n_results)
            docs = results.get("documents", [[]])[0]
            return list(docs)
        except Exception as exc:
            logger.warning("Query RAG falló, fallback: %s", exc)
            return self._fallback_query(collection_name, query_text, n_results)

    def _fallback_query(self, collection_name: str, query_text: str, n_results: int) -> list[str]:
        files = COLLECTIONS.get(collection_name, [])
        chunks: list[str] = []
        for fname in files:
            content = self._file_cache.get(fname, "")
            chunks.extend(self._chunk_text(content))
        if not chunks:
            return []
        query_words = set(query_text.lower().split())
        scored = []
        for chunk in chunks:
            words = set(chunk.lower().split())
            score = len(query_words & words)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:n_results]]


_store: RAGStore | None = None


def get_rag_store() -> RAGStore:
    global _store
    if _store is None:
        _store = RAGStore()
        _store.initialize()
    return _store
