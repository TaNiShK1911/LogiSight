"""
Amazon S3 client wrapper for LogiSight invoice file storage.
Replaces Supabase Storage with S3 pre-signed URLs.
"""

from __future__ import annotations

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _get_s3_config() -> tuple[str, str]:
    """Return (bucket_name, region)."""
    bucket = os.environ.get("S3_INVOICE_BUCKET", "logisight-invoices-hackathon")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return bucket, region


def _get_s3_client():
    """Return a boto3 S3 client."""
    _, region = _get_s3_config()
    return boto3.client("s3", region_name=region)


def generate_presigned_upload_url(
    key: str,
    content_type: str = "application/pdf",
    expires_in: int = 3600,
) -> str:
    """
    Generate a pre-signed PUT URL for uploading a file to S3.

    Args:
        key: S3 object key (e.g., "invoices/tenant-123/invoice-456.pdf")
        content_type: MIME type of the file
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Pre-signed URL string
    """
    bucket, _ = _get_s3_config()
    client = _get_s3_client()

    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        logger.info(f"Generated pre-signed upload URL for key={key}")
        return url
    except ClientError as e:
        logger.error(f"S3 pre-signed URL error: {e}")
        raise


def generate_presigned_download_url(
    key: str,
    expires_in: int = 3600,
) -> str:
    """
    Generate a pre-signed GET URL for downloading a file from S3.

    Args:
        key: S3 object key
        expires_in: URL expiration time in seconds

    Returns:
        Pre-signed URL string
    """
    bucket, _ = _get_s3_config()
    client = _get_s3_client()

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        logger.error(f"S3 download URL error: {e}")
        raise


def download_from_s3(key: str) -> bytes:
    """
    Download a file from S3 and return its content as bytes.

    Args:
        key: S3 object key

    Returns:
        File content as bytes
    """
    bucket, _ = _get_s3_config()
    client = _get_s3_client()

    try:
        response = client.get_object(Bucket=bucket, Key=key)
        data = response["Body"].read()
        logger.info(f"Downloaded {len(data)} bytes from S3 key={key}")
        return data
    except ClientError as e:
        logger.error(f"S3 download error for key={key}: {e}")
        raise


def upload_to_s3(
    key: str,
    data: bytes,
    content_type: str = "application/pdf",
) -> str:
    """
    Upload a file directly to S3 (used for local dev fallback).

    Args:
        key: S3 object key
        data: File content bytes
        content_type: MIME type

    Returns:
        S3 key of the uploaded file
    """
    bucket, _ = _get_s3_config()
    client = _get_s3_client()

    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info(f"Uploaded {len(data)} bytes to S3 key={key}")
        return key
    except ClientError as e:
        logger.error(f"S3 upload error for key={key}: {e}")
        raise
