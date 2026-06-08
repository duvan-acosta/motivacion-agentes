"""Hosting público de media para publicación vía API.

Las APIs de redes sociales (Meta Graph en particular) NO aceptan subir bytes
directamente: requieren una URL pública de la imagen/video. Este módulo abstrae
el alojamiento de archivos y devuelve URLs públicas accesibles por las APIs.

Proveedor seleccionado con la variable de entorno ``MEDIA_HOST_PROVIDER``:

  - ``none``       (default) → no hay hosting; las publicaciones que lo requieran
                    caen a modo manual.
  - ``base_url``   → los archivos de ``publication_queue`` ya se sirven de forma
                    estática bajo ``MEDIA_PUBLIC_BASE_URL`` (p. ej. un nginx o un
                    bucket montado). La URL se compone con la ruta relativa.
  - ``s3``         → sube el archivo a Amazon S3 (requiere ``boto3``).
  - ``cloudinary`` → sube el archivo a Cloudinary (requiere ``cloudinary``).

Las dependencias de ``s3`` y ``cloudinary`` son opcionales y se importan de forma
perezosa: el proyecto funciona sin ellas mientras no se seleccione ese proveedor.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from utils.config import Settings, get_settings

logger = logging.getLogger(__name__)


class MediaHost(ABC):
    """Interfaz de alojamiento de media."""

    @abstractmethod
    def available(self) -> bool:
        """¿Está el proveedor correctamente configurado?"""

    @abstractmethod
    def upload(self, path: Path) -> str | None:
        """Sube el archivo y devuelve su URL pública, o ``None`` si falla."""


class NoneMediaHost(MediaHost):
    """Sin hosting: fuerza publicación manual."""

    def available(self) -> bool:
        return False

    def upload(self, path: Path) -> str | None:
        logger.info(
            "MEDIA_HOST_PROVIDER=none — no se puede generar URL pública para %s", path.name
        )
        return None


class BaseUrlMediaHost(MediaHost):
    """Los archivos ya se sirven estáticamente bajo una URL base.

    Asume que el directorio ``publication_queue`` se expone en
    ``MEDIA_PUBLIC_BASE_URL`` y compone la URL con la ruta relativa del archivo.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        return bool(self.settings.media_public_base_url)

    def upload(self, path: Path) -> str | None:
        if not self.available():
            return None
        base = self.settings.media_public_base_url.rstrip("/")
        try:
            relative = path.resolve().relative_to(self.settings.queue_path.resolve())
            return f"{base}/{relative.as_posix()}"
        except ValueError:
            # El archivo no está bajo publication_queue; usar nombre como último recurso.
            logger.warning("%s fuera de publication_queue; usando solo el nombre", path)
            return f"{base}/{path.name}"


class S3MediaHost(MediaHost):
    """Sube archivos a Amazon S3 y devuelve su URL pública."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        return bool(
            self.settings.s3_bucket
            and self.settings.aws_access_key_id
            and self.settings.aws_secret_access_key
        )

    def _key_for(self, path: Path) -> str:
        # Conserva los últimos tres segmentos (content_id/plataforma/archivo) para
        # evitar colisiones entre paquetes.
        parts = path.parts[-3:]
        return "/".join(parts)

    def upload(self, path: Path) -> str | None:
        if not self.available():
            return None
        try:
            import boto3  # type: ignore

            client = boto3.client(
                "s3",
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                region_name=self.settings.s3_region,
            )
            key = self._key_for(path)
            content_type = "video/mp4" if path.suffix.lower() == ".mp4" else "image/jpeg"
            client.upload_file(
                str(path),
                self.settings.s3_bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            if self.settings.s3_public_base_url:
                return f"{self.settings.s3_public_base_url.rstrip('/')}/{key}"
            return (
                f"https://{self.settings.s3_bucket}.s3."
                f"{self.settings.s3_region}.amazonaws.com/{key}"
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Subida a S3 falló para %s: %s", path.name, exc)
            return None


class CloudinaryMediaHost(MediaHost):
    """Sube archivos a Cloudinary y devuelve su URL segura."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        return bool(self.settings.cloudinary_url)

    def upload(self, path: Path) -> str | None:
        if not self.available():
            return None
        try:
            import cloudinary  # type: ignore
            import cloudinary.uploader  # type: ignore

            cloudinary.config(cloudinary_url=self.settings.cloudinary_url)
            resource_type = "video" if path.suffix.lower() == ".mp4" else "image"
            result = cloudinary.uploader.upload(
                str(path), resource_type=resource_type
            )
            return result.get("secure_url")
        except Exception as exc:  # noqa: BLE001
            logger.error("Subida a Cloudinary falló para %s: %s", path.name, exc)
            return None


def build_media_host(settings: Settings | None = None) -> MediaHost:
    """Construye el ``MediaHost`` según ``MEDIA_HOST_PROVIDER``."""
    settings = settings or get_settings()
    provider = settings.media_host_provider.lower().strip()
    if provider == "base_url":
        return BaseUrlMediaHost(settings)
    if provider == "s3":
        return S3MediaHost(settings)
    if provider == "cloudinary":
        return CloudinaryMediaHost(settings)
    return NoneMediaHost()


def get_media_host() -> MediaHost:
    """Atajo: media host del entorno actual."""
    return build_media_host(get_settings())
