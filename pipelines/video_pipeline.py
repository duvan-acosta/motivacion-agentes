"""Pipeline de video: TTS + Pexels + MoviePy/FFmpeg."""

from __future__ import annotations

import logging
import subprocess
import wave
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

from utils.config import ensure_dir, get_settings
from utils.media import create_gradient_background, _load_font

logger = logging.getLogger(__name__)


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

        if self.settings.has_openai():
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

            phrases = [p.strip() for p in script.split("\n") if p.strip()]
            if not phrases:
                phrases = [script[:80]]

            clips = [video]
            seg = duration / len(phrases)
            for i, phrase in enumerate(phrases):
                try:
                    txt = (
                        TextClip(phrase, fontsize=48, color="white", font="Arial-Bold", method="caption", size=(900, None))
                        .set_position(("center", 1400))
                        .set_start(i * seg)
                        .set_duration(seg)
                    )
                    clips.append(txt)
                except Exception:
                    pass

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

    def _compose_fallback(
        self, audio_path: str | None, script: str, theme: str, message: str, out_path: Path
    ) -> None:
        frame_path = self.output_dir / "frame.jpg"
        bg = create_gradient_background(1080, 1920, theme)
        draw = ImageDraw.Draw(bg)
        font = _load_font(48, "Playfair Display", "DejaVu Serif")
        lines = [line.strip() for line in script.split("\n") if line.strip()][:6]
        y = 800
        for line in lines:
            draw.text((80, y), line[:60], font=font, fill="#FFFFFF")
            y += 70
        bg.save(frame_path, "JPEG", quality=90)

        duration = 25.0
        if audio_path and audio_path.endswith(".wav"):
            try:
                with wave.open(audio_path, "r") as wf:
                    duration = max(20, min(40, wf.getnframes() / wf.getframerate()))
            except Exception:
                pass

        if self._compose_with_moviepy_image(frame_path, audio_path, duration, out_path):
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

    def _compose_with_moviepy_image(
        self, frame_path: Path, audio_path: str | None, duration: float, out_path: Path
    ) -> bool:
        try:
            from moviepy.editor import AudioFileClip, ImageClip

            clip = ImageClip(str(frame_path)).set_duration(duration).resize((1080, 1920))
            if audio_path and Path(audio_path).exists():
                audio = AudioFileClip(audio_path).subclip(0, min(duration, 40))
                clip = clip.set_audio(audio)
            clip.write_videofile(
                str(out_path),
                fps=30,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None,
            )
            clip.close()
            return out_path.exists() and out_path.stat().st_size > 0
        except Exception as exc:
            logger.warning("MoviePy image fallback falló: %s", exc)
            return False
