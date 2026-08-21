"""Publicador de TikTok via navegador — sube videos como humano."""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

from publishing.browser.base import BaseBrowserPublisher

logger = logging.getLogger(__name__)

TT_URL = "https://www.tiktok.com"
TT_UPLOAD_URL = "https://www.tiktok.com/upload"


class TikTokBrowserPublisher(BaseBrowserPublisher):
    PLATFORM = "tiktok"

    def __init__(self) -> None:
        super().__init__()
        self.username = os.getenv("TIKTOK_USERNAME", "")
        self.password = os.getenv("TIKTOK_PASSWORD", "")

    # ── Login ──────────────────────────────────────────────────────────────────

    def _is_logged_in(self, page: Any) -> bool:
        try:
            # Perfil visible = logueado
            page.wait_for_selector("[data-e2e='profile-icon']", timeout=4000)
            return True
        except PWTimeout:
            return False

    def _login(self, page: Any, context: Any = None) -> bool:
        logger.info("[tiktok] Iniciando sesion como %s", self._google_email() or self.username)

        # ── Intento 1: Clic DIRECTO en 'Continuar con Google' en TikTok ──────
        # NO pre-navegar a Google — TikTok abre el popup OAuth desde su propio login
        if context:
            page.goto(f"{TT_URL}/login", wait_until="domcontentloaded")
            self.human.think(2.5, 4.0)
            self._screenshot(page, "login_loaded")

            def _click_google_btn_tiktok(btn_el: Any) -> bool:
                """Clic en el botón Google de TikTok, maneja popup y retorna True si login OK."""
                logger.info("[tiktok] Boton Google encontrado — clic directo")
                self.human.before_click(page)
                try:
                    with context.expect_page(timeout=6000) as popup_info:
                        btn_el.click()
                    popup = popup_info.value
                    popup.wait_for_load_state("domcontentloaded")
                    self.human.think(2.0, 3.5)
                    logger.info("[tiktok] Popup Google: %s", popup.url)
                    ok = self._handle_google_popup(popup)
                    if ok:
                        try:
                            popup.wait_for_event("close", timeout=20000)
                        except Exception:
                            pass
                        self.human.think(3.0, 6.0)
                        self._screenshot(page, "login_after_google")
                        return "/login" not in page.url
                except PWTimeout:
                    logger.info("[tiktok] Google OAuth redirect inline")
                    self.human.think(4.0, 7.0)
                    self._screenshot(page, "login_after_google")
                    return "/login" not in page.url
                except Exception as exc:
                    logger.warning("[tiktok] Google popup fallo: %s", exc)
                return False

            # Enfoque A: Playwright get_by_text (más robusto — funciona en div/span/button)
            google_btn_attempted = False
            google_oauth_blocked = False
            for gtext in ["Continuar con Google", "Continue with Google"]:
                try:
                    loc = page.get_by_text(gtext, exact=True).first
                    loc.wait_for(state="visible", timeout=5000)
                    google_btn_attempted = True
                    result = _click_google_btn_tiktok(loc)
                    if result:
                        return True  # login Google exitoso
                    # result=False → Google bloqueó el login por CDP
                    google_oauth_blocked = True
                    break
                except Exception:
                    continue

            if not google_btn_attempted:
                # Enfoque B: wait_for_selector CSS (fallback)
                css_sels = [
                    "[data-e2e='google-login-button']",
                    "span:has-text('Continuar con Google')",
                    "div:has-text('Continuar con Google')",
                    "div[aria-label*='Google']",
                ]
                for sel in css_sels:
                    try:
                        el = page.wait_for_selector(sel, timeout=5000, state="visible")
                        if el:
                            google_btn_attempted = True
                            result = _click_google_btn_tiktok(el)
                            if result:
                                return True
                            google_oauth_blocked = True
                            break
                    except Exception:
                        continue

            if not google_btn_attempted:
                logger.warning("[tiktok] Boton 'Continuar con Google' no encontrado")
            elif google_oauth_blocked:
                logger.error(
                    "[tiktok] Google bloquea login via CDP. "
                    "Ejecuta: python setup_sessions.py tiktok  — para login manual"
                )

            # Google OAuth no disponible o falló — probar email/password

        # ── Intento 2: email + password (fallback) ─────────────────────────────
        if not self.username or not self.password:
            logger.error("[tiktok] Sin credenciales — configura TIKTOK_USERNAME/TIKTOK_PASSWORD")
            return False

        logger.info("[tiktok] Fallback a email/password")
        page.goto(f"{TT_URL}/login/phone-or-email/email", wait_until="domcontentloaded")
        self.human.think(2.0, 4.0)

        try:
            page.wait_for_selector("input[name='username']", timeout=10000)
            page.locator("input[name='username']").fill(self.username)
            self.human.pause(0.6, 1.2)
            page.locator("input[type='password']").fill(self.password)
            self.human.pause(0.8, 1.8)
            self._screenshot(page, "login_filled")

            for sel in ["button[data-e2e='login-button']", "button[type='submit']"]:
                try:
                    btn = page.wait_for_selector(sel, timeout=4000)
                    if btn and btn.is_enabled():
                        btn.click()
                        self.human.think(5.0, 8.0)
                        break
                except Exception:
                    continue
            else:
                page.keyboard.press("Enter")
                self.human.think(5.0, 8.0)

            self._screenshot(page, "login_after_submit")
            if "/login" not in page.url:
                logger.info("[tiktok] Login email/pass exitoso")
                return True

            logger.warning("[tiktok] Login fallido — URL: %s", page.url)
            return False

        except Exception as exc:
            self._screenshot(page, "login_error")
            logger.error("[tiktok] Error en login: %s", exc)
            return False

    # ── Publicar video ─────────────────────────────────────────────────────────

    def _publish_video(self, page: Any, video_path: Path, caption: str) -> bool:
        logger.info("[tiktok] Publicando video: %s", video_path.name)

        # TikTok upload usa interfaz desktop
        page.goto(TT_UPLOAD_URL, wait_until="networkidle")
        self.human.think(3.0, 5.0)

        try:
            # Input de archivo (puede estar en iframe)
            iframe = None
            for frame in page.frames:
                try:
                    file_input = frame.wait_for_selector(
                        "input[type='file'][accept*='video']", timeout=3000, state="attached"
                    )
                    if file_input:
                        iframe = frame
                        break
                except PWTimeout:
                    continue

            if iframe:
                file_input = iframe.wait_for_selector(
                    "input[type='file'][accept*='video']", timeout=5000, state="attached"
                )
            else:
                file_input = page.wait_for_selector(
                    "input[type='file'][accept*='video']", timeout=10000, state="attached"
                )

            file_input.set_input_files(str(video_path))
            logger.info("[tiktok] Video subido, esperando procesamiento...")
            self.human.think(8.0, 15.0)  # Procesamiento de video

            # Caption — buscar en main page o iframe
            target = iframe or page
            caption_trimmed = caption[:2200]

            for sel in [
                "[data-e2e='caption-input']",
                "div[contenteditable='true']",
                "div[data-e2e='photo-title-input']",
            ]:
                try:
                    cap_el = target.wait_for_selector(sel, timeout=5000)
                    if cap_el:
                        cap_el.click()
                        self.human.pause(0.3, 0.7)
                        for char in caption_trimmed:
                            target.keyboard.type(char)
                            import time; time.sleep(0.04)
                        logger.debug("[tiktok] Caption escrito")
                        break
                except PWTimeout:
                    continue

            self.human.think(1.5, 3.0)

            # Botón de publicar
            for btn_text in ["Post", "Publicar", "Submit"]:
                try:
                    post_btn = target.get_by_role("button", name=btn_text)
                    if post_btn.is_visible(timeout=3000):
                        self.human.move_mouse_randomly(page)
                        self.human.pause(0.8, 1.5)
                        post_btn.click()
                        self.human.think(4.0, 7.0)
                        self._screenshot(page, "tiktok_published")
                        logger.info("[tiktok] Video publicado exitosamente")
                        return True
                except Exception:
                    continue

            self._screenshot(page, "tiktok_no_post_btn")
            logger.warning("[tiktok] No se encontró el botón de publicar")
            return False

        except Exception as exc:
            self._screenshot(page, "tiktok_error")
            logger.error("[tiktok] Error publicando: %s", exc)
            return False

    # ── Engagement post-publicación ────────────────────────────────────────────

    def _warm_engagement(self, page: Any) -> None:
        """Ver videos del FYP para mejorar el score de la cuenta."""
        try:
            logger.info("[tiktok] Engagement post-publicación (FYP warming)...")
            page.goto(TT_URL, wait_until="domcontentloaded")
            self.human.think(3.0, 5.0)

            # Ver 4-6 videos completos del FYP — señala que la cuenta está activa
            for i in range(random.randint(4, 6)):
                try:
                    # Esperar que cargue video y "verlo" por su duración
                    self.human.think(8.0, 18.0)  # simular ver un video
                    # Scroll para siguiente video
                    page.mouse.wheel(0, 800)
                    self.human.pause(1.0, 2.0)

                    # Dar like a 1 de cada 3 videos aproximadamente
                    if random.random() < 0.35:
                        like_btn = page.query_selector("[data-e2e='like-icon']")
                        if like_btn:
                            like_btn.click()
                            self.human.pause(0.8, 1.5)
                except Exception:
                    continue

            logger.info("[tiktok] Engagement FYP completado")
        except Exception as exc:
            logger.debug("[tiktok] Engagement falló (no crítico): %s", exc)

    # ── Entrada principal ──────────────────────────────────────────────────────

    def publish(self, package_path: Path) -> dict[str, Any]:
        video_path = package_path / "tiktok" / "video.mp4"
        caption_file = package_path / "tiktok" / "caption.txt"

        if not video_path.exists() or video_path.stat().st_size < 100_000:
            return {"platform": "tiktok", "success": False, "error": "Video no disponible"}

        caption = caption_file.read_text(encoding="utf-8").strip() if caption_file.exists() else ""
        results: dict[str, Any] = {"platform": "tiktok", "success": False}

        with sync_playwright() as pw:
            # headless=False requerido para Google OAuth — headless Chromium es bloqueado por Google
            browser, context = self._build_context(pw, headless=False, mobile=False)
            page = context.new_page()

            try:
                page.goto(TT_URL, wait_until="domcontentloaded")
                self.human.think(2.0, 3.5)

                if not self._is_logged_in(page):
                    if not self._login(page, context):
                        results["error"] = "Login fallido — configura GOOGLE_EMAIL o TIKTOK_USERNAME/TIKTOK_PASSWORD"
                        return results
                    self._save_cookies(context)

                results["success"] = self._publish_video(page, video_path, caption)

                if results["success"]:
                    self._warm_engagement(page)

                self._save_cookies(context)

            except Exception as exc:
                self._screenshot(page, "unexpected_error")
                results["error"] = str(exc)
                logger.error("[tiktok] Error inesperado: %s", exc)
            finally:
                context.close()
                browser.close()

        return results
