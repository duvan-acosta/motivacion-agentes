"""Helper de configuración de Pinterest.

Verifica que tu token funciona y lista tus tableros con sus IDs, listos para
pegar en ``.env`` como ``PINTEREST_BOARD_ID``.

Uso (con PINTEREST_ACCESS_TOKEN ya en .env):

    python -m scripts.pinterest_setup

Dentro de Docker:

    docker compose run --rm --entrypoint python motivacion-agentes -m scripts.pinterest_setup
"""

from __future__ import annotations

import sys

import requests

from utils.config import get_settings
from utils.pinterest_auth import resolve_access_token

USER_URL = "https://api.pinterest.com/v5/user_account"
BOARDS_URL = "https://api.pinterest.com/v5/boards"


def main() -> int:
    settings = get_settings()
    token = resolve_access_token(settings)
    if not token:
        print(
            "✗ No hay credenciales de Pinterest.\n"
            "  Configura PINTEREST_ACCESS_TOKEN (o PINTEREST_REFRESH_TOKEN + "
            "PINTEREST_APP_ID + PINTEREST_APP_SECRET) en .env."
        )
        return 1

    headers = {"Authorization": f"Bearer {token}"}

    try:
        u = requests.get(USER_URL, headers=headers, timeout=30)
        u.raise_for_status()
        username = u.json().get("username", "?")
        print(f"✓ Conexión OK — cuenta @{username}")
    except Exception as exc:  # noqa: BLE001
        print(f"✗ El token no funciona: {exc}")
        return 1

    try:
        b = requests.get(BOARDS_URL, headers=headers, timeout=30)
        b.raise_for_status()
        boards = b.json().get("items", [])
    except Exception as exc:  # noqa: BLE001
        print(f"✗ No se pudieron listar los tableros: {exc}")
        return 1

    if not boards:
        print("\nNo tienes tableros todavía. Crea uno en pinterest.com y vuelve a correr esto.")
        return 0

    print("\nTus tableros — copia el ID del que quieras usar a PINTEREST_BOARD_ID:\n")
    for board in boards:
        print(f"  {board.get('id')}   →   {board.get('name')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
