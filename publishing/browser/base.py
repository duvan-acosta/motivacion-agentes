"""Base para publicadores de navegador con comportamiento humano."""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright

from publishing.browser.google_auth import GoogleAuthHelper
from utils.config import get_settings

logger = logging.getLogger(__name__)


class HumanBehavior:
    """Delays y acciones que imitan a un usuario real — navegación lenta anti-bot."""

    @staticmethod
    def pause(min_s: float = 0.8, max_s: float = 2.5) -> None:
        time.sleep(random.uniform(min_s, max_s))

    @staticmethod
    def think(min_s: float = 2.0, max_s: float = 5.0) -> None:
        """Pausa larga — como cuando un humano lee algo antes de actuar."""
        time.sleep(random.uniform(min_s, max_s))

    @staticmethod
    def read_page(min_s: float = 3.0, max_s: float = 7.0) -> None:
        """Simula que el usuario está leyendo el contenido de la página."""
        time.sleep(random.uniform(min_s, max_s))

    @staticmethod
    def hesitate() -> None:
        """Micro-pausa de duda antes de hacer algo — muy humano."""
        time.sleep(random.uniform(0.3, 0.9))

    @staticmethod
    def type_text(page: Page, selector: str, text: str) -> None:
        page.click(selector)
        time.sleep(random.uniform(0.4, 0.9))
        for char in text:
            page.keyboard.type(char)
            # Velocidad variable: más lento en puntuación, errores ocasionales
            delay = random.uniform(0.06, 0.22)
            if char in ".,!?@":
                delay += random.uniform(0.05, 0.15)
            time.sleep(delay)

    @staticmethod
    def type_into_element(element: Any, text: str) -> None:
        element.click()
        time.sleep(random.uniform(0.4, 0.8))
        for char in text:
            element.type(char)
            time.sleep(random.uniform(0.05, 0.18))

    @staticmethod
    def scroll(page: Page, min_px: int = 100, max_px: int = 400) -> None:
        """Scroll suave en dos pasos — más natural que uno brusco."""
        delta = random.randint(min_px, max_px)
        half = delta // 2
        page.mouse.wheel(0, half)
        time.sleep(random.uniform(0.15, 0.4))
        page.mouse.wheel(0, delta - half)
        time.sleep(random.uniform(0.3, 0.8))

    @staticmethod
    def move_mouse_randomly(page: Page, width: int = 1920, height: int = 1080) -> None:
        """Mueve el mouse siguiendo una trayectoria en dos puntos intermedios."""
        for _ in range(random.randint(1, 3)):
            x = random.randint(80, width - 80)
            y = random.randint(120, height - 120)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.08, 0.25))

    @staticmethod
    def navigate(page: Page, url: str, wait: str = "domcontentloaded") -> None:
        """Navega a una URL y hace una pausa de lectura realista."""
        page.goto(url, wait_until=wait)
        # Pausa inicial de orientación
        time.sleep(random.uniform(1.5, 3.5))
        # Scroll pequeño para simular que comienza a leer
        if random.random() > 0.4:
            page.mouse.wheel(0, random.randint(50, 200))
            time.sleep(random.uniform(0.5, 1.2))

    @staticmethod
    def before_click(page: Page, x: int = 0, y: int = 0) -> None:
        """Mueve el mouse hacia el elemento antes de hacer clic — más natural."""
        if x and y:
            # Movimiento en dos pasos hacia el objetivo
            mid_x = x + random.randint(-40, 40)
            mid_y = y + random.randint(-30, 30)
            page.mouse.move(mid_x, mid_y)
            time.sleep(random.uniform(0.12, 0.3))
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.08, 0.2))
        else:
            time.sleep(random.uniform(0.2, 0.5))


class BaseBrowserPublisher(GoogleAuthHelper):
    """Publicador base con Playwright, persistencia de sesión y OAuth Google."""

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
        # Sesión Google compartida entre todas las plataformas
        self.google_session_file = self.sessions_dir / "google_session.json"

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
            # Velocidad de red reducida simula conexión celular colombiana
            # (evita cargas instantáneas que delatan bots)
        )
        # Ocultar señales de automatización + simular hardware real
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-CO','es','en'] });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
            window.chrome = { runtime: {}, loadTimes: () => ({}), csi: () => ({}) };
            // Ocultar Playwright en propiedades de performance
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (params) =>
                params.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(params);
        """)
        self._load_cookies(context)
        return browser, context

    def _load_cookies(self, context: BrowserContext) -> bool:
        loaded = 0
        # Cargar siempre las cookies Google (sesión compartida)
        if self.google_session_file.exists():
            try:
                g_cookies = json.loads(self.google_session_file.read_text(encoding="utf-8"))
                context.add_cookies(g_cookies)
                loaded += len(g_cookies)
            except Exception as exc:
                logger.warning("[%s] No se pudieron cargar cookies Google: %s", self.PLATFORM, exc)
        # Cargar cookies específicas de la plataforma
        if self.session_file.exists():
            try:
                cookies = json.loads(self.session_file.read_text(encoding="utf-8"))
                context.add_cookies(cookies)
                loaded += len(cookies)
            except Exception as exc:
                logger.warning("[%s] No se pudieron cargar cookies: %s", self.PLATFORM, exc)
        if loaded:
            logger.info("[%s] Sesión cargada (%d cookies)", self.PLATFORM, loaded)
        return loaded > 0

    def _save_cookies(self, context: BrowserContext) -> None:
        cookies = context.cookies()
        # Separar cookies Google de las de plataforma
        google_domains = {"google.com", "accounts.google.com", "myaccount.google.com", "youtube.com"}
        g_cookies = [c for c in cookies if any(d in (c.get("domain", "")) for d in google_domains)]
        p_cookies = [c for c in cookies if not any(d in (c.get("domain", "")) for d in google_domains)]
        if g_cookies:
            self.google_session_file.write_text(
                json.dumps(g_cookies, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        if p_cookies:
            self.session_file.write_text(
                json.dumps(p_cookies, ensure_ascii=False, indent=2), encoding="utf-8"
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
