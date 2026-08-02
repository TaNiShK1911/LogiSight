"""
S3-triggered Lambda handler for invoice ingestion.
Triggered when a PDF is uploaded to S3 via pre-signed URL.
Flow: S3 event → fetch PDF → Veryfi OCR → map charges → store in CockroachDB.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from datetime import date

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context) -> dict:
    """
    AWS Lambda entry point — triggered by S3 PutObject events.

    Event structure:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "logisight-invoices-hackathon"},
                "object": {"key": "invoices/tenant-123/quote-456/timestamp_file.pdf"}
            }
        }]
    }
    """
    import boto3
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    for record in event.get("Records", []):
        s3_info = record.get("s3", {})
        bucket = s3_info.get("bucket", {}).get("name", "")
        key = s3_info.get("object", {}).get("key", "")

        if not bucket or not key:
            logger.warning(f"Skipping record — missing bucket or key: {record}")
            continue

        logger.info(f"Processing invoice: s3://{bucket}/{key}")

        try:
            _process_invoice(bucket, key)
        except Exception as e:
            logger.error(f"Failed to process {key}: {e}", exc_info=True)
            # Update invoice status to 'failed' if possible
            _update_invoice_status(key, "failed")

    return {"statusCode": 200, "body": "OK"}


def _get_db_url() -> str:
    """Get sync PostgreSQL URL from environment."""
    url = os.environ.get("COCKROACHDB_URL", os.environ.get("DATABASE_URL", ""))
    if not url:
        raise RuntimeError("COCKROACHDB_URL or DATABASE_URL not set")

    if url.startswith("cockroachdb://"):
        url = url.replace("cockroachdb://", "postgresql://")
    elif "postgresql+asyncpg://" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")

    return url


def _process_invoice(bucket: str, key: str) -> None:
    """Download PDF from S3, extract via Veryfi, map charges, store in DB."""
    import boto3

    s3 = boto3.client("s3")

    # Download PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        s3.download_file(bucket, key, tmp.name)
        tmp_path = tmp.name

    try:
        # Extract invoice data via Veryfi
        from app.services.invoice_extraction import extract_invoice_with_veryfi_sync

        invoice_number, extracted_charges = extract_invoice_with_veryfi_sync(tmp_path)
        logger.info(f"Extracted: invoice_number={invoice_number}, charges={len(extracted_charges)}")
    finally:
        os.unlink(tmp_path)

    # Find the pending invoice record by s3_key
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(_get_db_url())

    with Session(engine) as session:
        from sqlalchemy import text

        row = session.execute(
            text("SELECT id, quote_id FROM invoices WHERE s3_key = :key"),
            {"key": key},
        ).fetchone()

        if row is None:
            logger.warning(f"No pending invoice found for s3_key={key}")
            return

        invoice_id, quote_id = row[0], row[1]

        # Get buyer_id from quote
        qrow = session.execute(
            text("SELECT buyer_id FROM quotes WHERE id = :qid"),
            {"qid": quote_id},
        ).fetchone()

        if qrow is None:
            logger.error(f"Quote {quote_id} not found")
            return

        buyer_id = qrow[0]

        # Update invoice with extracted data
        session.execute(
            text("""
                UPDATE invoices
                SET invoice_number = :num,
                    invoice_date = :dt,
                    processing_status = 'completed'
                WHERE id = :id
            """),
            {"num": invoice_number, "dt": date.today().isoformat(), "id": invoice_id},
        )

        # Insert mapped charges
        for charge in extracted_charges:
            session.execute(
                text("""
                    INSERT INTO invoice_charges
                        (invoice_id, raw_charge_name, mapping_tier, low_confidence,
                         rate, basis, qty, amount)
                    VALUES
                        (:inv_id, :raw, 'UNMAPPED', true,
                         :rate, :basis, :qty, :amount)
                """),
                {
                    "inv_id": invoice_id,
                    "raw": charge.raw_charge_name,
                    "rate": charge.rate,
                    "basis": charge.basis,
                    "qty": charge.qty,
                    "amount": charge.amount,
                },
            )

        # Write copilot memory event
        session.execute(
            text("""
                INSERT INTO copilot_memory_events
                    (id, session_id, tenant_id, event_type, content)
                VALUES
                    (:id, :session_id, :tenant_id, 'invoice_ingested', :content)
            """),
            {
                "id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "tenant_id": buyer_id,
                "content": json.dumps({
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "charge_count": len(extracted_charges),
                    "s3_key": key,
                }),
            },
        )

        session.commit()
        logger.info(f"✓ Invoice {invoice_id} processed: {len(extracted_charges)} charges")


def _update_invoice_status(s3_key: str, status: str) -> None:
    """Update invoice processing status (best effort)."""
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session

        engine = create_engine(_get_db_url())
        with Session(engine) as session:
            session.execute(
                text("UPDATE invoices SET processing_status = :st WHERE s3_key = :key"),
                {"st": status, "key": s3_key},
            )
            session.commit()
    except Exception as e:
        logger.warning(f"Failed to update invoice status: {e}")
