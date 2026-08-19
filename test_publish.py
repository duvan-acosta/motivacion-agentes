"""Script de prueba de publicación — corre plataforma por plataforma."""

import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

PACKAGE = Path(
    "publication_queue/2026-06-10/msg_20260610_amor_propio_221856"
)

PLATFORMS = sys.argv[1:] or ["twitter", "instagram", "facebook", "tiktok"]


def run():
    if not PACKAGE.exists():
        print(f"ERROR: paquete no encontrado: {PACKAGE}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"PAQUETE: {PACKAGE.name}")
    print(f"PLATAFORMAS: {', '.join(PLATFORMS)}")
    print(f"{'='*60}\n")

    from agents.browser_publisher import BrowserPublisherAgent
    agent = BrowserPublisherAgent()
    result = agent.publish(PACKAGE, platforms=PLATFORMS)

    print(f"\n{'='*60}")
    print("RESULTADO FINAL")
    print(f"{'='*60}")
    print(f"Éxito global : {result['success']}")
    print(f"Publicado en : {', '.join(result['published']) or 'ninguna'}")
    for platform, r in result["results"].items():
        status = "[OK]" if r.get("success") else f"[FALLO] {r.get('error','?')}"
        print(f"  {platform:12} {status}")
    print()


if __name__ == "__main__":
    run()
