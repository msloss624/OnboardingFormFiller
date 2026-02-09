"""
Storage abstraction — Azure Blob in production, local filesystem in dev.
When BLOB_CONNECTION_STRING is set, files go to Azure Blob Storage.
Otherwise, they're saved to the local `generated/` directory.
"""
from __future__ import annotations
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

from backend.config import get_config

logger = logging.getLogger(__name__)

CONTAINER_NAME = "exports"
LOCAL_DIR = Path(__file__).parent.parent / "generated"
LOCAL_DIR.mkdir(exist_ok=True)


def _get_blob_client():
    """Lazy-import and return a BlobServiceClient, or None if not configured."""
    config = get_config()
    if not config.blob_connection_string:
        return None
    from azure.storage.blob import BlobServiceClient
    return BlobServiceClient.from_connection_string(config.blob_connection_string)


def _ensure_container(service_client):
    """Create the exports container if it doesn't exist."""
    container = service_client.get_container_client(CONTAINER_NAME)
    try:
        container.get_container_properties()
    except Exception:
        container.create_container()
    return container


def upload_excel(blob_path: str, file_bytes: bytes) -> str:
    """
    Upload an Excel file. Returns the storage path (blob path or local path).
    """
    service = _get_blob_client()
    if service:
        container = _ensure_container(service)
        blob = container.get_blob_client(blob_path)
        from azure.storage.blob import ContentSettings
        blob.upload_blob(
            file_bytes,
            overwrite=True,
            content_settings=ContentSettings(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        logger.info(f"Uploaded to blob: {blob_path}")
        return blob_path
    else:
        local_path = LOCAL_DIR / blob_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(file_bytes)
        logger.info(f"Saved locally: {local_path}")
        return str(local_path)


def download_excel(blob_path: str) -> Optional[bytes]:
    """
    Download an Excel file. Returns bytes or None if not found.
    """
    service = _get_blob_client()
    if service:
        container = _ensure_container(service)
        blob = container.get_blob_client(blob_path)
        try:
            stream = blob.download_blob()
            return stream.readall()
        except Exception:
            logger.warning(f"Blob not found: {blob_path}")
            return None
    else:
        # Try the path directly first, then under LOCAL_DIR
        for candidate in [Path(blob_path), LOCAL_DIR / blob_path]:
            if candidate.exists():
                return candidate.read_bytes()
        logger.warning(f"Local file not found: {blob_path}")
        return None


def get_download_url(blob_path: str, expiry_hours: int = 1) -> Optional[str]:
    """
    Generate a time-limited SAS URL for direct download (Azure only).
    Returns None in local mode — caller should stream the file instead.
    """
    service = _get_blob_client()
    if not service:
        return None
    from datetime import datetime, timedelta, timezone
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions
    container = _ensure_container(service)
    sas = generate_blob_sas(
        account_name=service.account_name,
        container_name=CONTAINER_NAME,
        blob_name=blob_path,
        account_key=service.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
    )
    return f"{container.get_blob_client(blob_path).url}?{sas}"
