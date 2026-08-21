"""
setup_sessions.py — Login manual UNA VEZ para guardar sesiones.

Google bloquea el Chromium de Playwright pero NO bloquea el Chrome real instalado.
Este script usa channel='chrome' para abrir el Chrome del sistema — Google lo acepta.
El usuario hace login normalmente y las cookies se guardan para uso futuro.

Uso:
    python setup_sessions.py                     # todas las plataformas
    python setup_sessions.py tiktok youtube      # plataformas especificas
    python setup_sessions.py google              # solo Google (aplica a YouTube y otros)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSIONS_DIR = Path("data/sessions")

PLATFORMS = {
    "google": {
        "url": "https://myaccount.google.com",
        "hint": (
            "1. Ingresa tu correo mentalequilibrio06@gmail.com\n"
            "2. Haz click en Siguiente\n"
            "3. Si aparece pantalla de Passkey, haz click en 'Usar una contrasena'\n"
            "4. Ingresa la contrasena y entra a tu cuenta\n"
            "5. Cuando veas tu perfil de Google (myaccount.google.com), presiona ENTER"
        ),
    },
    "youtube": {
        "url": "https://studio.youtube.com",
        "hint": (
            "1. El navegador te llevara a login de Google\n"
            "2. Selecciona la cuenta mentalequilibrio06@gmail.com\n"
            "3. Cuando veas YouTube Studio (dashboard de creadores), presiona ENTER"
        ),
    },
    "tiktok": {
        "url": "https://www.tiktok.com/login",
        "hint": (
            "1. Haz click en 'Continuar con Google'\n"
            "2. Selecciona mentalequilibrio06@gmail.com\n"
            "3. Cuando veas el feed de TikTok (ya logueado), presiona ENTER\n"
            "\nALTERNATIVA si Google falla:\n"
            "  - Ve a TikTok app -> Perfil -> Menu -> Configuracion -> Contrasena -> Agregar contrasena\n"
            "  - Establece: Mental.Equilibrio01#\n"
            "  - Luego usa 'Usar telefono, correo o nombre de usuario' en la web"
        ),
    },
    "instagram": {
        "url": "https://www.instagram.com/accounts/login/",
        "hint": (
            "PRIMERO resetea la contrasena en instagram.com/accounts/password/reset/\n"
            "Luego:\n"
            "1. Ingresa mentalequilibrio06@gmail.com\n"
            "2. Ingresa la nueva contrasena\n"
            "3. Cuando veas el feed de Instagram, presiona ENTER"
        ),
    },
    "twitter": {
        "url": "https://x.com/login",
        "hint": (
            "PRIMERO activa la cuenta desde la app de X (iOS/Android):\n"
            "  - Descarga X, inicia con Google, completa el perfil hasta ver el feed\n"
            "Luego:\n"
            "1. En el navegador que se abre, haz click en 'Sign in with Google'\n"
            "2. Selecciona mentalequilibrio06@gmail.com\n"
            "3. Cuando veas el feed de X, presiona ENTER"
        ),
    },
    "facebook": {
        "url": "https://www.facebook.com",
        "hint": (
            "1. Ingresa el correo/telefono de Facebook\n"
            "2. Ingresa la contrasena\n"
            "3. Cuando veas el feed de Facebook, presiona ENTER"
        ),
    },
}


def setup_platform(name: str) -> None:
    cfg = PLATFORMS[name]
    print(f"\n{'='*60}")
    print(f"  CONFIGURANDO: {name.upper()}")
    print(f"{'='*60}")
    print(f"\nInstrucciones:\n{cfg['hint']}\n")
    input("Presiona ENTER para abrir el navegador...")

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp_profile:
        # Usar Chrome REAL instalado (channel='chrome') con perfil temporal limpio.
        # Google acepta Chrome real via CDP; bloquea el Chromium bundled de Playwright.
        # launch_persistent_context crea un perfil de Chrome real — no un WebView.
        context = pw.chromium.launch_persistent_context(
            user_data_dir=tmp_profile,
            channel="chrome",
            headless=False,
            no_viewport=True,
            args=[
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        page = context.new_page()
        page.goto(cfg["url"], wait_until="domcontentloaded")

        print(f"\nNavegador abierto en {cfg['url']}")
        print("Completa el login manualmente en el navegador.")
        print("Cuando estés en la pantalla principal (feed/dashboard), regresa aqui.")
        input("\nPresiona ENTER para guardar las cookies...")

        cookies = context.cookies()
        out_file = SESSIONS_DIR / f"{name}_session.json"
        out_file.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        print(f"✓ {len(cookies)} cookies guardadas en {out_file}")

        # Extraer y guardar cookies Google por separado (compartidas entre plataformas)
        # Aplica a: google, youtube, tiktok (OAuth), twitter (OAuth)
        google_domains = {".google.com", "accounts.google.com", ".googleapis.com", ".youtube.com"}
        g_cookies = [c for c in cookies if any(d in c.get("domain", "") for d in google_domains)]
        if g_cookies:
            google_file = SESSIONS_DIR / "google_session.json"
            # Combinar con cookies Google existentes para no perder otras
            existing_g: list = []
            if google_file.exists():
                try:
                    existing_g = json.loads(google_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            # Merge: mantener existentes que no estén en las nuevas
            existing_keys = {(c["name"], c.get("domain", "")) for c in g_cookies}
            merged = g_cookies + [c for c in existing_g if (c["name"], c.get("domain", "")) not in existing_keys]
            google_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")
            print(f"✓ {len(g_cookies)} cookies Google guardadas/actualizadas en {google_file}")

        context.close()

    print(f"\n✓ Sesion de {name} configurada exitosamente.")


def main() -> None:
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(PLATFORMS.keys())
    invalid = [t for t in targets if t not in PLATFORMS]
    if invalid:
        print(f"Plataformas invalidas: {invalid}")
        print(f"Opciones: {list(PLATFORMS.keys())}")
        sys.exit(1)

    print("\n╔══════════════════════════════════════════╗")
    print("║  CONFIGURACION DE SESIONES — Mental Equilibrio  ║")
    print("╚══════════════════════════════════════════╝")
    print(f"\nPlataformas a configurar: {', '.join(targets)}")
    print("\nEste proceso abre un navegador para cada plataforma.")
    print("Hace login manualmente — las cookies se guardan automaticamente.")
    print("\nLas sesiones duran 30-90 dias (se renueva sola con cada publicacion).")

    for name in targets:
        setup_platform(name)
        print()

    print("\n╔══════════════════════════════════════════╗")
    print("║  ✓ SESIONES CONFIGURADAS                 ║")
    print("╚══════════════════════════════════════════╝")
    print("\nAhora el scheduler puede publicar sin necesidad de login.")
    print("Copia las sesiones al servidor si ejecutas en Docker:")
    print(f"  docker cp {SESSIONS_DIR} motivacion-agentes-scheduler-1:/app/data/sessions")


if __name__ == "__main__":
    main()
