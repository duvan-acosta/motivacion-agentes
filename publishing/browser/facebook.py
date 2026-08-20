"""Publicador de Facebook via navegador — publica en página de empresa."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

from publishing.browser.base import BaseBrowserPublisher

logger = logging.getLogger(__name__)

FB_URL = "https://www.facebook.com"


class FacebookBrowserPublisher(BaseBrowserPublisher):
    PLATFORM = "facebook"

    def __init__(self) -> None:
        super().__init__()
        self.email = os.getenv("FB_EMAIL", "")
        self.password = os.getenv("FB_PASSWORD", "")
        self.page_name = os.getenv("FB_PAGE_NAME", "")  # slug de la página

    # ── Login ──────────────────────────────────────────────────────────────────

    def _is_logged_in(self, page: Any) -> bool:
        try:
            page.wait_for_selector("[aria-label='Your profile']", timeout=4000)
            return True
        except PWTimeout:
            try:
                page.wait_for_selector("div[aria-label='Facebook']", timeout=3000)
                return True
            except PWTimeout:
                return False

    def _login(self, page: Any, context: Any = None) -> bool:
        if not self.email or not self.password:
            logger.error("[facebook] Configura FB_EMAIL y FB_PASSWORD en .env")
            return False

        logger.info("[facebook] Iniciando sesión como %s", self.email)
        self.human.navigate(page, FB_URL, wait="networkidle")
        self.human.think(2.5, 4.5)

        # Aceptar cookies si aparece
        for sel in ["button[data-cookiebanner='accept_button']",
                    "[data-testid='cookie-policy-manage-dialog-accept-button']"]:
            try:
                btn = page.wait_for_selector(sel, timeout=3000)
                if btn:
                    self.human.before_click(page)
                    btn.click()
                    self.human.pause()
            except PWTimeout:
                pass

        try:
            page.wait_for_selector("input[name='email']", timeout=10000)
            self.human.hesitate()
            page.locator("input[name='email']").fill(self.email)
            self.human.pause(0.8, 1.8)

            page.locator("input[name='pass'], input[type='password']").first.fill(self.password)
            self.human.pause(1.0, 2.0)
            self._screenshot(page, "login_filled")

            try:
                self.human.before_click(page)
                page.locator("input[type='submit'], button[type='submit']").first.click()
            except Exception:
                page.keyboard.press("Enter")
            self.human.think(5.0, 9.0)
            self._screenshot(page, "login_after_submit")

            if "login" not in page.url:
                logger.info("[facebook] Login exitoso")
                return True

            logger.warning("[facebook] Login fallido — URL: %s", page.url)
            return False

        except Exception as exc:
            logger.error("[facebook] Error en login: %s", exc)
            return False

    # ── Publicar en página ─────────────────────────────────────────────────────

    def _publish_post(self, page: Any, image_path: Path, caption: str) -> bool:
        logger.info("[facebook] Publicando en: %s", self.page_name or "perfil personal")

        # Ir al feed personal o a la página
        target_url = f"{FB_URL}/{self.page_name}" if self.page_name else FB_URL
        page.goto(target_url, wait_until="domcontentloaded")
        self.human.think(2.0, 4.0)
        self._screenshot(page, "fb_feed_loaded")

        # Si la página no existe, caer al feed personal
        if "no está disponible" in (page.content() or "") or "isn't available" in (page.content() or ""):
            logger.warning("[facebook] Página no encontrada, usando feed personal")
            page.goto(FB_URL, wait_until="domcontentloaded")
            self.human.think(2.0, 3.5)

        try:
            # Cerrar cualquier modal/diálogo que bloquee
            for esc_text in ["Ahora no", "Not Now", "Cerrar", "Close"]:
                try:
                    btn = page.get_by_role("button", name=esc_text)
                    if btn.is_visible(timeout=1500):
                        btn.click()
                        self.human.pause(0.5, 1.0)
                except Exception:
                    pass
            page.keyboard.press("Escape")
            self.human.pause(0.5, 1.0)

            # Clic en la caja "¿Qué estás pensando, [Nombre]?"
            clicked_create = False
            for sel in [
                "div[aria-label*='pensando']",
                "div[aria-label*='mind']",
                "div[role='button'][aria-label*='post']",
                "span:has-text('¿Qué estás pensando')",
                "span:has-text(\"What's on your mind\")",
            ]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=4000):
                        el.click()
                        clicked_create = True
                        self.human.think(1.5, 3.0)
                        self._screenshot(page, "fb_create_clicked")
                        break
                except Exception:
                    continue

            if not clicked_create:
                # Fallback: buscar el primer div clickeable del área de crear post
                try:
                    post_area = page.locator("[role='main'] [role='button']").first
                    post_area.click()
                    self.human.think(1.5, 3.0)
                except Exception:
                    pass

            # Escribir texto en el editor del modal
            written = False
            for sel in [
                "div[contenteditable='true'][aria-label*='post']",
                "div[contenteditable='true'][role='textbox']",
                "div[data-lexical-editor='true']",
                "div[contenteditable='true']",
            ]:
                try:
                    editor = page.locator(sel).first
                    if editor.is_visible(timeout=5000):
                        editor.click()
                        self.human.pause(0.5, 1.0)
                        import time
                        for char in caption[:63000]:
                            page.keyboard.type(char)
                            time.sleep(0.04)
                        written = True
                        self._screenshot(page, "fb_text_written")
                        break
                except Exception:
                    continue

            if not written:
                logger.warning("[facebook] No se pudo escribir el texto")
                self._screenshot(page, "fb_no_editor")
                return False

            self.human.think(1.0, 2.0)

            # Adjuntar imagen
            if image_path.exists():
                try:
                    for sel in ["[aria-label='Foto/video']", "[aria-label='Photo/video']", "[aria-label*='Foto']"]:
                        try:
                            btn = page.locator(sel).first
                            if btn.is_visible(timeout=3000):
                                btn.click()
                                self.human.think(1.0, 2.0)
                                file_input = page.wait_for_selector("input[type='file']", timeout=5000, state="attached")
                                file_input.set_input_files(str(image_path))
                                self.human.think(3.0, 5.0)
                                break
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug("[facebook] No se pudo adjuntar imagen: %s", e)

            # Publicar
            for btn_text in ["Publicar", "Post", "Share now", "Compartir"]:
                try:
                    post_btn = page.get_by_role("button", name=btn_text)
                    if post_btn.is_visible(timeout=3000):
                        self.human.move_mouse_randomly(page)
                        self.human.pause(0.8, 1.5)
                        post_btn.click()
                        self.human.think(5.0, 8.0)
                        self._screenshot(page, "fb_published")
                        logger.info("[facebook] Post publicado exitosamente")
                        return True
                except Exception:
                    continue

            self._screenshot(page, "fb_no_post_btn")
            logger.warning("[facebook] No se encontró el botón Publicar")
            return False

        except Exception as exc:
            self._screenshot(page, "fb_error")
            logger.error("[facebook] Error publicando: %s", exc)
            return False

    # ── Entrada principal ──────────────────────────────────────────────────────

    def publish(self, package_path: Path) -> dict[str, Any]:
        image_path = package_path / "facebook" / "post.jpg"
        caption_file = package_path / "facebook" / "caption.txt"

        caption = caption_file.read_text(encoding="utf-8").strip() if caption_file.exists() else ""
        results: dict[str, Any] = {"platform": "facebook", "success": False}

        with sync_playwright() as pw:
            browser, context = self._build_context(pw, headless=True, mobile=False)
            page = context.new_page()

            try:
                page.goto(FB_URL, wait_until="domcontentloaded")
                self.human.think(2.0, 3.5)

                if not self._is_logged_in(page):
                    if not self._login(page):
                        results["error"] = "Login fallido — configura FB_EMAIL y FB_PASSWORD"
                        return results
                    self._save_cookies(context)

                results["success"] = self._publish_post(page, image_path, caption)
                self._save_cookies(context)

            except Exception as exc:
                self._screenshot(page, "unexpected_error")
                results["error"] = str(exc)
                logger.error("[facebook] Error inesperado: %s", exc)
            finally:
                context.close()
                browser.close()

        return results
