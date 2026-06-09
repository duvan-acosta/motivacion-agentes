"""Pipeline de video: TTS + Pexels + MoviePy/FFmpeg."""

from __future__ import annotations

import logging
import subprocess
import wave
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

# Compatibilidad MoviePy 1.x ↔ Pillow ≥10: Pillow eliminó Image.ANTIALIAS pero
# MoviePy 1.x todavía lo usa en .resize(). Restauramos el alias antes de que
# moviepy se importe en cualquier parte del pipeline.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]

from utils.config import ensure_dir, get_settings
from utils.media import create_gradient_background, _load_font
from utils.subtitles import build_cues, cues_to_srt

logger = logging.getLogger(__name__)

# Estilo del overlay de subtítulos (alineado con rag/knowledge/guion-video.md).
SUBTITLE_FONT_SIZE = 46
SUBTITLE_MAX_LINE_WIDTH = 900  # px sobre lienzo 1080×1920
SUBTITLE_Y_POSITION = 1100  # safe zone central-baja (entre 900 y 1500)
SUBTITLE_BOX_OPACITY = 0.40
SUBTITLE_FADE_SECONDS = 0.2


class VideoPipeline:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.settings = get_settings()
        self.output_dir = output_dir or ensure_dir(self.settings.project_root / "tmp" / "video")

    def generate(
        self,
        script: str,
        theme: str,
        message: str,
        video_keywords: list[str] | None = None,
    ) -> str:
        audio_path = self._generate_tts(script)
        video_bg = self._fetch_pexels_video(video_keywords or [theme])
        out_path = self.output_dir / "reel_master.mp4"

        if video_bg and audio_path:
            self._compose_with_moviepy(video_bg, audio_path, script, out_path, theme)
        else:
            self._compose_fallback(audio_path, script, theme, message, out_path)

        return str(out_path)

    def _generate_tts(self, script: str) -> str | None:
        out = self.output_dir / "narration.mp3"
        if self.settings.demo_mode or self.settings.use_mock():
            return self._generate_silent_wav(script, out.with_suffix(".wav"))

        if self.settings.tts_provider == "elevenlabs" and self.settings.elevenlabs_api_key:
            return self._tts_elevenlabs(script, out)

        # OpenAI TTS solo está disponible con el endpoint nativo; proveedores
        # compatibles (DeepSeek, Groq) no lo ofrecen — caemos al silent WAV.
        if self.settings.is_native_openai():
            return self._tts_openai(script, out)

        return self._generate_silent_wav(script, out.with_suffix(".wav"))

    def _tts_openai(self, script: str, out: Path) -> str | None:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.audio.speech.create(
                model=self.settings.openai_tts_model,
                voice=self.settings.openai_tts_voice,
                input=script.replace("\n", " "),
            )
            response.stream_to_file(str(out))
            return str(out)
        except Exception as exc:
            logger.warning("OpenAI TTS falló: %s", exc)
            return self._generate_silent_wav(script, out.with_suffix(".wav"))

    def _tts_elevenlabs(self, script: str, out: Path) -> str | None:
        try:
            from elevenlabs import ElevenLabs

            client = ElevenLabs(api_key=self.settings.elevenlabs_api_key)
            voice_id = self.settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"
            audio = client.generate(text=script.replace("\n", " "), voice=voice_id)
            out.write_bytes(audio)
            return str(out)
        except Exception as exc:
            logger.warning("ElevenLabs TTS falló: %s", exc)
            return self._generate_silent_wav(script, out.with_suffix(".wav"))

    def _generate_silent_wav(self, script: str, out: Path) -> str:
        words = len(script.split())
        duration = max(20, min(40, words * 0.4))
        sample_rate = 44100
        n_frames = int(sample_rate * duration)
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * n_frames)
        return str(out)

    def _fetch_pexels_video(self, keywords: list[str]) -> str | None:
        if not self.settings.has_pexels() or self.settings.demo_mode:
            return None
        query = " ".join(keywords[:2]) or "nature vertical"
        headers = {"Authorization": self.settings.pexels_api_key}
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                params={"query": query, "per_page": 3, "orientation": "portrait"},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            if not videos:
                return None
            files = videos[0].get("video_files", [])
            hd = next((f for f in files if f.get("height", 0) >= 720), files[0] if files else None)
            if not hd:
                return None
            local = self.output_dir / "bg_video.mp4"
            vresp = requests.get(hd["link"], timeout=120)
            vresp.raise_for_status()
            local.write_bytes(vresp.content)
            return str(local)
        except Exception as exc:
            logger.warning("Pexels video falló: %s", exc)
            return None

    def _compose_with_moviepy(
        self, video_bg: str, audio_path: str, script: str, out_path: Path, theme: str
    ) -> None:
        try:
            from moviepy.editor import AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip

            video = VideoFileClip(video_bg).resize((1080, 1920))
            audio = AudioFileClip(audio_path)
            duration = min(max(audio.duration, 20), 40)
            video = video.subclip(0, min(video.duration, duration)).loop(duration=duration)
            video = video.set_audio(audio.subclip(0, duration))

            cues = build_cues(audio_path, script, fallback_duration=duration)
            if not cues:
                cues = build_cues(None, script or "", fallback_duration=duration)
            self._write_srt(cues, out_path)

            clips = [video]
            for cue in cues:
                cue_clip = self._make_subtitle_clip(cue.text, cue.start, cue.duration, duration)
                if cue_clip is not None:
                    clips.append(cue_clip)

            final = CompositeVideoClip(clips).set_duration(duration)
            final.write_videofile(
                str(out_path),
                fps=30,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None,
            )
            video.close()
            audio.close()
        except Exception as exc:
            logger.warning("MoviePy falló, usando fallback FFmpeg: %s", exc)
            self._compose_fallback(audio_path, script, theme, script[:80], out_path)

    def _render_subtitle_png(self, text: str) -> Image.Image:
        """Renderiza un overlay PIL con caja semi-transparente + texto blanco.

        Devuelve una imagen RGBA del ancho del lienzo (1080) — alto justo para el
        texto + padding. No depende de ImageMagick.
        """
        font = _load_font(SUBTITLE_FONT_SIZE, "DejaVu Sans", "DejaVu Sans")
        # Wrap manual hasta SUBTITLE_MAX_LINE_WIDTH.
        tmp = Image.new("RGBA", (10, 10))
        draw = ImageDraw.Draw(tmp)
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= SUBTITLE_MAX_LINE_WIDTH:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        line_height = SUBTITLE_FONT_SIZE + 8
        pad_x, pad_y = 28, 18
        text_w = max(
            (draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0])
            for line in lines
        )
        text_h = len(lines) * line_height
        box_w = min(1080 - 60, text_w + 2 * pad_x)
        box_h = text_h + 2 * pad_y

        img = Image.new("RGBA", (1080, box_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        box_x = (1080 - box_w) // 2
        d.rectangle(
            [box_x, 0, box_x + box_w, box_h],
            fill=(0, 0, 0, int(SUBTITLE_BOX_OPACITY * 255)),
        )
        # Texto blanco con sombra negra suave para legibilidad extra.
        y = pad_y
        for line in lines:
            bbox = d.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            x = (1080 - line_w) // 2
            d.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 220))
            d.text((x, y), line, font=font, fill=(255, 255, 255, 255))
            y += line_height
        return img

    def _make_subtitle_clip(
        self, text: str, start: float, duration: float, video_duration: float
    ):
        """Crea un ImageClip con el overlay del subtítulo (PIL, sin ImageMagick)."""
        try:
            import numpy as np
            from moviepy.editor import ImageClip

            duration = max(0.6, min(duration, video_duration - start))
            if duration <= 0:
                return None

            pil_img = self._render_subtitle_png(text)
            clip = (
                ImageClip(np.array(pil_img))
                .set_position(("center", SUBTITLE_Y_POSITION))
                .set_start(start)
                .set_duration(duration)
            )
            if duration > 2 * SUBTITLE_FADE_SECONDS:
                try:
                    clip = clip.crossfadein(SUBTITLE_FADE_SECONDS).crossfadeout(
                        SUBTITLE_FADE_SECONDS
                    )
                except Exception:  # noqa: BLE001
                    pass
            return clip
        except Exception as exc:  # noqa: BLE001
            logger.warning("Overlay de subtítulo falló para '%s...': %s", text[:30], exc)
            return None

    def _write_srt(self, cues, video_path: Path) -> None:
        """Guarda los subtítulos junto al video (útil para upload manual en IG/YT)."""
        if not cues:
            return
        try:
            srt_path = video_path.with_suffix(".srt")
            srt_path.write_text(cues_to_srt(cues), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo escribir SRT: %s", exc)

    def _compose_fallback(
        self, audio_path: str | None, script: str, theme: str, message: str, out_path: Path
    ) -> None:
        # Fondo limpio: los subtítulos sincronizados van encima como overlay.
        # El mensaje principal se reserva para el primer plano (hook visual).
        frame_path = self.output_dir / "frame.jpg"
        bg = create_gradient_background(1080, 1920, theme)
        draw = ImageDraw.Draw(bg)
        hook_font = _load_font(58, "Playfair Display", "DejaVu Serif")
        # Hook visual breve en el tercio superior (mejora retención los primeros 2s).
        hook = (message or "").strip()
        if hook:
            wrapped_lines: list[str] = []
            words = hook.split()
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if draw.textbbox((0, 0), candidate, font=hook_font)[2] <= 900:
                    current = candidate
                else:
                    if current:
                        wrapped_lines.append(current)
                    current = word
            if current:
                wrapped_lines.append(current)
            y = 380
            for line in wrapped_lines[:4]:
                bbox = draw.textbbox((0, 0), line, font=hook_font)
                tx = (1080 - (bbox[2] - bbox[0])) // 2
                draw.text((tx + 2, y + 2), line, font=hook_font, fill="#000000")
                draw.text((tx, y), line, font=hook_font, fill="#FFFFFF")
                y += 70
        bg.save(frame_path, "JPEG", quality=90)

        duration = 25.0
        if audio_path and audio_path.endswith(".wav"):
            try:
                with wave.open(audio_path, "r") as wf:
                    duration = max(20, min(40, wf.getnframes() / wf.getframerate()))
            except Exception:
                pass

        if self._compose_with_moviepy_image(
            frame_path, audio_path, duration, out_path, script=script
        ):
            return

        audio_input = audio_path or str(self.output_dir / "narration.wav")
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(frame_path),
            "-i", audio_input,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest",
            "-t", str(int(duration)),
            "-r", "30",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("FFmpeg no disponible: %s", exc)
            raise RuntimeError("No se pudo generar video (MoviePy/FFmpeg)") from exc
        # En esta ruta no se anima el overlay, pero sí dejamos el .srt al lado
        # del video para que se pueda subir manualmente en IG/YT/TikTok.
        cues = build_cues(audio_path, script, fallback_duration=duration)
        self._write_srt(cues, out_path)

    def _compose_with_moviepy_image(
        self,
        frame_path: Path,
        audio_path: str | None,
        duration: float,
        out_path: Path,
        script: str = "",
    ) -> bool:
        try:
            from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip

            base = ImageClip(str(frame_path)).set_duration(duration).resize((1080, 1920))
            if audio_path and Path(audio_path).exists():
                audio = AudioFileClip(audio_path).subclip(0, min(duration, 40))
                base = base.set_audio(audio)

            cues = build_cues(audio_path, script or "", fallback_duration=duration)
            self._write_srt(cues, out_path)

            clips = [base]
            for cue in cues:
                cue_clip = self._make_subtitle_clip(cue.text, cue.start, cue.duration, duration)
                if cue_clip is not None:
                    clips.append(cue_clip)

            final = (
                CompositeVideoClip(clips).set_duration(duration) if len(clips) > 1 else base
            )
            final.write_videofile(
                str(out_path),
                fps=30,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None,
            )
            final.close()
            return out_path.exists() and out_path.stat().st_size > 0
        except Exception as exc:
            logger.warning("MoviePy image fallback falló: %s", exc)
            return False
