"""Base para publicadores de navegador con comportamiento humano."""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright

from utils.config import get_settings

logger = logging.getLogger(__name__)


class HumanBehavior:
    """Delays y acciones que imitan a un usuario real."""

    @staticmethod
    def pause(min_s: float = 0.6, max_s: float = 2.2) -> None:
        time.sleep(random.uniform(min_s, max_s))

    @staticmethod
    def think(min_s: float = 1.5, max_s: float = 4.0) -> None:
        """Pausa larga — como cuando un humano lee algo antes de actuar."""
        time.sleep(random.uniform(min_s, max_s))

    @staticmethod
    def type_text(page: Page, selector: str, text: str) -> None:
        """Escribe texto carácter por carácter con velocidad variable."""
        page.click(selector)
        time.sleep(random.uniform(0.3, 0.7))
        for char in text:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.03, 0.15))

    @staticmethod
    def type_into_element(element: Any, text: str) -> None:
        """Escribe en un element handle con delays humanos."""
        element.click()
        time.sleep(random.uniform(0.3, 0.6))
        for char in text:
            element.type(char)
            time.sleep(random.uniform(0.03, 0.12))

    @staticmethod
    def scroll(page: Page, min_px: int = 80, max_px: int = 350) -> None:
        """Scroll aleatorio hacia abajo como si estuviera leyendo."""
        delta = random.randint(min_px, max_px)
        page.mouse.wheel(0, delta)
        time.sleep(random.uniform(0.2, 0.6))

    @staticmethod
    def move_mouse_randomly(page: Page, width: int = 390, height: int = 844) -> None:
        """Mueve el mouse a una posición aleatoria de la pantalla."""
        x = random.randint(50, width - 50)
        y = random.randint(100, height - 100)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.1, 0.3))


class BaseBrowserPublisher:
    """Publicador base con Playwright y persistencia de sesión."""

    PLATFORM: str = "base"
    # User-agent de iPhone 15 — funciona bien con Instagram y TikTok mobile
    MOBILE_UA: str = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.2 Mobile/15E148 Safari/604.1"
    )
    DESKTOP_UA: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    def __init__(self) -> None:
        self.settings = get_settings()
        self.human = HumanBehavior()
        root = self.settings.project_root
        self.sessions_dir = root / "data" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir = root / "data" / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.sessions_dir / f"{self.PLATFORM}_session.json"

    # ── Context ────────────────────────────────────────────────────────────────

    def _build_context(
        self,
        playwright: Playwright,
        headless: bool = True,
        mobile: bool = True,
        width: int = 0,
        height: int = 0,
    ) -> tuple[Browser, BrowserContext]:
        """Crea browser con fingerprint anti-detección."""
        browser = playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        if mobile:
            vw = width or random.choice([390, 393, 414])
            vh = height or random.choice([844, 852, 896])
            ua = self.MOBILE_UA
        else:
            vw = width or 1920
            vh = height or 1080
            ua = self.DESKTOP_UA
        viewport = {"width": vw, "height": vh}

        context = browser.new_context(
            viewport=viewport,
            user_agent=ua,
            locale="es-CO",
            timezone_id="America/Bogota",
            extra_http_headers={"Accept-Language": "es-CO,es;q=0.9,en;q=0.8"},
        )
        # Ocultar señales de automatización
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-CO','es','en'] });
            window.chrome = { runtime: {} };
        """)
        self._load_cookies(context)
        return browser, context

    def _load_cookies(self, context: BrowserContext) -> bool:
        if not self.session_file.exists():
            return False
        try:
            cookies = json.loads(self.session_file.read_text(encoding="utf-8"))
            context.add_cookies(cookies)
            logger.info("[%s] Sesión cargada (%d cookies)", self.PLATFORM, len(cookies))
            return True
        except Exception as exc:
            logger.warning("[%s] No se pudieron cargar cookies: %s", self.PLATFORM, exc)
            return False

    def _save_cookies(self, context: BrowserContext) -> None:
        cookies = context.cookies()
        self.session_file.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("[%s] Sesión guardada (%d cookies)", self.PLATFORM, len(cookies))

    # ── Screenshots ────────────────────────────────────────────────────────────

    def _screenshot(self, page: Page, label: str) -> str:
        path = self.screenshots_dir / f"{self.PLATFORM}_{label}_{int(time.time())}.png"
        try:
            page.screenshot(path=str(path))
        except Exception:
            pass
        return str(path)

    # ── Interfaz pública ───────────────────────────────────────────────────────

    def publish(self, package_path: Path) -> dict[str, Any]:
        raise NotImplementedError

    def clear_session(self) -> None:
        """Elimina la sesión guardada — fuerza re-login en el próximo ciclo."""
        if self.session_file.exists():
            self.session_file.unlink()
            logger.info("[%s] Sesión eliminada", self.PLATFORM)
