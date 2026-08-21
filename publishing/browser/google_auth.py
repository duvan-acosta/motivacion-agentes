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
        """
        Hace login en Google con email+password.
        NOTA: Google bloquea login desde Playwright/Puppeteer (detecta CDP).
        Si falla con 'No se ha podido iniciar sesion', ejecuta:
            python setup_sessions.py google
        para hacer login manualmente y guardar las cookies.
        """
        email = self._google_email()
        password = self._google_password()
        if not email or not password:
            logger.error("[google_auth] Configura GOOGLE_EMAIL y GOOGLE_PASSWORD en .env")
            return False

        logger.info("[google_auth] Login Google como %s", email)
        page.goto(GOOGLE_LOGIN_URL, wait_until="domcontentloaded")
        self.human.think(2.0, 4.0)  # type: ignore[attr-defined]

        # Detectar bloqueo de Google antes de continuar
        blocked_texts = ["No se ha podido iniciar sesion", "No puedes acceder", "couldn't sign in", "can't sign in"]
        for txt in blocked_texts:
            try:
                if page.get_by_text(txt, exact=False).is_visible(timeout=1500):
                    logger.error(
                        "[google_auth] Google bloquea este navegador. "
                        "Ejecuta: python setup_sessions.py google  — para login manual"
                    )
                    return False
            except Exception:
                pass

        try:
            # Email
            page.wait_for_selector(_EMAIL_SEL, timeout=12000)
            page.locator(_EMAIL_SEL).first.fill(email)
            self.human.pause(0.6, 1.2)  # type: ignore[attr-defined]
            self._click_google_next(page)
            self.human.think(2.0, 3.5)  # type: ignore[attr-defined]

            # Detectar bloqueo post-email
            for txt in blocked_texts:
                try:
                    if page.get_by_text(txt, exact=False).is_visible(timeout=1000):
                        logger.error(
                            "[google_auth] Google bloqueo post-email. "
                            "Ejecuta: python setup_sessions.py google"
                        )
                        return False
                except Exception:
                    pass

            # Google puede mostrar pantalla de Passkey antes del campo de contraseña
            self._bypass_google_passkey(page)

            # Contraseña
            page.wait_for_selector(_PASS_SEL, timeout=12000)
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
                logger.warning(
                    "[google_auth] Login Google fallido — ejecuta: python setup_sessions.py google"
                )
                return False

        except Exception as exc:
            logger.error("[google_auth] Error en login Google: %s — ejecuta: python setup_sessions.py google", exc)
            return False

    def _bypass_google_passkey(self, page: Any) -> None:
        """
        Google puede mostrar 'Elige cómo iniciar sesión' (Passkey/biometría)
        después del email. Aquí detectamos la pantalla y navegamos a contraseña.
        Captura screenshot para debug si detecta pantalla de selección de método.
        """
        import time as _t
        from pathlib import Path as _Path

        # Capturar estado actual para debug
        try:
            shots_dir = _Path("data/screenshots")
            shots_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots_dir / f"google_passkey_check_{int(_t.time())}.png"))
        except Exception:
            pass

        # Botones/links que aparecen en la pantalla de Passkey/selector de método
        passkey_indicators = [
            "Ingresar contraseña",          # ES — opción directa de contraseña
            "Usar una contraseña",           # ES — variante
            "Usar otra cuenta",              # ES
            "Use a password",                # EN
            "Enter your password",           # EN
            "Try another way",              # EN — "Intentar de otra forma"
            "Intentar de otra forma",       # ES
            "Probar de otra manera",        # ES
            "More options",                 # EN
            "Más opciones",                 # ES
            "Switch account",               # EN
        ]
        for text in passkey_indicators:
            try:
                el = page.get_by_text(text, exact=False).first
                if el.is_visible(timeout=1500):
                    el.click()
                    self.human.think(1.5, 3.0)  # type: ignore[attr-defined]
                    logger.info("[google_auth] Passkey screen bypasseada via '%s'", text)
                    # Después de "Try another way" puede aparecer menú con "Contraseña"
                    for pwd_text in ["Contraseña", "Password", "Ingresar contraseña"]:
                        try:
                            pwd_opt = page.get_by_text(pwd_text, exact=False).first
                            if pwd_opt.is_visible(timeout=2000):
                                pwd_opt.click()
                                self.human.think(1.5, 2.5)  # type: ignore[attr-defined]
                                logger.info("[google_auth] Opcion Password seleccionada")
                                return
                        except Exception:
                            continue
                    return
            except Exception:
                continue

        # También intentar via link href con "usepw"
        try:
            pwd_link = page.locator("a[href*='usepw'], a[href*='password']").first
            if pwd_link.is_visible(timeout=1500):
                pwd_link.click()
                self.human.think(1.5, 2.5)  # type: ignore[attr-defined]
                logger.info("[google_auth] Passkey bypass via href link")
        except Exception:
            pass

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
        Dentro del popup de Google OAuth:
        - Si ya hay sesión activa: selecciona la cuenta
        - Si no: hace login completo (email → passkey bypass → password)
        - Luego confirma permisos si aparecen
        """
        import time as _t
        try:
            popup.wait_for_load_state("domcontentloaded")
            self.human.think(2.0, 3.5)  # type: ignore[attr-defined]
            logger.info("[google_auth] Popup URL: %s", popup.url)

            # Capturar screenshot con nombre único para debug
            try:
                import os as _os
                from pathlib import Path as _Path
                shots_dir = _Path("data/screenshots")
                shots_dir.mkdir(parents=True, exist_ok=True)
                popup.screenshot(path=str(shots_dir / f"google_popup_state_{int(_t.time())}.png"))
            except Exception:
                pass

            email = self._google_email()

            # ── Caso 1: Selector de cuenta (sesión Google ya activa) ──────────
            for sel in [
                f"[data-email='{email}']",
                f"[data-identifier='{email}']",
                "div[data-authuser]",
                "li[data-authuser]",
                "div[role='link'][data-identifier]",
                # Fallback: cualquier elemento con el email visible
                f"div:has-text('{email}')",
            ]:
                try:
                    el = popup.locator(sel).first
                    if el.is_visible(timeout=2500):
                        el.click()
                        self.human.think(2.0, 4.0)  # type: ignore[attr-defined]
                        logger.info("[google_auth] Cuenta seleccionada en popup: %s", sel)
                        # Confirmar permisos si aparecen después de seleccionar cuenta
                        self._dismiss_google_prompts(popup)
                        return True
                except Exception:
                    continue

            # ── Caso 2: Pantalla de login completo (sesión NO activa en popup) ──
            try:
                popup.wait_for_selector(_EMAIL_SEL, timeout=5000)
                logger.info("[google_auth] Popup requiere login completo")

                # Email
                popup.locator(_EMAIL_SEL).first.fill(email)
                self.human.pause(0.6, 1.2)  # type: ignore[attr-defined]
                self._click_google_next(popup)
                self.human.think(2.5, 4.0)  # type: ignore[attr-defined]

                # Capturar qué muestra Google después del email
                try:
                    shots_dir = _Path("data/screenshots")
                    popup.screenshot(path=str(shots_dir / f"google_popup_after_email_{int(_t.time())}.png"))
                except Exception:
                    pass

                # Bypass Passkey antes del campo de contraseña
                self._bypass_google_passkey(popup)

                # Contraseña
                password = self._google_password()
                popup.wait_for_selector(_PASS_SEL, timeout=15000)
                popup.locator(_PASS_SEL).first.fill(password)
                self.human.pause(0.8, 1.5)  # type: ignore[attr-defined]
                self._click_google_next(popup)
                self.human.think(4.0, 7.0)  # type: ignore[attr-defined]

                logger.info("[google_auth] Login completo en popup — esperando redirect")
                self._dismiss_google_prompts(popup)
                return True

            except PWTimeout:
                # No encontró email input → asumir que ya está autenticado o hubo redirect
                logger.info("[google_auth] No email input en popup — posible sesion activa o redirect")
                self._dismiss_google_prompts(popup)
                return True

        except Exception as exc:
            logger.warning("[google_auth] Error en popup Google: %s", exc)
            return False
