"""
Supabase Storage service for file uploads (LogiSight).
"""

from __future__ import annotations

import os
from typing import BinaryIO

from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Get Supabase client with service role key for storage operations."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for storage operations"
        )

    return create_client(url, key)


async def upload_invoice_to_storage(
    file_data: bytes,
    filename: str,
    quote_id: int,
) -> str:
    """
    Upload invoice PDF to Supabase Storage.

    Args:
        file_data: PDF file bytes
        filename: Original filename
        quote_id: Quote ID for organizing files

    Returns:
        Public URL of the uploaded file

    Raises:
        RuntimeError: If upload fails
    """
    client = get_supabase_client()
    bucket_name = "invoices"

    # Create storage path: invoices/{quote_id}/{filename}
    storage_path = f"{quote_id}/{filename}"

    try:
        # Upload file to Supabase Storage
        # Note: Supabase Python client expects file-like object or bytes
        response = client.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "application/pdf"}
        )

        # Get public URL
        public_url = client.storage.from_(bucket_name).get_public_url(storage_path)

        return public_url

    except Exception as e:
        raise RuntimeError(f"Failed to upload invoice to Supabase Storage: {e}") from e


async def download_invoice_from_storage(storage_url: str) -> bytes:
    """
    Download invoice PDF from Supabase Storage.

    Args:
        storage_url: Public URL of the file

    Returns:
        File bytes

    Raises:
        RuntimeError: If download fails
    """
    client = get_supabase_client()
    bucket_name = "invoices"

    # Extract path from URL
    # URL format: https://{project}.supabase.co/storage/v1/object/public/invoices/{path}
    try:
        path = storage_url.split(f"/object/public/{bucket_name}/")[1]
    except IndexError:
        raise RuntimeError(f"Invalid storage URL format: {storage_url}")

    try:
        # Download file from Supabase Storage
        response = client.storage.from_(bucket_name).download(path)
        return response

    except Exception as e:
        raise RuntimeError(f"Failed to download invoice from Supabase Storage: {e}") from e


async def delete_invoice_from_storage(storage_url: str) -> None:
    """
    Delete invoice PDF from Supabase Storage.

    Args:
        storage_url: Public URL of the file

    Raises:
        RuntimeError: If deletion fails
    """
    client = get_supabase_client()
    bucket_name = "invoices"

    # Extract path from URL
    try:
        path = storage_url.split(f"/object/public/{bucket_name}/")[1]
    except IndexError:
        raise RuntimeError(f"Invalid storage URL format: {storage_url}")

    try:
        # Delete file from Supabase Storage
        client.storage.from_(bucket_name).remove([path])

    except Exception as e:
        raise RuntimeError(f"Failed to delete invoice from Supabase Storage: {e}") from e
