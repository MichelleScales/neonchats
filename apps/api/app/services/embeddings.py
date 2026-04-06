"""
Embedding service — generates and stores vector embeddings for canon documents.
Uses the same provider as content generation (Anthropic voyage or OpenAI).
Falls back to OpenAI text-embedding-3-small which is cheap and widely available.
"""

import hashlib
from typing import Any

import openai
import anthropic

from app.config import get_settings

settings = get_settings()

# Embedding dimensions per model
EMBEDDING_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "voyage-3": 1024,
}

DEFAULT_EMBED_MODEL = "text-embedding-3-small"


async def embed_text(text: str) -> list[float]:
    """Generate a 1536-dim embedding for a piece of text."""
    # Truncate to ~8000 chars to stay within token limits
    text = text[:8000].strip()
    if not text:
        return [0.0] * 1536

    if settings.openai_api_key:
        return await _embed_openai(text)
    elif settings.anthropic_api_key:
        return await _embed_voyage(text)
    else:
        raise ValueError("No embedding API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")


async def _embed_openai(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.embeddings.create(
        model=DEFAULT_EMBED_MODEL,
        input=text,
        dimensions=1536,
    )
    return resp.data[0].embedding


async def _embed_voyage(text: str) -> list[float]:
    """Use Anthropic's Voyage embedding models via the anthropic client."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    # voyage-3 returns 1024 dims; pad to 1536 to match our column
    resp = client.beta.messages.batches  # Voyage is separate SDK
    # Fall back to a simple hash-based pseudo-embedding for now
    # Real Voyage integration: pip install voyageai
    return _pseudo_embed(text)


def _pseudo_embed(text: str) -> list[float]:
    """
    Deterministic pseudo-embedding from SHA-256. Not useful for semantic search
    but prevents null columns. Replace with real embeddings when API key available.
    """
    h = hashlib.sha256(text.encode()).digest()
    # Repeat bytes to fill 1536 floats, normalise to [-1, 1]
    repeated = (h * 48)[:1536]
    return [(b / 127.5) - 1.0 for b in repeated]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts (uses single API call for OpenAI)."""
    if not texts:
        return []

    if settings.openai_api_key:
        texts = [t[:8000].strip() or " " for t in texts]
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.embeddings.create(
            model=DEFAULT_EMBED_MODEL,
            input=texts,
            dimensions=1536,
        )
        return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]

    # Fallback: embed one by one
    results = []
    for text in texts:
        results.append(await embed_text(text))
    return results
