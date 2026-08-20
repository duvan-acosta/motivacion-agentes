"""Publicador de X/Twitter via navegador — login con email + password propio."""

from __future__ import annotations

import logging
import os
import random
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
                "[data-testid='SideNav_NewTweet_Button'], "
                "[aria-label='Post'], "
                "[data-testid='primaryColumn']",
                timeout=5000,
            )
            return True
        except PWTimeout:
            return False

    def _login(self, page: Any, context: Any = None) -> bool:
        logger.info("[twitter] Iniciando sesion como %s", self._google_email() or self.username)
        self.human.navigate(page, X_URL)
        self.human.think(2.0, 3.5)
        self.human.navigate(page, X_LOGIN_URL)
        self.human.think(3.0, 5.5)
        self._screenshot(page, "login_loaded")

        # ── Intento 1: Google OAuth directo ─────────────────────────────────
        if context:
            google_sels = [
                "[data-testid='google_sign_in_container']",
                "a[href*='google']:has-text('Google')",
                "span:has-text('Continuar con Google')",
                "span:has-text('Continue with Google')",
                "span:has-text('Sign in with Google')",
                "span:has-text('Iniciar sesión con Google')",
                "div[aria-label*='Google']",
            ]
            for sel in google_sels:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        logger.info("[twitter] Boton Google encontrado: %s", sel)
                        self.human.before_click(page)
                        try:
                            with context.expect_page(timeout=6000) as popup_info:
                                el.click()
                            popup = popup_info.value
                            popup.wait_for_load_state("domcontentloaded")
                            self.human.think(2.0, 3.5)
                            logger.info("[twitter] Popup Google: %s", popup.url)

                            ok = self._handle_google_popup(popup)
                            if ok:
                                try:
                                    popup.wait_for_event("close", timeout=20000)
                                except Exception:
                                    pass
                                self.human.think(3.0, 6.0)
                                self._screenshot(page, "login_after_google")
                                if self._is_logged_in(page):
                                    logger.info("[twitter] Login Google OAuth exitoso")
                                    return True
                        except PWTimeout:
                            logger.info("[twitter] Google OAuth redirect inline")
                            self.human.think(4.0, 7.0)
                            if self._is_logged_in(page):
                                return True
                        except Exception as exc:
                            logger.warning("[twitter] Google popup fallo: %s", exc)
                        break
                except Exception:
                    continue

        # ── Intento 2: email + password ──────────────────────────────────────
        if not self.username or not self.password:
            logger.error("[twitter] Configura X_USERNAME y X_PASSWORD en .env")
            return False

        logger.info("[twitter] Intentando login email/password")
        # Volver al login en caso de que hayamos navegado
        try:
            if X_LOGIN_URL not in page.url and "x.com/i/flow/login" not in page.url:
                self.human.navigate(page, X_LOGIN_URL)
                self.human.think(2.5, 4.5)
        except Exception:
            pass

        try:
            user_sel = (
                "input[data-testid='ocfEnterTextTextInput'], "
                "input[name='text'], "
                "input[autocomplete='username'], "
                "input[type='text']"
            )
            page.wait_for_selector(user_sel, timeout=15000)
            self.human.hesitate()
            page.locator(user_sel).first.fill(self.username)
            self.human.pause(1.0, 2.0)
            self._screenshot(page, "login_email_filled")

            self._click_next(page)
            self.human.think(2.5, 4.5)
            self._screenshot(page, "login_after_email_next")

            # X puede pedir verificación extra de handle
            try:
                verify_sel = "input[data-testid='ocfEnterTextTextInput']"
                page.wait_for_selector(verify_sel, timeout=4000)
                logger.info("[twitter] Verificacion de handle solicitada")
                handle = self.username.split("@")[0]
                page.locator(verify_sel).first.fill(handle)
                self.human.pause(0.8, 1.5)
                self._click_next(page)
                self.human.think(2.0, 3.5)
            except PWTimeout:
                pass

            # Paso 2: contraseña
            pass_sel = "input[type='password'], input[name='password']"
            page.wait_for_selector(pass_sel, timeout=10000)
            self.human.hesitate()
            page.locator(pass_sel).first.fill(self.password)
            self.human.pause(1.0, 2.0)
            self._screenshot(page, "login_password_filled")

            for selector in ["[data-testid='LoginForm_Login_Button']"]:
                try:
                    btn = page.wait_for_selector(selector, timeout=3000)
                    if btn and btn.is_visible():
                        self.human.before_click(page)
                        btn.click()
                        self.human.think(5.0, 9.0)
                        break
                except PWTimeout:
                    continue
            else:
                for txt in ["Log in", "Iniciar sesión", "Sign in"]:
                    try:
                        btn = page.get_by_role("button", name=txt)
                        if btn.is_visible(timeout=2000):
                            self.human.before_click(page)
                            btn.click()
                            self.human.think(5.0, 9.0)
                            break
                    except Exception:
                        continue

            self._screenshot(page, "login_after_submit")

            if self._is_logged_in(page):
                logger.info("[twitter] Login exitoso")
                return True

            logger.warning("[twitter] Login fallido — URL: %s", page.url)
            return False

        except Exception as exc:
            self._screenshot(page, "login_error")
            logger.error("[twitter] Error en login: %s", exc)
            return False

    def _click_next(self, page: Any) -> None:
        for selector in [
            "[data-testid='ocfEnterTextNextButton']",
            "[data-testid='LoginForm_Login_Button']",
        ]:
            try:
                btn = page.wait_for_selector(selector, timeout=3000)
                if btn and btn.is_visible():
                    self.human.before_click(page)
                    btn.click()
                    return
            except PWTimeout:
                continue
        for txt in ["Continuar", "Next", "Siguiente", "Continue"]:
            try:
                btn = page.get_by_role("button", name=txt)
                if btn.is_visible(timeout=2000):
                    self.human.before_click(page)
                    btn.click()
                    return
            except Exception:
                continue
        page.keyboard.press("Enter")

    # ── Publicar tweet ─────────────────────────────────────────────────────────

    def _post_tweet(self, page: Any, text: str, image_path: Path | None) -> bool:
        logger.info("[twitter] Publicando tweet...")

        try:
            # Pasar por home antes de componer — más natural
            self.human.navigate(page, X_URL)
            self.human.read_page(2.0, 4.0)
            self.human.scroll(page, 80, 250)

            self.human.navigate(page, X_COMPOSE_URL)
            self.human.think(2.0, 3.5)

            tweet_box = page.wait_for_selector(
                "[data-testid='tweetTextarea_0'], div[role='textbox'][aria-label]",
                timeout=10000,
            )
            self.human.before_click(page)
            tweet_box.click()
            self.human.pause(0.6, 1.2)

            for char in text[:280]:
                page.keyboard.type(char)
                delay = random.uniform(0.06, 0.20)
                if char in ".,!?":
                    delay += random.uniform(0.08, 0.18)
                elif char == " ":
                    delay += random.uniform(0.02, 0.08)
                time.sleep(delay)

            self.human.think(1.5, 3.0)

            # Adjuntar imagen
            if image_path and image_path.exists():
                try:
                    for file_sel in ["input[type='file'][accept*='image']", "input[type='file']"]:
                        try:
                            fi = page.wait_for_selector(file_sel, timeout=4000, state="attached")
                            if fi:
                                fi.set_input_files(str(image_path))
                                self.human.think(2.5, 4.5)
                                logger.info("[twitter] Imagen adjuntada")
                                break
                        except PWTimeout:
                            continue
                    else:
                        media_btn = page.locator("[data-testid='attachments']").first
                        if media_btn.is_visible(timeout=3000):
                            self.human.before_click(page)
                            media_btn.click()
                            self.human.pause(0.8, 1.5)
                            fi = page.wait_for_selector("input[type='file']", timeout=5000, state="attached")
                            fi.set_input_files(str(image_path))
                            self.human.think(2.5, 4.5)
                except Exception as exc:
                    logger.warning("[twitter] No se pudo adjuntar imagen: %s", exc)

            self.human.move_mouse_randomly(page)
            self.human.pause(1.0, 2.0)

            # Publicar
            try:
                post_btn = page.get_by_test_id("tweetButton")
                if post_btn.is_visible(timeout=3000):
                    self.human.before_click(page)
                    post_btn.click()
                    self.human.think(3.5, 6.0)
                    self._screenshot(page, "tweet_published")
                    logger.info("[twitter] Tweet publicado")
                    return True
            except Exception:
                pass

            for txt in ["Post", "Publicar", "Tweet"]:
                try:
                    btn = page.get_by_role("button", name=txt)
                    if btn.is_visible(timeout=2000):
                        self.human.before_click(page)
                        btn.click()
                        self.human.think(3.5, 6.0)
                        self._screenshot(page, "tweet_published")
                        logger.info("[twitter] Tweet publicado via '%s'", txt)
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
        caption_file = package_path / "instagram" / "caption.txt"

        if tweet_file.exists():
            tweet_text = tweet_file.read_text(encoding="utf-8").strip()[:280]
        elif caption_file.exists():
            tweet_text = caption_file.read_text(encoding="utf-8").strip()[:250]
        else:
            tweet_text = ""

        if not tweet_text:
            return {"platform": "twitter", "success": False, "error": "Sin texto para tweet"}

        results: dict[str, Any] = {"platform": "twitter", "success": False}

        with sync_playwright() as pw:
            # headless=False para Google OAuth — Google bloquea headless Chromium
            browser, context = self._build_context(pw, headless=False, mobile=False)
            page = context.new_page()

            try:
                self.human.navigate(page, X_URL)
                self.human.think(2.0, 4.0)

                if not self._is_logged_in(page):
                    if not self._login(page, context):
                        results["error"] = "Login fallido — configura X_USERNAME/X_PASSWORD o GOOGLE_EMAIL/GOOGLE_PASSWORD"
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
