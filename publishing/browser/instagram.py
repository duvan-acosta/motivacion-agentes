"""Publicador de Instagram via navegador — sube feed y reels como humano."""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

from publishing.browser.base import BaseBrowserPublisher

logger = logging.getLogger(__name__)

IG_URL = "https://www.instagram.com"
IG_LOGIN_URL = f"{IG_URL}/accounts/login/"


class InstagramBrowserPublisher(BaseBrowserPublisher):
    PLATFORM = "instagram"

    def __init__(self) -> None:
        super().__init__()
        self.username = self._get_env("IG_USERNAME")
        self.password = self._get_env("IG_PASSWORD")

    def _get_env(self, key: str) -> str:
        import os
        return os.getenv(key, "")

    # ── Login ──────────────────────────────────────────────────────────────────

    def _is_logged_in(self, page: Any) -> bool:
        """Verifica por presencia POSITIVA de elementos del feed autenticado."""
        try:
            page.wait_for_selector(
                "svg[aria-label='Home'], "
                "svg[aria-label='Inicio'], "
                "a[href='/'][role='link'], "
                "[aria-label='New post'], "
                "[aria-label='Nueva publicación']",
                timeout=5000,
            )
            logger.info("[instagram] Sesion activa detectada")
            return True
        except PWTimeout:
            return False

    def _dismiss_modals(self, page: Any) -> None:
        """Cierra popups que bloquean la interfaz."""
        for text in ["Not Now", "Ahora no", "Not now", "Allow", "Permitir",
                     "Accept All", "Aceptar todo", "Only allow essential cookies"]:
            try:
                btn = page.get_by_role("button", name=text)
                if btn.is_visible(timeout=2000):
                    btn.click()
                    self.human.pause(0.5, 1.0)
            except Exception:
                pass

    def _login(self, page: Any, context: Any = None) -> bool:
        logger.info("[instagram] Iniciando sesion en %s", IG_LOGIN_URL)
        page.goto(IG_LOGIN_URL, wait_until="domcontentloaded")
        self.human.think(2.0, 3.5)
        self._screenshot(page, "login_loaded")
        self._dismiss_modals(page)

        # ── Intento 1: Google OAuth (cuenta creada con Google) ────────────────
        if context:
            google_btns = [
                "button:has-text('Iniciar sesión con Google')",
                "button:has-text('Log in with Google')",
                "a:has-text('Iniciar sesión con Google')",
                "[aria-label*='Google']",
            ]
            try:
                ok = self._oauth_sign_in_with_google(page, context, google_btns)
                if ok:
                    self.human.think(3.0, 5.0)
                    self._dismiss_modals(page)
                    if self._is_logged_in(page):
                        logger.info("[instagram] Login via Google OAuth exitoso")
                        return True
            except Exception as exc:
                logger.warning("[instagram] Google OAuth fallo, intentando con email/pass: %s", exc)

        # ── Intento 2: email + password directo ───────────────────────────────
        if not self.username or not self.password:
            logger.error("[instagram] Sin credenciales — configura GOOGLE_EMAIL o IG_USERNAME/IG_PASSWORD")
            return False

        # Puede que Google OAuth haya navegado — volver al login
        if IG_LOGIN_URL not in page.url:
            page.goto(IG_LOGIN_URL, wait_until="domcontentloaded")
            self.human.think(2.0, 3.5)

        for sel in ["a:has-text('Iniciar sesión')", "a:has-text('Log in')", "a[href='/accounts/login/']"]:
            try:
                link = page.locator(sel).first
                if link.is_visible(timeout=2000):
                    link.click()
                    self.human.think(1.5, 3.0)
                    break
            except Exception:
                pass

        self._dismiss_modals(page)

        USER_SEL = "input[name='email'], input[name='username'], input[autocomplete='username webauthn']"
        PASS_SEL = "input[name='pass'], input[name='password'], input[type='password']"

        try:
            page.wait_for_selector(USER_SEL, timeout=12000)
            page.locator(USER_SEL).first.fill(self.username)
            self.human.pause(0.6, 1.2)
            page.locator(PASS_SEL).first.fill(self.password)
            self.human.pause(0.8, 1.5)
            self._screenshot(page, "login_filled")

            try:
                page.locator("input[type='submit'], button[type='submit']").first.click()
            except Exception:
                page.keyboard.press("Enter")
            self.human.think(5.0, 8.0)
            self._dismiss_modals(page)
            self._screenshot(page, "login_after_submit")

            if self._is_logged_in(page) or "/accounts/login" not in page.url:
                logger.info("[instagram] Login email/pass exitoso")
                return True

            self._screenshot(page, "login_failed")
            logger.warning("[instagram] Login fallo — URL: %s", page.url)
            return False

        except Exception as exc:
            self._screenshot(page, "login_error")
            logger.error("[instagram] Error en login: %s", exc)
            return False

    # ── Publicar feed (imagen) ────────────────────────────────────────────────

    def _publish_feed(self, page: Any, image_path: Path, caption: str) -> bool:
        logger.info("[instagram] Publicando imagen de feed: %s", image_path.name)

        try:
            self._screenshot(page, "feed_before_create")

            # Buscar el botón "Nueva publicación" en la barra lateral
            clicked = False
            for sel in [
                "[aria-label='New post']",
                "[aria-label='Nueva publicación']",
                "svg[aria-label='New post']",
                "svg[aria-label='Nueva publicación']",
            ]:
                try:
                    btn = page.wait_for_selector(sel, timeout=5000)
                    if btn:
                        btn.click()
                        clicked = True
                        self.human.think(1.5, 3.0)
                        break
                except PWTimeout:
                    continue

            if not clicked:
                # Fallback: input de archivo directamente
                logger.info("[instagram] Boton + no encontrado, buscando input directo")

            self._screenshot(page, "feed_after_create_click")

            # El input de archivo puede estar presente antes o después del click
            file_input = page.wait_for_selector(
                "input[type='file']",
                timeout=12000,
                state="attached",
            )
            file_input.set_input_files(str(image_path))
            logger.info("[instagram] Imagen seleccionada")
            self.human.think(3.0, 5.0)
            self._screenshot(page, "feed_after_file")

            # Wizard: Next → Next → (caption) → Share
            caption_written = False
            for _ in range(5):
                for btn_text in ["Share", "Compartir"]:
                    try:
                        share_btn = page.get_by_role("button", name=btn_text)
                        if share_btn.is_visible(timeout=2000):
                            if not caption_written:
                                self._fill_caption(page, caption)
                                self.human.think(1.0, 2.0)
                                caption_written = True
                            share_btn.click()
                            self.human.think(5.0, 9.0)
                            self._screenshot(page, "feed_published")
                            logger.info("[instagram] Feed publicado")
                            return True
                    except Exception:
                        pass

                for btn_text in ["Next", "Siguiente", "OK"]:
                    try:
                        next_btn = page.get_by_role("button", name=btn_text)
                        if next_btn.is_visible(timeout=2000):
                            next_btn.click()
                            self.human.think(1.5, 3.0)
                            self._screenshot(page, f"feed_wizard_step")
                            break
                    except Exception:
                        continue

            self._screenshot(page, "feed_no_share_btn")
            return False

        except Exception as exc:
            self._screenshot(page, "feed_error")
            logger.error("[instagram] Error publicando feed: %s", exc)
            return False

    # ── Publicar reel (video) ─────────────────────────────────────────────────

    def _publish_reel(self, page: Any, video_path: Path, caption: str) -> bool:
        logger.info("[instagram] Publicando reel: %s", video_path.name)

        page.goto(IG_URL, wait_until="domcontentloaded")
        self.human.think(2.0, 3.5)

        try:
            # Navegar a crear reel
            page.goto(f"{IG_URL}/reels/", wait_until="domcontentloaded")
            self.human.think(1.5, 3.0)

            # Buscar botón de creación
            for sel in [
                "[aria-label='New reel']",
                "svg[aria-label='Nuevo reel']",
                "a[href='/create/select/']",
            ]:
                try:
                    btn = page.wait_for_selector(sel, timeout=4000)
                    if btn:
                        btn.click()
                        break
                except PWTimeout:
                    continue

            self.human.think(2.0, 3.5)

            # Subir video
            file_input = page.wait_for_selector(
                "input[type='file'][accept*='video']",
                timeout=10000,
                state="attached",
            )
            file_input.set_input_files(str(video_path))
            self.human.think(5.0, 9.0)  # Procesamiento de video tarda más

            # Wizard de reel
            for next_text in ["Next", "Siguiente", "Share", "Compartir"]:
                try:
                    next_btn = page.get_by_role("button", name=next_text)
                    if next_btn.is_visible(timeout=4000):
                        if next_text in ("Share", "Compartir"):
                            self._fill_caption(page, caption)
                            self.human.think(1.0, 2.0)
                        next_btn.click()
                        self.human.think(2.0, 4.0)
                except Exception:
                    continue

            self._screenshot(page, "reel_published")
            logger.info("[instagram] Reel publicado exitosamente")
            return True

        except Exception as exc:
            self._screenshot(page, "reel_error")
            logger.error("[instagram] Error publicando reel: %s", exc)
            return False

    # ── Caption ───────────────────────────────────────────────────────────────

    def _fill_caption(self, page: Any, caption: str) -> None:
        """Escribe el caption en el campo de texto con comportamiento humano."""
        for sel in [
            "div[aria-label='Write a caption…']",
            "div[aria-label='Escribe un pie de foto…']",
            "textarea[aria-label='Write a caption…']",
            "div[role='textbox']",
        ]:
            try:
                el = page.wait_for_selector(sel, timeout=5000)
                if el:
                    el.click()
                    time.sleep(0.5)
                    # Escribir carácter por carácter con delays
                    for char in caption[:2200]:  # IG max 2200 chars
                        page.keyboard.type(char)
                        time.sleep(0.04 + (0.12 if char == "\n" else 0))
                    logger.debug("[instagram] Caption escrito (%d chars)", len(caption))
                    return
            except PWTimeout:
                continue
        logger.warning("[instagram] No se encontró el campo de caption")

    # ── Engagement post-publicación (activa el algoritmo) ─────────────────────

    def _warm_engagement(self, page: Any) -> None:
        """Interactúa con el feed para señalar actividad al algoritmo de IG."""
        try:
            logger.info("[instagram] Engagement post-publicación...")
            page.goto(IG_URL, wait_until="domcontentloaded")
            self.human.think(2.0, 4.0)

            # Dar like a 5-8 posts del feed (reciprocidad de algoritmo)
            liked = 0
            for _ in range(12):  # intentar varios posts
                if liked >= random.randint(5, 8):
                    break
                try:
                    # Buscar botón de like que NO esté ya dado
                    like_btn = page.query_selector(
                        "svg[aria-label='Like']:not([aria-label='Unlike'])"
                    )
                    if like_btn:
                        like_btn.click()
                        liked += 1
                        self.human.pause(1.2, 2.8)
                    self.human.scroll(page, 200, 500)
                except Exception:
                    self.human.scroll(page, 200, 400)

            logger.info("[instagram] Engagement: %d likes dados", liked)

            # Explorar hashtag del nicho — señala interés temático al algoritmo
            self.human.think(2.0, 3.5)
            for tag in ["saludmental", "amorpropio", "motivacion"]:
                try:
                    page.goto(f"{IG_URL}/explore/tags/{tag}/", wait_until="domcontentloaded")
                    self.human.think(2.0, 4.0)
                    self.human.scroll(page, 150, 400)
                    # Like al primer post del hashtag
                    like_btn = page.query_selector("svg[aria-label='Like']")
                    if like_btn:
                        like_btn.click()
                        self.human.pause(1.5, 3.0)
                    break  # un hashtag es suficiente
                except Exception:
                    continue

        except Exception as exc:
            logger.debug("[instagram] Engagement falló (no crítico): %s", exc)

    # ── Entrada principal ──────────────────────────────────────────────────────

    def publish(self, package_path: Path) -> dict[str, Any]:
        feed_img = package_path / "instagram" / "feed.jpg"
        reel_vid = package_path / "instagram" / "reel.mp4"
        caption_file = package_path / "instagram" / "caption.txt"
        hashtags_file = package_path / "instagram" / "hashtags.txt"

        caption = ""
        if caption_file.exists():
            caption = caption_file.read_text(encoding="utf-8").strip()
        if hashtags_file.exists():
            caption = f"{caption}\n\n{hashtags_file.read_text(encoding='utf-8').strip()}"

        results: dict[str, Any] = {"platform": "instagram", "feed": False, "reel": False}

        with sync_playwright() as pw:
            # Desktop 1920x1080 — evita que IG lo trate como tablet
            browser, context = self._build_context(pw, headless=True, mobile=False, width=1920, height=1080)
            page = context.new_page()

            try:
                page.goto(IG_URL, wait_until="domcontentloaded")
                self.human.think(2.5, 4.0)

                if not self._is_logged_in(page):
                    if not self._login(page, context):
                        results["error"] = "Login fallido — configura GOOGLE_EMAIL o IG_USERNAME/IG_PASSWORD"
                        return results
                    self._save_cookies(context)
                    # Navegar al home después del login
                    page.goto(IG_URL, wait_until="domcontentloaded")
                    self.human.think(2.0, 3.5)
                    self._dismiss_modals(page)

                # Publicar feed (imagen)
                if feed_img.exists():
                    results["feed"] = self._publish_feed(page, feed_img, caption)
                    self.human.think(3.0, 6.0)

                # Publicar reel (video) — solo si existe y no está vacío
                if reel_vid.exists() and reel_vid.stat().st_size > 100_000:
                    results["reel"] = self._publish_reel(page, reel_vid, caption)

                # Engagement post-publicación para activar el algoritmo
                if results["feed"] or results["reel"]:
                    self._warm_engagement(page)

                # Actualizar sesión
                self._save_cookies(context)
                results["success"] = results["feed"] or results["reel"]

            except Exception as exc:
                self._screenshot(page, "unexpected_error")
                results["error"] = str(exc)
                results["success"] = False
                logger.error("[instagram] Error inesperado: %s", exc)
            finally:
                context.close()
                browser.close()

        return results
