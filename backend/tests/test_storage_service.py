import pytest

from app.config import Settings
from app.services.storage_service import ObjectStorageConfigError, ObjectStorageService


@pytest.mark.asyncio
async def test_storage_disabled_raises() -> None:
    service = ObjectStorageService(Settings(object_storage_enabled=False))
    with pytest.raises(RuntimeError, match="Object storage is not enabled"):
        await service.download_bytes(object_key="anything")


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"object_storage_bucket": None}, "OBJECT_STORAGE_BUCKET"),
        ({"object_storage_access_key": None}, "OBJECT_STORAGE_ACCESS_KEY"),
        ({"object_storage_secret_key": None}, "OBJECT_STORAGE_SECRET_KEY"),
    ],
)
def test_storage_enabled_requires_required_fields(overrides: dict, expected_message: str) -> None:
    base = {
        "object_storage_enabled": True,
        "object_storage_bucket": "bucket",
        "object_storage_access_key": "access",
        "object_storage_secret_key": "secret",
        "object_storage_region": "us-east-1",
        "object_storage_endpoint": "http://127.0.0.1:9000",
    }
    base.update(overrides)

    with pytest.raises(ObjectStorageConfigError, match=expected_message):
        ObjectStorageService(Settings(**base))
