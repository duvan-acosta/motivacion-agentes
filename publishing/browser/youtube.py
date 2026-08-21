"""Publicador de YouTube via navegador — sube Shorts via YouTube Studio."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

from publishing.browser.base import BaseBrowserPublisher

logger = logging.getLogger(__name__)

YT_STUDIO = "https://studio.youtube.com"
GOOGLE_LOGIN = "https://accounts.google.com"


class YouTubeBrowserPublisher(BaseBrowserPublisher):
    PLATFORM = "youtube"

    def __init__(self) -> None:
        super().__init__()
        self.email = os.getenv("GOOGLE_EMAIL", os.getenv("IG_USERNAME", ""))
        self.password = os.getenv("GOOGLE_PASSWORD", os.getenv("IG_PASSWORD", ""))

    # ── Login Google ───────────────────────────────────────────────────────────

    def _is_logged_in(self, page: Any) -> bool:
        try:
            page.wait_for_selector(
                "[aria-label='Create'], "
                "ytcp-button#create-icon, "
                "button[aria-label*='Create'], "
                "#avatar-btn",
                timeout=5000,
            )
            return True
        except PWTimeout:
            return False

    def _login_google(self, page: Any) -> bool:
        if not self.email or not self.password:
            logger.error("[youtube] Configura GOOGLE_EMAIL y GOOGLE_PASSWORD")
            return False

        logger.info("[youtube] Login Google como %s", self.email)
        page.goto(
            f"{GOOGLE_LOGIN}/signin/v2/identifier?hl=es&continue=https://studio.youtube.com",
            wait_until="domcontentloaded",
        )
        self.human.think(2.0, 4.0)
        self._screenshot(page, "login_loaded")

        try:
            # Email
            page.wait_for_selector(
                "input[type='email'], input[name='identifier']", timeout=12000
            )
            page.locator("input[type='email'], input[name='identifier']").first.fill(self.email)
            self.human.pause(0.6, 1.2)
            self._screenshot(page, "login_email")

            # Next
            for sel in ["#identifierNext", "button:has-text('Siguiente')", "button:has-text('Next')"]:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        self.human.think(2.0, 3.5)
                        break
                except Exception:
                    continue

            # Contraseña
            page.wait_for_selector(
                "input[type='password'], input[name='password']", timeout=10000
            )
            self.human.pause(0.5, 1.0)
            page.locator("input[type='password']").first.fill(self.password)
            self.human.pause(0.8, 1.5)
            self._screenshot(page, "login_password")

            # Sign in
            for sel in ["#passwordNext", "button:has-text('Siguiente')", "button:has-text('Next')"]:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        self.human.think(5.0, 9.0)
                        break
                except Exception:
                    continue

            self._screenshot(page, "login_after_submit")

            # Manejar verificaciones adicionales de Google (2FA, teléfono)
            try:
                # Si pide verificación de teléfono — skip
                for skip_text in ["Ahora no", "Not now", "Skip", "Omitir", "Recordar más tarde"]:
                    try:
                        btn = page.get_by_role("button", name=skip_text)
                        if btn.is_visible(timeout=3000):
                            btn.click()
                            self.human.think(2.0, 3.0)
                    except Exception:
                        pass
            except Exception:
                pass

            # Verificar login exitoso — buscar YouTube Studio
            try:
                page.wait_for_url("*studio.youtube.com*", timeout=15000)
                logger.info("[youtube] Login Google exitoso")
                return True
            except PWTimeout:
                pass

            # Navegar manualmente a Studio
            page.goto(YT_STUDIO, wait_until="domcontentloaded")
            self.human.think(3.0, 5.0)

            if self._is_logged_in(page):
                logger.info("[youtube] Login Google exitoso (navegación manual)")
                return True

            self._screenshot(page, "login_failed")
            logger.warning("[youtube] Login fallido — URL: %s", page.url)
            return False

        except Exception as exc:
            self._screenshot(page, "login_error")
            logger.error("[youtube] Error en login: %s", exc)
            return False

    # ── Subir video ────────────────────────────────────────────────────────────

    def _upload_short(
        self,
        page: Any,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
    ) -> bool:
        logger.info("[youtube] Subiendo Short: %s", video_path.name)

        page.goto(YT_STUDIO, wait_until="domcontentloaded")
        self.human.think(3.0, 5.0)
        self._screenshot(page, "studio_loaded")

        try:
            # Si YouTube pide crear canal primero, hacerlo automáticamente
            for btn_text in ["Crear canal", "Create channel"]:
                try:
                    btn = page.get_by_role("button", name=btn_text).first
                    if btn.is_visible(timeout=3000):
                        logger.info("[youtube] Creando canal de YouTube...")
                        btn.click()
                        self.human.think(4.0, 7.0)
                        self._screenshot(page, "channel_created")
                        logger.info("[youtube] Canal creado")
                        # Recargar Studio tras crear canal
                        page.goto(YT_STUDIO, wait_until="domcontentloaded")
                        self.human.think(3.0, 5.0)
                        break
                except Exception:
                    pass

            # Cerrar modales de bienvenida/onboarding que bloquean la UI
            for btn_text in ["Continuar", "Continue", "Got it", "Entendido", "Dismiss", "OK"]:
                try:
                    btn = page.get_by_role("button", name=btn_text).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        self.human.think(1.0, 2.0)
                        logger.info("[youtube] Modal '%s' cerrado", btn_text)
                        break
                except Exception:
                    pass

            self._screenshot(page, "studio_ready")

            # Botón "Crear" en YouTube Studio → abre menú con "Subir videos"
            crear_clicked = False
            for sel in [
                "#create-icon",
                "ytcp-button#create-icon",
                "[aria-label='Create']",
                "[aria-label='Crear']",
                "button[aria-label*='Crear']",
                "button[aria-label*='Create']",
                # Botón con texto en la barra superior
                "yt-button-shape button",
            ]:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        self.human.think(1.0, 2.0)
                        crear_clicked = True
                        logger.info("[youtube] Boton Crear clicado: %s", sel)
                        break
                except Exception:
                    continue

            # Si no encontró botón Crear, intentar botón directo "Subir videos" en Studio
            if not crear_clicked:
                for text in ["Subir videos", "Upload videos", "Upload"]:
                    try:
                        btn = page.get_by_role("button", name=text).first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            self.human.think(2.0, 3.5)
                            self._screenshot(page, "upload_dialog")
                            crear_clicked = True
                            break
                    except Exception:
                        continue

            # Opción "Subir videos" del menú desplegable (si se abrió menú)
            if crear_clicked:
                for text in ["Subir videos", "Upload videos", "Upload video"]:
                    try:
                        opt = page.get_by_text(text, exact=False).first
                        if opt.is_visible(timeout=3000):
                            opt.click()
                            self.human.think(2.0, 3.5)
                            self._screenshot(page, "upload_dialog")
                            break
                    except Exception:
                        continue

            # Input de archivo
            file_input = page.wait_for_selector(
                "input[type='file']", timeout=12000, state="attached"
            )
            file_input.set_input_files(str(video_path))
            logger.info("[youtube] Archivo seleccionado, esperando procesamiento...")
            self.human.think(8.0, 15.0)
            self._screenshot(page, "upload_processing")

            # Título
            title_sel = (
                "ytcp-mention-textbox[aria-label*='título'], "
                "ytcp-mention-textbox[aria-label*='title'], "
                "div[id='textbox'][aria-label*='title'], "
                "div[id='textbox'][aria-label*='título']"
            )
            try:
                title_box = page.locator(title_sel).first
                title_box.wait_for(state="visible", timeout=10000)
                title_box.click()
                # Seleccionar todo y reemplazar
                page.keyboard.press("Control+a")
                page.keyboard.type(title[:100])
                self.human.pause(0.5, 1.0)
            except Exception as exc:
                logger.warning("[youtube] No se pudo escribir título: %s", exc)

            # Descripción
            desc_sel = (
                "ytcp-mention-textbox[aria-label*='escripción'], "
                "ytcp-mention-textbox[aria-label*='description'], "
                "div#description-container div[id='textbox']"
            )
            try:
                desc_box = page.locator(desc_sel).first
                if desc_box.is_visible(timeout=5000):
                    desc_box.click()
                    self.human.pause(0.3, 0.7)
                    for char in description[:5000]:
                        page.keyboard.type(char)
                        time.sleep(0.03)
            except Exception as exc:
                logger.warning("[youtube] No se pudo escribir descripción: %s", exc)

            self._screenshot(page, "upload_details_filled")

            # Marcar como "No es contenido para niños"
            try:
                no_kids = page.locator(
                    "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT']"
                ).first
                if no_kids.is_visible(timeout=3000):
                    no_kids.click()
                    self.human.pause(0.3, 0.6)
            except Exception:
                pass

            # Next → Next → Next → Publicar (el wizard tiene 3-4 pasos)
            for step in range(4):
                for btn_text in ["Siguiente", "Next"]:
                    try:
                        btn = page.get_by_role("button", name=btn_text)
                        if btn.is_visible(timeout=3000) and btn.is_enabled():
                            btn.click()
                            self.human.think(1.5, 3.0)
                            self._screenshot(page, f"upload_step_{step}")
                            break
                    except Exception:
                        continue

            # Visibilidad: Público
            for text in ["Público", "Public"]:
                try:
                    radio = page.get_by_text(text, exact=True).first
                    if radio.is_visible(timeout=3000):
                        radio.click()
                        self.human.pause(0.5, 1.0)
                        break
                except Exception:
                    continue

            # Publicar / Save
            for btn_text in ["Publicar", "Publish", "Save", "Guardar"]:
                try:
                    btn = page.get_by_role("button", name=btn_text)
                    if btn.is_visible(timeout=3000) and btn.is_enabled():
                        self.human.move_mouse_randomly(page)
                        self.human.pause(0.8, 1.5)
                        btn.click()
                        self.human.think(6.0, 10.0)
                        self._screenshot(page, "upload_published")
                        logger.info("[youtube] Short publicado exitosamente")
                        return True
                except Exception:
                    continue

            self._screenshot(page, "upload_no_publish_btn")
            return False

        except Exception as exc:
            self._screenshot(page, "upload_error")
            logger.error("[youtube] Error subiendo: %s", exc)
            return False

    # ── Entrada principal ──────────────────────────────────────────────────────

    def publish(self, package_path: Path) -> dict[str, Any]:
        video_path = package_path / "youtube" / "short.mp4"
        title_file = package_path / "youtube" / "title.txt"
        desc_file = package_path / "youtube" / "description.txt"
        tags_file = package_path / "youtube" / "tags.txt"

        if not video_path.exists() or video_path.stat().st_size < 50_000:
            return {"platform": "youtube", "success": False, "error": "Video no disponible"}

        title = title_file.read_text(encoding="utf-8").strip() if title_file.exists() else "Mental Equilibrio"
        description = desc_file.read_text(encoding="utf-8").strip() if desc_file.exists() else ""
        tags = tags_file.read_text(encoding="utf-8").strip().split("\n") if tags_file.exists() else []

        results: dict[str, Any] = {"platform": "youtube", "success": False}

        with sync_playwright() as pw:
            # headless=False para login Google — Google bloquea CDP headless en OAuth
            browser, context = self._build_context(pw, headless=False, mobile=False)
            page = context.new_page()

            try:
                page.goto(YT_STUDIO, wait_until="domcontentloaded")
                self.human.think(2.0, 4.0)

                if not self._is_logged_in(page):
                    # Usar el helper base que carga cookies Google compartidas
                    if not self._ensure_google_session(page, context):
                        # Fallback al login directo propio si el helper falla
                        if not self._login_google(page):
                            results["error"] = "Login Google fallido — configura GOOGLE_EMAIL y GOOGLE_PASSWORD"
                            return results
                    self._save_cookies(context)
                    page.goto(YT_STUDIO, wait_until="domcontentloaded")
                    self.human.think(2.0, 4.0)

                results["success"] = self._upload_short(page, video_path, title, description, tags)
                self._save_cookies(context)

            except Exception as exc:
                self._screenshot(page, "unexpected_error")
                results["error"] = str(exc)
                logger.error("[youtube] Error inesperado: %s", exc)
            finally:
                context.close()
                browser.close()

        return results
