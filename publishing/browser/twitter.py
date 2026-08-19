"""Publicador de X/Twitter via navegador — publica tweets con imagen."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

from publishing.browser.base import BaseBrowserPublisher

logger = logging.getLogger(__name__)

X_URL = "https://x.com"
X_LOGIN_URL = "https://x.com/i/flow/login"
X_COMPOSE_URL = "https://x.com/compose/tweet"


class TwitterBrowserPublisher(BaseBrowserPublisher):
    PLATFORM = "twitter"

    def __init__(self) -> None:
        super().__init__()
        self.username = os.getenv("X_USERNAME", "")
        self.password = os.getenv("X_PASSWORD", "")

    # ── Login ──────────────────────────────────────────────────────────────────

    def _is_logged_in(self, page: Any) -> bool:
        try:
            page.wait_for_selector(
                "[data-testid='SideNav_NewTweet_Button'], [aria-label='Post']",
                timeout=5000,
            )
            return True
        except PWTimeout:
            return False

    def _login(self, page: Any) -> bool:
        if not self.username or not self.password:
            logger.error("[twitter] Credenciales X_USERNAME / X_PASSWORD no configuradas")
            return False

        logger.info("[twitter] Iniciando sesión como %s", self.username)
        # Ir al home primero para cargar cookies/contexto, luego al login
        page.goto(X_URL, wait_until="domcontentloaded")
        self.human.think(2.0, 3.5)
        page.goto(X_LOGIN_URL, wait_until="domcontentloaded")
        self.human.think(3.0, 5.0)
        self._screenshot(page, "login_page_loaded")

        try:
            # Paso 1: email/usuario
            # X usa overlays que bloquean click directo — usamos fill() + type()
            user_sel = (
                "input[data-testid='ocfEnterTextTextInput'], "
                "input[name='username_or_email'], "
                "input[autocomplete='username'], "
                "input[name='text'], "
                "input[type='text']"
            )
            page.wait_for_selector(user_sel, timeout=15000)
            self.human.pause(0.5, 1.0)
            # fill() no requiere click — evita el overlay de PassKey
            page.locator(user_sel).first.fill(self.username)
            self.human.pause(0.8, 1.5)
            self._screenshot(page, "login_email_filled")

            # Botón Next
            self._click_next(page)
            self.human.think(2.0, 3.5)
            self._screenshot(page, "login_after_email_next")

            # X puede pedir verificación de nombre de usuario
            try:
                verify_sel = "input[data-testid='ocfEnterTextTextInput']"
                page.wait_for_selector(verify_sel, timeout=4000)
                logger.info("[twitter] Verificación de usuario extra solicitada")
                handle = self.username.split("@")[0]
                page.locator(verify_sel).first.fill(handle)
                self.human.pause(0.5, 1.0)
                self._click_next(page)
                self.human.think(1.5, 2.5)
            except PWTimeout:
                pass

            # Paso 2: contraseña
            pass_sel = "input[type='password'], input[name='password']"
            page.wait_for_selector(pass_sel, timeout=10000)
            self.human.pause(0.4, 0.8)
            page.locator(pass_sel).first.fill(self.password)
            self.human.pause(0.8, 1.8)
            self._screenshot(page, "login_password_filled")

            # Botón Log in
            for selector in [
                "[data-testid='LoginForm_Login_Button']",
                "button[data-testid='LoginForm_Login_Button']",
            ]:
                try:
                    btn = page.wait_for_selector(selector, timeout=3000)
                    if btn and btn.is_visible():
                        btn.click()
                        self.human.think(5.0, 8.0)
                        break
                except PWTimeout:
                    continue
            else:
                # Fallback por texto
                for btn_text in ["Log in", "Iniciar sesión", "Sign in"]:
                    try:
                        btn = page.get_by_role("button", name=btn_text)
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            self.human.think(5.0, 8.0)
                            break
                    except Exception:
                        continue

            self._screenshot(page, "login_after_submit")

            if self._is_logged_in(page):
                logger.info("[twitter] Login exitoso")
                return True

            logger.warning("[twitter] Login posiblemente fallido — URL: %s", page.url)
            return False

        except Exception as exc:
            self._screenshot(page, "login_error")
            logger.error("[twitter] Error en login: %s", exc)
            return False

    def _click_next(self, page: Any) -> None:
        # Intentar por data-testid primero
        for selector in [
            "[data-testid='ocfEnterTextNextButton']",
            "[data-testid='LoginForm_Login_Button']",
        ]:
            try:
                btn = page.wait_for_selector(selector, timeout=3000)
                if btn and btn.is_visible():
                    btn.click()
                    return
            except PWTimeout:
                continue
        # Intentar por texto (X cambia el idioma según la región)
        for btn_text in ["Continuar", "Next", "Siguiente", "Continue"]:
            try:
                btn = page.get_by_role("button", name=btn_text)
                if btn.is_visible(timeout=2000):
                    btn.click()
                    return
            except Exception:
                continue
        # Fallback: Enter en el campo activo
        page.keyboard.press("Enter")

    # ── Publicar tweet ─────────────────────────────────────────────────────────

    def _post_tweet(self, page: Any, text: str, image_path: Path | None) -> bool:
        logger.info("[twitter] Publicando tweet...")

        try:
            # Abrir modal de composición
            page.goto(X_COMPOSE_URL, wait_until="domcontentloaded")
            self.human.think(2.0, 3.5)

            # Área de texto del tweet
            tweet_box = page.wait_for_selector(
                "[data-testid='tweetTextarea_0'], div[role='textbox'][aria-label]",
                timeout=10000,
            )
            tweet_box.click()
            self.human.pause(0.4, 0.8)

            # Escribir carácter a carácter
            for char in text[:280]:
                page.keyboard.type(char)
                time.sleep(0.04 + (0.08 if char in ".!?" else 0))

            self.human.think(1.0, 2.0)

            # Adjuntar imagen si existe
            if image_path and image_path.exists():
                try:
                    media_btn = page.wait_for_selector(
                        "[data-testid='attachments'], input[type='file'][accept*='image']",
                        timeout=5000,
                        state="attached",
                    )
                    if "input" in (media_btn.get_attribute("data-testid") or ""):
                        media_btn.set_input_files(str(image_path))
                    else:
                        media_btn.click()
                        self.human.pause(0.5, 1.0)
                        file_input = page.wait_for_selector(
                            "input[type='file']", timeout=5000, state="attached"
                        )
                        file_input.set_input_files(str(image_path))
                    self.human.think(2.0, 4.0)
                    logger.info("[twitter] Imagen adjuntada")
                except Exception as exc:
                    logger.warning("[twitter] No se pudo adjuntar imagen: %s", exc)

            # Publicar
            for btn_label in ["Post", "Publicar", "Tweet"]:
                try:
                    post_btn = page.get_by_test_id("tweetButton")
                    if not post_btn or not post_btn.is_visible(timeout=2000):
                        raise Exception("no testid")
                    self.human.move_mouse_randomly(page)
                    self.human.pause(0.8, 1.5)
                    post_btn.click()
                    self.human.think(3.0, 5.0)
                    self._screenshot(page, "tweet_published")
                    logger.info("[twitter] Tweet publicado")
                    return True
                except Exception:
                    try:
                        btn = page.get_by_role("button", name=btn_label)
                        if btn.is_visible(timeout=2000):
                            self.human.pause(0.8, 1.5)
                            btn.click()
                            self.human.think(3.0, 5.0)
                            self._screenshot(page, "tweet_published")
                            logger.info("[twitter] Tweet publicado")
                            return True
                    except Exception:
                        continue

            self._screenshot(page, "twitter_no_post_btn")
            return False

        except Exception as exc:
            self._screenshot(page, "twitter_error")
            logger.error("[twitter] Error publicando tweet: %s", exc)
            return False

    # ── Entrada principal ──────────────────────────────────────────────────────

    def publish(self, package_path: Path) -> dict[str, Any]:
        tweet_file = package_path / "twitter" / "tweet.txt"
        image_path = package_path / "twitter" / "card.jpg"
        caption_file = package_path / "instagram" / "caption.txt"  # fallback

        # Texto del tweet (280 chars)
        if tweet_file.exists():
            tweet_text = tweet_file.read_text(encoding="utf-8").strip()[:280]
        elif caption_file.exists():
            # Fallback: primeras 250 chars del caption de IG
            tweet_text = caption_file.read_text(encoding="utf-8").strip()[:250]
        else:
            tweet_text = ""

        if not tweet_text:
            return {"platform": "twitter", "success": False, "error": "Sin texto para tweet"}

        results: dict[str, Any] = {"platform": "twitter", "success": False}

        with sync_playwright() as pw:
            browser, context = self._build_context(pw, headless=True, mobile=False)
            page = context.new_page()

            try:
                page.goto(X_URL, wait_until="domcontentloaded")
                self.human.think(2.0, 3.5)

                if not self._is_logged_in(page):
                    if not self._login(page):
                        results["error"] = "Login fallido — configura X_USERNAME y X_PASSWORD"
                        return results
                    self._save_cookies(context)

                img = image_path if image_path.exists() else None
                results["success"] = self._post_tweet(page, tweet_text, img)
                self._save_cookies(context)

            except Exception as exc:
                self._screenshot(page, "unexpected_error")
                results["error"] = str(exc)
                logger.error("[twitter] Error inesperado: %s", exc)
            finally:
                context.close()
                browser.close()

        return results
