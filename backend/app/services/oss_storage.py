"""
Alibaba Cloud OSS Storage service for LogiSight.
Replaces Supabase Storage for invoice PDF upload, download, and presigned URL generation.

Requires environment variables:
  ALIBABA_ACCESS_KEY_ID
  ALIBABA_ACCESS_KEY_SECRET
  OSS_ENDPOINT       e.g. oss-ap-southeast-1.aliyuncs.com
  OSS_BUCKET_NAME    e.g. logisight-invoices
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_oss_bucket():
    """
    Create and return an authenticated Alibaba Cloud OSS Bucket client.
    Requires oss2 to be installed: pip install oss2
    """
    try:
        import oss2
    except ImportError as exc:
        raise RuntimeError(
            "oss2 package not installed. Run: pip install oss2>=2.18.0"
        ) from exc

    access_key_id = os.environ.get("ALIBABA_ACCESS_KEY_ID", "")
    access_key_secret = os.environ.get("ALIBABA_ACCESS_KEY_SECRET", "")
    endpoint = os.environ.get("OSS_ENDPOINT", "")
    bucket_name = os.environ.get("OSS_BUCKET_NAME", "")

    if not all([access_key_id, access_key_secret, endpoint, bucket_name]):
        raise RuntimeError(
            "Alibaba Cloud OSS is not fully configured. "
            "Set ALIBABA_ACCESS_KEY_ID, ALIBABA_ACCESS_KEY_SECRET, "
            "OSS_ENDPOINT, and OSS_BUCKET_NAME in your .env file."
        )

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, f"https://{endpoint}", bucket_name)
    return bucket


def _is_oss_configured() -> bool:
    """Return True if all OSS environment variables are set."""
    return all([
        os.environ.get("ALIBABA_ACCESS_KEY_ID"),
        os.environ.get("ALIBABA_ACCESS_KEY_SECRET"),
        os.environ.get("OSS_ENDPOINT"),
        os.environ.get("OSS_BUCKET_NAME"),
    ])


async def upload_invoice_to_oss(
    file_bytes: bytes,
    filename: str,
    quote_id: int,
) -> str:
    """
    Upload an invoice PDF to Alibaba Cloud OSS.

    Args:
        file_bytes: Raw PDF bytes
        filename: Original filename (used to construct the object key)
        quote_id: Quote ID for path organisation

    Returns:
        OSS object key, e.g. "invoices/42/INV-001.pdf"

    Raises:
        RuntimeError: If OSS credentials are not set or upload fails
    """
    if not _is_oss_configured():
        # Fall back to local filesystem in development (stores relative path)
        logger.warning(
            "[OSS] Alibaba Cloud OSS not configured — "
            "storing file locally as fallback"
        )
        return await _local_fallback_upload(file_bytes, filename, quote_id)

    bucket = _get_oss_bucket()
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    object_key = f"invoices/{quote_id}/{timestamp}_{filename}"

    try:
        bucket.put_object(object_key, file_bytes)
        logger.info(f"[OSS] Uploaded invoice to OSS: {object_key}")
        return object_key
    except Exception as exc:
        raise RuntimeError(f"OSS upload failed for '{object_key}': {exc}") from exc


async def download_invoice_from_oss(object_key_or_url: str) -> bytes:
    """
    Download an invoice PDF from Alibaba Cloud OSS.

    Args:
        object_key_or_url: OSS object key OR a legacy Supabase/local URL

    Returns:
        Raw PDF bytes
    """
    # If it's a Supabase URL or a local path, fall back to HTTP/disk read
    if object_key_or_url.startswith("http"):
        return await _download_from_url(object_key_or_url)
    if object_key_or_url.startswith("/"):
        return _read_local_file(object_key_or_url)

    if not _is_oss_configured():
        raise RuntimeError(
            "OSS not configured and object_key provided — cannot download."
        )

    bucket = _get_oss_bucket()
    try:
        result = bucket.get_object(object_key_or_url)
        data = result.read()
        logger.info(f"[OSS] Downloaded {len(data)} bytes from OSS: {object_key_or_url}")
        return data
    except Exception as exc:
        raise RuntimeError(f"OSS download failed for '{object_key_or_url}': {exc}") from exc


def get_invoice_download_url(object_key: str, expiry_seconds: int = 3600) -> str:
    """
    Generate a presigned download URL for an OSS object (valid for expiry_seconds).

    Args:
        object_key: OSS object key, e.g. "invoices/42/INV-001.pdf"
        expiry_seconds: URL validity in seconds (default 1 hour)

    Returns:
        Presigned URL string
    """
    if not _is_oss_configured():
        logger.warning("[OSS] OSS not configured — returning object key as URL placeholder")
        return f"/api/invoices/download/{object_key}"

    bucket = _get_oss_bucket()
    try:
        url = bucket.sign_url("GET", object_key, expiry_seconds)
        return url
    except Exception as exc:
        logger.error(f"[OSS] sign_url failed for '{object_key}': {exc}")
        return f"/api/invoices/download/{object_key}"


async def delete_invoice_from_oss(object_key: str) -> None:
    """
    Delete an invoice PDF from Alibaba Cloud OSS.

    Args:
        object_key: OSS object key to delete
    """
    if not _is_oss_configured():
        logger.warning(f"[OSS] OSS not configured — skipping delete for '{object_key}'")
        return

    bucket = _get_oss_bucket()
    try:
        bucket.delete_object(object_key)
        logger.info(f"[OSS] Deleted OSS object: {object_key}")
    except Exception as exc:
        raise RuntimeError(f"OSS delete failed for '{object_key}': {exc}") from exc


# ── Local development fallbacks ──────────────────────────────────────────────

async def _local_fallback_upload(file_bytes: bytes, filename: str, quote_id: int) -> str:
    """Store file locally when OSS is not configured (development only)."""
    import asyncio
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    quote_dir = os.path.join(uploads_dir, str(quote_id))
    os.makedirs(quote_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    local_path = os.path.join(quote_dir, f"{timestamp}_{filename}")

    def _write():
        with open(local_path, "wb") as f:
            f.write(file_bytes)

    await asyncio.to_thread(_write)
    logger.info(f"[OSS-FALLBACK] Saved locally: {local_path}")
    return local_path  # Return absolute path as key


async def _download_from_url(url: str) -> bytes:
    """Download file from an HTTP/HTTPS URL."""
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def _read_local_file(path: str) -> bytes:
    """Read a local file from disk."""
    if not os.path.exists(path):
        raise RuntimeError(f"Local file not found: {path}")
    with open(path, "rb") as f:
        return f.read()
