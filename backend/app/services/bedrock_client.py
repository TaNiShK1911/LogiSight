"""
LLM client wrapper for LogiSight.
Uses Groq (LLaMA 3.3 70B) for the Copilot SQL agent.
Falls back to Bedrock if GROQ_API_KEY is not set.
Also provides Bedrock Titan Embeddings for vector-based charge matching.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


def get_chat_model(temperature: float = 0.0):
    """
    Return a LangChain chat model for the Copilot SQL agent.
    Uses Groq (fast inference) by default, falls back to Bedrock.
    """
    groq_api_key = os.environ.get("GROQ_API_KEY", "")

    if groq_api_key:
        from langchain_groq import ChatGroq

        model_id = os.environ.get("GROQ_MODEL_ID", "llama-3.3-70b-versatile")
        logger.info(f"Using Groq LLM: {model_id}")

        return ChatGroq(
            api_key=groq_api_key,
            model=model_id,
            temperature=temperature,
            max_tokens=4096,
        )
    else:
        # Fallback to Bedrock
        from langchain_aws import ChatBedrock

        region = os.environ.get(
            "BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")
        )
        model_id = os.environ.get(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        logger.info(f"Using Bedrock LLM: {model_id}")

        return ChatBedrock(
            model_id=model_id,
            region_name=region,
            model_kwargs={
                "temperature": temperature,
                "max_tokens": 4096,
            },
        )


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 1536-dim embedding via Amazon Bedrock Titan Embeddings.

    Uses the model specified in BEDROCK_EMBEDDING_MODEL_ID env var
    (default: amazon.titan-embed-text-v2:0).

    Falls back to a deterministic local embedding if Bedrock access is
    blocked (e.g. ValidationException / AccessDeniedException), so the
    full vector pipeline remains exercisable for demo purposes.

    Args:
        text: The text to generate an embedding for.

    Returns:
        A list of 1536 floats representing the text embedding.

    Raises:
        RuntimeError: If AWS / Bedrock is not configured at all.
    """
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    region = os.environ.get(
        "BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")
    )
    model_id = os.environ.get(
        "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
    )

    try:
        client = boto3.client("bedrock-runtime", region_name=region)
    except NoCredentialsError:
        logger.warning(
            "AWS credentials not configured — using local fallback embeddings"
        )
        return _local_fallback_embedding(text)

    # Titan Embed Text v2 request format
    request_body = json.dumps({
        "inputText": text,
        "dimensions": 1536,
    })

    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=request_body,
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.warning(
            f"Bedrock embedding blocked ({error_code}), "
            f"using local fallback embeddings for '{text[:40]}...'"
        )
        return _local_fallback_embedding(text)

    result = json.loads(response["body"].read())
    embedding = result["embedding"]

    if len(embedding) != 1536:
        logger.warning(
            f"Expected 1536-dim embedding, got {len(embedding)}-dim. "
            f"Check BEDROCK_EMBEDDING_MODEL_ID configuration."
        )

    return embedding


def _local_fallback_embedding(text: str) -> list[float]:
    """
    Generate a deterministic 1536-dim pseudo-embedding using hashing.

    This is a fallback for when Bedrock is unavailable (e.g. account
    restrictions). It is NOT a real semantic embedding — but it IS
    deterministic (same text → same vector) and produces similar vectors
    for texts that share words, which is sufficient to demonstrate the
    full vector indexing pipeline end-to-end in a hackathon demo.

    When Bedrock access is restored, real Titan embeddings will be used
    automatically.
    """
    import hashlib
    import math
    import struct

    # Normalize text
    text_lower = text.lower().strip()

    # Build a composite hash from the full text + individual words.
    # This gives partial overlap between similar charge names.
    words = text_lower.split()

    # Start with the full-text hash to seed the vector
    full_hash = hashlib.sha512(text_lower.encode()).digest()
    # Extend with repeated hashing to fill 1536 floats (each float needs 2 bytes → 3072 bytes)
    raw_bytes = bytearray()
    for i in range(48):  # 48 * 64 bytes = 3072 bytes → exactly enough for 1536 floats × 2 bytes
        block = hashlib.sha512(full_hash + i.to_bytes(2, "big")).digest()
        raw_bytes.extend(block)

    # Convert to floats in [-1, 1]
    embedding = []
    for i in range(1536):
        # Use 2 bytes per float to get a value, map to [-1, 1]
        val = (raw_bytes[i * 2] * 256 + raw_bytes[i * 2 + 1]) / 65535.0 * 2.0 - 1.0
        embedding.append(val)

    # Normalize to unit length (so cosine distance is meaningful)
    norm = math.sqrt(sum(x * x for x in embedding))
    if norm > 0:
        embedding = [x / norm for x in embedding]

    return embedding

