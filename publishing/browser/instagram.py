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
        """
        Login Instagram web con email + password.
        NOTA: Instagram web NO tiene 'Sign in with Google'. Si la cuenta fue
        creada vía Google OAuth en mobile, el usuario debe resetear la contraseña
        en instagram.com/accounts/password/reset/ para obtener una clave web.
        """
        if not self.username or not self.password:
            logger.error("[instagram] Configura IG_USERNAME e IG_PASSWORD en .env")
            return False

        logger.info("[instagram] Iniciando sesion en %s", IG_LOGIN_URL)
        page.goto(IG_LOGIN_URL, wait_until="domcontentloaded")
        self.human.think(2.0, 3.5)
        self._screenshot(page, "login_loaded")
        self._dismiss_modals(page)

        # IG puede mostrar pantalla "Abrir app" en desktop — buscar link de login
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
            self.human.hesitate()
            page.locator(USER_SEL).first.fill(self.username)
            self.human.pause(0.8, 1.5)
            page.locator(PASS_SEL).first.fill(self.password)
            self.human.pause(1.0, 2.0)
            self._screenshot(page, "login_filled")

            try:
                page.locator("input[type='submit'], button[type='submit']").first.click()
            except Exception:
                page.keyboard.press("Enter")
            self.human.think(5.0, 8.0)
            self._dismiss_modals(page)
            self._screenshot(page, "login_after_submit")

            # Verificar login real: debe aparecer el feed, no solo salir del /login
            if self._is_logged_in(page):
                logger.info("[instagram] Login exitoso — feed detectado")
                return True

            # Si está en /challenge o /two_factor, Instagram detectó login sospechoso
            if any(x in page.url for x in ["/challenge", "/two_factor", "/verify"]):
                logger.error(
                    "[instagram] Instagram pide verificacion adicional (IP/dispositivo nuevo). "
                    "Inicia sesion manualmente en Chrome y exporta con la extension."
                )
                self._screenshot(page, "login_challenge")
                return False

            # Si sigue en login, credenciales incorrectas
            if "/accounts/login" in page.url:
                self._screenshot(page, "login_failed")
                logger.warning("[instagram] Credenciales incorrectas o cuenta bloqueada")
                return False

            # Otro caso: redirigido pero no al feed (pantalla intermedia de IG)
            logger.warning("[instagram] Login ambiguo — URL: %s. Esperando feed...", page.url)
            self.human.think(3.0, 5.0)
            self._dismiss_modals(page)
            if self._is_logged_in(page):
                logger.info("[instagram] Feed detectado tras espera extra")
                return True

            self._screenshot(page, "login_no_feed")
            logger.error(
                "[instagram] No se pudo confirmar el feed tras login. "
                "Exporta la sesion con la extension Chrome estando en el feed de Instagram."
            )
            return False

        except Exception as exc:
            self._screenshot(page, "login_error")
            logger.error("[instagram] Error en login: %s", exc)
            return False

    # ── Publicar feed (imagen) ────────────────────────────────────────────────

    # ── Helpers de creación ───────────────────────────────────────────────────

    def _open_create_dialog(self, page: Any) -> bool:
        """
        Abre el diálogo de creación de Instagram clicando el link del sidebar.
        IMPORTANTE: NO navegar a /create/select/ con page.goto() — Instagram lo
        interpreta como el perfil del usuario @create (SPA vs full-page load).
        El clic en el anchor usa el routing JS de React y abre el modal correcto.
        """
        # Asegurar que estamos en home y logueados
        if IG_URL not in page.url or "/accounts/login" in page.url:
            page.goto(IG_URL, wait_until="domcontentloaded")
            self.human.think(2.0, 3.5)

        self._screenshot(page, "create_before")

        # Verificar sesión activa antes de buscar el botón
        if "/accounts/login" in page.url or "Registrarte" in page.content():
            logger.warning("[instagram] No autenticado al intentar crear post")
            return False

        # Selectores del botón Crear en el sidebar (en orden de preferencia)
        # El link a[href='/create/select/'] usa SPA routing — NO page.goto()
        CREATE_SELS = [
            "a[href='/create/select/']",           # link sidebar — más fiable
            "[aria-label='New post']",
            "[aria-label='Nueva publicación']",
            "[aria-label='Create']",
            "[aria-label='Crear']",
            "svg[aria-label='New post']",
            "svg[aria-label='Nueva publicación']",
            # Texto en nav (contexto restringido al sidebar para no pillar 'Crear cuenta')
            "nav span:has-text('Create')",
            "nav span:has-text('Crear')",
            "nav a span:has-text('Create')",
            "nav a span:has-text('Crear')",
        ]
        for sel in CREATE_SELS:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="visible", timeout=3000)
                self.human.before_click(page)
                btn.click()
                self.human.think(1.5, 2.5)
                self._screenshot(page, "create_btn_clicked")
                logger.info("[instagram] Boton Crear clicado: %s", sel)
                return True
            except Exception:
                continue

        logger.warning("[instagram] No se encontro boton de creacion")
        self._screenshot(page, "create_not_found")
        return False

    def _get_file_input(self, page: Any, timeout: int = 10000) -> Any:
        """Obtiene el input de archivo del diálogo, visible o no."""
        # Primero intentar attached (funciona aunque esté hidden)
        try:
            return page.wait_for_selector("input[type='file']", timeout=timeout, state="attached")
        except PWTimeout:
            pass
        # Fallback: cualquier input file en el DOM
        try:
            el = page.locator("input[type='file']").first
            el.wait_for(state="attached", timeout=3000)
            return el
        except Exception:
            return None

    def _wizard_to_share(self, page: Any, caption: str) -> bool:
        """Navega el wizard Next→Next→(caption)→Share/Compartir."""
        caption_written = False
        for step in range(6):
            self._screenshot(page, f"wizard_step_{step}")

            # ¿Ya llegamos a Share?
            for share_text in ["Share", "Compartir", "Publish", "Publicar"]:
                try:
                    btn = page.get_by_role("button", name=share_text).first
                    if btn.is_visible(timeout=1500):
                        if not caption_written:
                            self._fill_caption(page, caption)
                            self.human.think(1.0, 2.0)
                            caption_written = True
                        self.human.before_click(page)
                        btn.click()
                        self.human.think(5.0, 9.0)
                        self._screenshot(page, "published")
                        return True
                except Exception:
                    pass

            # Siguiente paso
            advanced = False
            for next_text in ["Next", "Siguiente", "OK", "Continue", "Continuar"]:
                try:
                    btn = page.get_by_role("button", name=next_text).first
                    if btn.is_visible(timeout=1500):
                        self.human.before_click(page)
                        btn.click()
                        self.human.think(1.5, 2.5)
                        advanced = True
                        break
                except Exception:
                    pass

            if not advanced:
                break

        return False

    # ── Publicar feed (imagen) ────────────────────────────────────────────────

    def _publish_feed(self, page: Any, image_path: Path, caption: str) -> bool:
        logger.info("[instagram] Publicando imagen de feed: %s", image_path.name)

        try:
            if not self._open_create_dialog(page):
                return False

            # Si el diálogo tiene opciones (Post/Reel/Story), seleccionar Post
            for opt_text in ["Post", "Publicación", "Photo", "Foto"]:
                try:
                    opt = page.get_by_role("button", name=opt_text).first
                    if opt.is_visible(timeout=2000):
                        opt.click()
                        self.human.think(1.0, 2.0)
                        logger.info("[instagram] Opcion '%s' seleccionada", opt_text)
                        break
                except Exception:
                    pass

            file_input = self._get_file_input(page)
            if not file_input:
                self._screenshot(page, "feed_no_input")
                logger.error("[instagram] No se encontro input de archivo para feed")
                return False

            file_input.set_input_files(str(image_path))
            logger.info("[instagram] Imagen seleccionada")
            self.human.think(3.0, 5.0)
            self._screenshot(page, "feed_after_file")

            result = self._wizard_to_share(page, caption)
            if result:
                logger.info("[instagram] Feed publicado exitosamente")
            return result

        except Exception as exc:
            self._screenshot(page, "feed_error")
            logger.error("[instagram] Error publicando feed: %s", exc)
            return False

    # ── Publicar reel (video) ─────────────────────────────────────────────────

    def _publish_reel(self, page: Any, video_path: Path, caption: str) -> bool:
        logger.info("[instagram] Publicando reel: %s", video_path.name)

        try:
            if not self._open_create_dialog(page):
                return False

            # Seleccionar opción Reel en el diálogo de creación
            for opt_text in ["Reel", "Video"]:
                try:
                    opt = page.get_by_role("button", name=opt_text).first
                    if opt.is_visible(timeout=2000):
                        opt.click()
                        self.human.think(1.0, 2.0)
                        logger.info("[instagram] Opcion '%s' seleccionada", opt_text)
                        break
                except Exception:
                    pass

            # Input de archivo — aceptar video
            file_input = None
            try:
                file_input = page.wait_for_selector(
                    "input[type='file'][accept*='video'], input[type='file']",
                    timeout=10000,
                    state="attached",
                )
            except PWTimeout:
                file_input = self._get_file_input(page)

            if not file_input:
                self._screenshot(page, "reel_no_input")
                logger.error("[instagram] No se encontro input de archivo para reel")
                return False

            file_input.set_input_files(str(video_path))
            logger.info("[instagram] Video seleccionado")
            self.human.think(6.0, 12.0)  # procesamiento de video
            self._screenshot(page, "reel_after_file")

            result = self._wizard_to_share(page, caption)
            if result:
                logger.info("[instagram] Reel publicado exitosamente")
            return result

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
            browser, context = self._build_context(pw, headless=False, mobile=False, width=1920, height=1080)
            page = context.new_page()

            try:
                page.goto(IG_URL, wait_until="domcontentloaded")
                self.human.think(2.5, 4.0)

                if not self._is_logged_in(page):
                    if not self._login(page):
                        results["error"] = "Login fallido — resetea la contrasena en instagram.com/accounts/password/reset/"
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
