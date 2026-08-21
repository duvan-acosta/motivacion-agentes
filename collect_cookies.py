"""
collect_cookies.py — Servidor local que recibe cookies desde la extensión de Chrome.

Uso:
    python collect_cookies.py

Luego en Chrome:
    1. Navega a google.com (logueado), haz clic en la extensión → Exportar
    2. Navega a youtube.com (logueado), haz clic en la extensión → Exportar
    3. Navega a tiktok.com (logueado), haz clic en la extensión → Exportar
    ... etc para instagram, x.com, facebook.com

El servidor guarda automáticamente en data/sessions/{platform}_session.json
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SESSIONS_DIR = Path("data/sessions")
PORT = 7788

GOOGLE_DOMAINS = {".google.com", "accounts.google.com", ".googleapis.com", ".youtube.com"}


class CookieReceiver(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # silenciar logs de request HTTP
        pass

    def do_OPTIONS(self):  # CORS preflight
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/save":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
            platform: str = data["platform"]
            cookies: list = data["cookies"]
        except Exception as exc:
            self._respond(400, {"error": str(exc)})
            return

        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Guardar sesión de la plataforma
        out_file = SESSIONS_DIR / f"{platform}_session.json"
        existing: list = []
        if out_file.exists():
            try:
                existing = json.loads(out_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing_keys = {(c["name"], c.get("domain", "")) for c in cookies}
        merged = cookies + [c for c in existing if (c["name"], c.get("domain", "")) not in existing_keys]
        out_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [{platform}] {len(cookies)} cookies → {out_file}")

        # Extraer cookies Google y guardar compartidas
        g_cookies = [c for c in cookies if any(d in c.get("domain", "") for d in GOOGLE_DOMAINS)]
        if g_cookies:
            g_file = SESSIONS_DIR / "google_session.json"
            g_existing: list = []
            if g_file.exists():
                try:
                    g_existing = json.loads(g_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            g_keys = {(c["name"], c.get("domain", "")) for c in g_cookies}
            g_merged = g_cookies + [c for c in g_existing if (c["name"], c.get("domain", "")) not in g_keys]
            g_file.write_text(json.dumps(g_merged, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [google_session] {len(g_cookies)} cookies Google compartidas → {g_file}")

        self._respond(200, {"message": f"Sesión de {platform} guardada ({len(cookies)} cookies)"})

    def _respond(self, code: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")


def main() -> None:
    print("=" * 55)
    print("  Mental Equilibrio — Receptor de Cookies")
    print("=" * 55)
    print(f"\nEscuchando en http://localhost:{PORT}")
    print("\nPasos:")
    print("  1. Instala la extensión en Chrome (ver instrucciones abajo)")
    print("  2. Inicia sesión en cada plataforma en tu Chrome normal")
    print("  3. Haz clic en el ícono de la extensión y luego 'Exportar'")
    print("  4. Repite para: Google, YouTube, TikTok, Instagram, X, Facebook")
    print("\nLas sesiones se guardan en:  data/sessions/")
    print("\nPara instalar la extensión:")
    print("  chrome://extensions → Activar 'Modo desarrollador'")
    print("  → 'Cargar descomprimida' → seleccionar carpeta: browser_extension/")
    print("\nCtrl+C para cerrar cuando termines.\n")

    server = HTTPServer(("localhost", PORT), CookieReceiver)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServidor cerrado.")
        # Mostrar resumen de sesiones guardadas
        saved = list(SESSIONS_DIR.glob("*_session.json")) if SESSIONS_DIR.exists() else []
        if saved:
            print("\nSesiones guardadas:")
            for f in saved:
                try:
                    n = len(json.loads(f.read_text(encoding="utf-8")))
                    print(f"  {f.name}: {n} cookies")
                except Exception:
                    print(f"  {f.name}")
        print("\nSi usas Docker, copia las sesiones al contenedor:")
        print(f"  docker cp data/sessions motivacion-agentes-scheduler-1:/app/data/sessions")
        sys.exit(0)


if __name__ == "__main__":
    main()
