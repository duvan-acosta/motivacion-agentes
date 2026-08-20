"""Helper OAuth Google — login único reutilizable en todos los publishers."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

GOOGLE_LOGIN_URL = "https://accounts.google.com/signin/v2/identifier?hl=es"
GOOGLE_CHECK_URL = "https://myaccount.google.com"

# Selectores del flujo de login Google
_EMAIL_SEL = "input[type='email'], input[name='identifier']"
_PASS_SEL = "input[type='password']"
_NEXT_SELS = ["#identifierNext", "#passwordNext", "button:has-text('Siguiente')", "button:has-text('Next')"]
_SKIP_TEXTS = ["Ahora no", "Not now", "Skip", "Omitir", "Recordar más tarde", "Continuar", "Continue"]


class GoogleAuthHelper:
    """
    Mixin que añade login Google y flujo OAuth a cualquier publisher.

    Uso: heredar junto con BaseBrowserPublisher. Llama a
    `self._ensure_google_session(page, context)` antes de intentar OAuth.
    """

    def _google_email(self) -> str:
        return os.getenv("GOOGLE_EMAIL", os.getenv("IG_USERNAME", ""))

    def _google_password(self) -> str:
        return os.getenv("GOOGLE_PASSWORD", os.getenv("IG_PASSWORD", ""))

    # ── Verificar sesión activa ────────────────────────────────────────────────

    def _google_is_logged_in(self, page: Any) -> bool:
        """Rápido: abre myaccount.google.com y busca el avatar."""
        try:
            page.goto(GOOGLE_CHECK_URL, wait_until="domcontentloaded")
            page.wait_for_selector(
                "a[aria-label*='Google Account'], img[alt*='profile'], "
                "[data-email], header[aria-label]",
                timeout=6000,
            )
            logger.info("[google_auth] Sesion Google activa")
            return True
        except PWTimeout:
            return False

    # ── Login Google directo ───────────────────────────────────────────────────

    def _google_login(self, page: Any) -> bool:
        """Hace login en Google con email+password. Devuelve True si éxito."""
        email = self._google_email()
        password = self._google_password()
        if not email or not password:
            logger.error("[google_auth] Configura GOOGLE_EMAIL y GOOGLE_PASSWORD en .env")
            return False

        logger.info("[google_auth] Login Google como %s", email)
        page.goto(GOOGLE_LOGIN_URL, wait_until="domcontentloaded")
        self.human.think(2.0, 4.0)  # type: ignore[attr-defined]

        try:
            # Email
            page.wait_for_selector(_EMAIL_SEL, timeout=12000)
            page.locator(_EMAIL_SEL).first.fill(email)
            self.human.pause(0.6, 1.2)  # type: ignore[attr-defined]
            self._click_google_next(page)
            self.human.think(2.0, 3.5)  # type: ignore[attr-defined]

            # Contraseña
            page.wait_for_selector(_PASS_SEL, timeout=10000)
            self.human.pause(0.5, 1.0)  # type: ignore[attr-defined]
            page.locator(_PASS_SEL).first.fill(password)
            self.human.pause(0.8, 1.5)  # type: ignore[attr-defined]
            self._click_google_next(page)
            self.human.think(5.0, 9.0)  # type: ignore[attr-defined]

            # Descartar verificaciones secundarias (teléfono, 2FA optional)
            self._dismiss_google_prompts(page)

            # Verificar
            try:
                page.wait_for_url("*myaccount.google.com*", timeout=8000)
                logger.info("[google_auth] Login Google exitoso")
                return True
            except PWTimeout:
                pass

            page.goto(GOOGLE_CHECK_URL, wait_until="domcontentloaded")
            self.human.think(2.0, 3.5)  # type: ignore[attr-defined]

            try:
                page.wait_for_selector(
                    "a[aria-label*='Google Account'], [data-email]", timeout=6000
                )
                logger.info("[google_auth] Login Google exitoso (verificacion manual)")
                return True
            except PWTimeout:
                logger.warning("[google_auth] Login Google fallido — URL: %s", page.url)
                return False

        except Exception as exc:
            logger.error("[google_auth] Error en login Google: %s", exc)
            return False

    def _click_google_next(self, page: Any) -> None:
        for sel in _NEXT_SELS:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    return
            except Exception:
                continue
        page.keyboard.press("Enter")

    def _dismiss_google_prompts(self, page: Any) -> None:
        """Cierra los diálogos post-login de Google (2FA, teléfono, etc.)."""
        for text in _SKIP_TEXTS:
            try:
                btn = page.get_by_role("button", name=text)
                if btn.is_visible(timeout=3000):
                    btn.click()
                    self.human.think(1.5, 2.5)  # type: ignore[attr-defined]
            except Exception:
                pass

    # ── Asegurar sesión antes de OAuth ────────────────────────────────────────

    def _ensure_google_session(self, page: Any, context: Any) -> bool:
        """
        Garantiza que hay sesión Google activa en el contexto.
        Si no, hace login y guarda las cookies.
        """
        if self._google_is_logged_in(page):
            return True

        ok = self._google_login(page)
        if ok:
            self._save_cookies(context)  # type: ignore[attr-defined]
        return ok

    # ── Flujo OAuth: click "Sign in with Google" en plataforma ────────────────

    def _oauth_sign_in_with_google(
        self,
        page: Any,
        context: Any,
        btn_selectors: list[str],
    ) -> bool:
        """
        Hace clic en el botón 'Iniciar sesión con Google' de cualquier plataforma.
        Maneja tanto popup como redirect. Devuelve True si éxito.
        """
        # Asegurar sesión Google activa antes de lanzar el OAuth
        if not self._ensure_google_session(page, context):
            return False

        # Volver a la plataforma (la verificación de Google pudo haber navegado)
        # El llamador debe haber establecido la URL antes de llamar aquí.

        btn = None
        for sel in btn_selectors:
            try:
                candidate = page.locator(sel).first
                if candidate.is_visible(timeout=3000):
                    btn = candidate
                    break
            except Exception:
                continue

        if not btn:
            logger.warning("[google_auth] Boton 'Sign in with Google' no encontrado")
            return False

        logger.info("[google_auth] Clic en boton OAuth Google")

        # Intentar manejar popup (ventana nueva) — si no hay popup en 3s, es redirect
        try:
            with context.expect_page(timeout=5000) as popup_info:
                btn.click()
            popup = popup_info.value
            popup.wait_for_load_state("domcontentloaded")
            self.human.think(2.0, 4.0)  # type: ignore[attr-defined]

            logger.info("[google_auth] Popup Google detectado: %s", popup.url)
            result = self._handle_google_popup(popup)
            if result:
                # Esperar que el popup cierre y la plataforma termine el OAuth
                try:
                    popup.wait_for_event("close", timeout=15000)
                except Exception:
                    pass
                self.human.think(3.0, 6.0)  # type: ignore[attr-defined]
                return True
            return False

        except PWTimeout:
            # No hubo popup — es redirect inline
            logger.info("[google_auth] Redirect OAuth inline (sin popup)")
            self.human.think(3.0, 6.0)  # type: ignore[attr-defined]
            self._dismiss_google_prompts(page)
            self.human.think(2.0, 4.0)  # type: ignore[attr-defined]
            return True

    def _handle_google_popup(self, popup: Any) -> bool:
        """
        Dentro del popup de Google: selecciona la cuenta o confirma acceso.
        Si Google ya tiene sesión activa, solo hace clic en la cuenta.
        """
        try:
            # Google muestra selector de cuenta (ya autenticado)
            email = self._google_email()
            for sel in [
                f"[data-email='{email}']",
                f"div:has-text('{email}')",
                "[data-identifier]",
                "li[data-authuser]",
                "div[role='link']",
            ]:
                try:
                    el = popup.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        self.human.think(2.0, 4.0)  # type: ignore[attr-defined]
                        logger.info("[google_auth] Cuenta seleccionada en popup")
                        break
                except Exception:
                    continue

            # Confirmar permisos si los pide
            for text in ["Continuar", "Continue", "Permitir", "Allow", "Acceder", "Sign in"]:
                try:
                    btn = popup.get_by_role("button", name=text)
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        self.human.think(2.0, 3.5)  # type: ignore[attr-defined]
                except Exception:
                    continue

            return True

        except Exception as exc:
            logger.warning("[google_auth] Error en popup Google: %s", exc)
            return False
