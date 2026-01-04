from __future__ import annotations

from dataclasses import dataclass

import aioboto3
from botocore.config import Config as BotoConfig

from app.config import Settings


class ObjectStorageConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ObjectStorageConfig:
    endpoint: str | None
    bucket: str
    access_key: str
    secret_key: str
    region: str

    @staticmethod
    def from_settings(settings: Settings) -> "ObjectStorageConfig":
        if not settings.object_storage_bucket:
            raise ObjectStorageConfigError(
                "OBJECT_STORAGE_BUCKET is required when object storage is enabled"
            )
        if not settings.object_storage_access_key:
            raise ObjectStorageConfigError(
                "OBJECT_STORAGE_ACCESS_KEY is required when object storage is enabled"
            )
        if not settings.object_storage_secret_key:
            raise ObjectStorageConfigError(
                "OBJECT_STORAGE_SECRET_KEY is required when object storage is enabled"
            )

        return ObjectStorageConfig(
            endpoint=settings.object_storage_endpoint,
            bucket=settings.object_storage_bucket,
            access_key=settings.object_storage_access_key,
            secret_key=settings.object_storage_secret_key,
            region=settings.object_storage_region,
        )


class ObjectStorageService:
    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.object_storage_enabled
        self._config = ObjectStorageConfig.from_settings(settings) if self._enabled else None

    def _require_enabled(self) -> ObjectStorageConfig:
        if not self._enabled or self._config is None:
            raise RuntimeError("Object storage is not enabled (set OBJECT_STORAGE_ENABLED=true)")
        return self._config

    def _client_kwargs(self, config: ObjectStorageConfig) -> dict:
        return {
            "service_name": "s3",
            "endpoint_url": config.endpoint,
            "aws_access_key_id": config.access_key,
            "aws_secret_access_key": config.secret_key,
            "region_name": config.region,
            "config": BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        }

    async def upload_bytes(
        self,
        *,
        object_key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        config = self._require_enabled()
        session = aioboto3.Session()
        async with session.client(**self._client_kwargs(config)) as s3:
            await s3.put_object(
                Bucket=config.bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )

    async def download_bytes(self, *, object_key: str) -> bytes:
        config = self._require_enabled()
        session = aioboto3.Session()
        async with session.client(**self._client_kwargs(config)) as s3:
            response = await s3.get_object(Bucket=config.bucket, Key=object_key)
            body = response["Body"]
            return await body.read()

    async def delete_object(self, *, object_key: str) -> None:
        config = self._require_enabled()
        session = aioboto3.Session()
        async with session.client(**self._client_kwargs(config)) as s3:
            await s3.delete_object(Bucket=config.bucket, Key=object_key)
