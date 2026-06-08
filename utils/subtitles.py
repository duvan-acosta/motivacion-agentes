"""Subtítulos sincronizados para Reels/Shorts/TikTok.

El 80% de la audiencia en redes verticales mira sin sonido. Este módulo toma
el audio del TTS y devuelve una lista de cues ``[{text, start, end}, ...]``
para superponer en el video con sincronía real.

Estrategia en cascada:

1. **Whisper API (OpenAI)** — devuelve segmentos con timestamps por palabra.
   Es la mejor calidad. Coste: ≈0.006 USD/minuto, ≈0.003 USD por video.
2. **Estimación por cadencia** — si no hay key o falla, distribuye las frases
   del script asumiendo 2.2 palabras/segundo (la cadencia que documenta
   ``rag/knowledge/guion-video.md``). Suficiente para mantener subtítulos
   en demo y como degradación elegante.

Los cues están agrupados a nivel de frase (no palabra), porque el estilo de
la marca pide overlays de 6-12 palabras visibles 2-4 segundos. Trocear por
palabra produciría un efecto "karaoke" que no encaja con el tono sereno.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from utils.config import get_settings

logger = logging.getLogger(__name__)

# Cadencia documentada en rag/knowledge/guion-video.md (~2.0-2.5 palabras/seg).
WORDS_PER_SECOND = 2.2
# Una cue dura como mínimo 1.2s (lectura cómoda) y como máximo 5s (no aburrir).
MIN_CUE_DURATION = 1.2
MAX_CUE_DURATION = 5.0
# Cada overlay debe ser legible. La marca usa frases cortas (6-12 palabras).
MAX_WORDS_PER_CUE = 12


@dataclass(frozen=True)
class Cue:
    text: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict:
        return {"text": self.text, "start": self.start, "end": self.end}


def _split_into_phrases(script: str) -> list[str]:
    """Divide el script en frases cortas aptas para overlay.

    Respeta saltos de línea existentes (el ``VideoProducerAgent`` ya escribe
    una frase por línea) y, dentro de cada línea, parte por punto/coma/exclama-
    ción para evitar overlays muy largos.
    """
    if not script:
        return []
    raw_lines = [line.strip() for line in script.splitlines() if line.strip()]
    phrases: list[str] = []
    for line in raw_lines:
        parts = re.split(r"(?<=[\.\?\!])\s+|(?<=:)\s+", line)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Si la frase es demasiado larga, partimos por comas.
            if len(part.split()) > MAX_WORDS_PER_CUE:
                sub = [s.strip() for s in part.split(",") if s.strip()]
                phrases.extend(sub if sub else [part])
            else:
                phrases.append(part)
    return phrases


def _estimate_cues_from_phrases(
    phrases: list[str], total_duration: float
) -> list[Cue]:
    """Reparte las frases en el rango [0, total_duration] por número de palabras."""
    if not phrases or total_duration <= 0:
        return []
    word_counts = [max(1, len(p.split())) for p in phrases]
    total_words = sum(word_counts)
    cues: list[Cue] = []
    cursor = 0.0
    for phrase, wc in zip(phrases, word_counts):
        share = (wc / total_words) * total_duration
        duration = max(MIN_CUE_DURATION, min(MAX_CUE_DURATION, share))
        start = cursor
        end = min(total_duration, start + duration)
        cues.append(Cue(text=phrase, start=round(start, 2), end=round(end, 2)))
        cursor = end
        if cursor >= total_duration:
            break
    # Ajuste final: la última cue cierra exactamente en el total.
    if cues and cues[-1].end < total_duration:
        last = cues[-1]
        cues[-1] = Cue(last.text, last.start, total_duration)
    return cues


def _whisper_transcribe(audio_path: Path) -> list[Cue] | None:
    """Llama a Whisper y devuelve cues a nivel de segmento, o ``None`` si falla."""
    settings = get_settings()
    if not settings.has_openai():
        return None
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=settings.openai_api_key)
        with audio_path.open("rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                language="es",
            )
        segments = getattr(resp, "segments", None) or resp.get("segments", [])
        cues: list[Cue] = []
        for seg in segments:
            text = (seg.get("text") if isinstance(seg, dict) else seg.text).strip()
            start = float(seg.get("start") if isinstance(seg, dict) else seg.start)
            end = float(seg.get("end") if isinstance(seg, dict) else seg.end)
            if not text:
                continue
            cues.append(Cue(text=text, start=round(start, 2), end=round(end, 2)))
        return cues or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Whisper transcribe falló, usando estimación: %s", exc)
        return None


def build_cues(
    audio_path: str | Path | None,
    script: str,
    fallback_duration: float | None = None,
) -> list[Cue]:
    """Devuelve los cues sincronizados con el audio.

    - Si ``audio_path`` apunta a un archivo real y hay OpenAI key, intenta
      Whisper.
    - Si falla o no aplica, distribuye ``script`` por cadencia usando
      ``fallback_duration`` o, en su defecto, palabras × 1/WORDS_PER_SECOND.
    """
    phrases = _split_into_phrases(script)
    if not phrases:
        return []

    if audio_path:
        path = Path(audio_path)
        if path.exists() and path.suffix.lower() in {".mp3", ".m4a", ".wav"}:
            cues = _whisper_transcribe(path)
            if cues:
                return cues

    if fallback_duration is None or fallback_duration <= 0:
        total_words = sum(max(1, len(p.split())) for p in phrases)
        fallback_duration = total_words / WORDS_PER_SECOND
    return _estimate_cues_from_phrases(phrases, fallback_duration)


def cues_to_srt(cues: list[Cue]) -> str:
    """Serializa los cues a formato SRT (útil para debug y para futuro export)."""
    def fmt(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int(round((t - int(t)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines: list[str] = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{fmt(cue.start)} --> {fmt(cue.end)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)
