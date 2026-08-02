"""
LLM client wrapper for LogiSight.
Uses Groq (LLaMA 3.3 70B) for the Copilot SQL agent.
Falls back to Bedrock if GROQ_API_KEY is not set.
"""

from __future__ import annotations

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
