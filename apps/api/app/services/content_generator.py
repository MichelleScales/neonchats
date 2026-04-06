"""
Content generation service.
Routes to Anthropic or OpenAI based on config and data classification.
Applies voice pack context and runs policy checks on output.
"""

import hashlib
import json
from typing import Any

import anthropic
import openai

from app.config import get_settings
from app.services.policy import run_policy_checks

settings = get_settings()


def _body_to_text(body: dict[str, Any]) -> str:
    """Flatten a body dict to plain text for policy checking."""
    return " ".join(str(v) for v in body.values() if v)


def _build_system_prompt(voice_pack_data: dict[str, Any] | None) -> str:
    base = (
        "You are an expert marketing copywriter. "
        "Generate compelling, on-brand marketing content. "
        "Return output as a JSON object matching the requested format."
    )
    if not voice_pack_data:
        return base

    style = voice_pack_data.get("style_summary", "")
    vocab = voice_pack_data.get("vocabulary", [])
    banned = voice_pack_data.get("banned_phrases", [])

    additions = []
    if style:
        additions.append(f"Brand voice: {style}")
    if vocab:
        additions.append(f"Preferred vocabulary: {', '.join(vocab[:20])}")
    if banned:
        additions.append(f"Never use these phrases: {', '.join(banned[:20])}")

    return base + "\n\n" + "\n".join(additions)


def _build_user_prompt(
    asset_type: str,
    campaign_context: dict[str, Any],
    brief: str | None,
    canon_examples: list[str],
) -> str:
    ctx_parts = [f"Campaign: {campaign_context.get('name', '')}"]
    if campaign_context.get("goal"):
        ctx_parts.append(f"Goal: {campaign_context['goal']}")
    if campaign_context.get("audience_summary"):
        ctx_parts.append(f"Audience: {campaign_context['audience_summary']}")
    offer = campaign_context.get("offer", {})
    if offer:
        ctx_parts.append(f"Offer: {json.dumps(offer)}")
    if brief:
        ctx_parts.append(f"Additional brief: {brief}")

    if canon_examples:
        ctx_parts.append("\nCanon examples (match this style):")
        for i, ex in enumerate(canon_examples[:3], 1):
            ctx_parts.append(f"Example {i}: {ex[:500]}")

    format_instructions = {
        "email": '{"subject": "...", "preheader": "...", "html_body": "...", "text_body": "..."}',
        "social_post": '{"caption": "...", "hashtags": ["...", "..."], "image_prompt": "..."}',
        "landing_page": '{"headline": "...", "subheadline": "...", "cta": "...", "sections": []}',
        "ad_copy": '{"headline": "...", "description": "...", "cta": "..."}',
    }.get(asset_type, '{"content": "..."}')

    return "\n".join(ctx_parts) + f"\n\nGenerate {asset_type} content. Return JSON: {format_instructions}"


async def generate_variants(
    *,
    asset_type: str,
    campaign_context: dict[str, Any],
    brief: str | None,
    variant_count: int,
    voice_pack_data: dict[str, Any] | None,
    canon_examples: list[str],
    banned_phrases: list[str],
    claims_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    system_prompt = _build_system_prompt(voice_pack_data)
    user_prompt = _build_user_prompt(asset_type, campaign_context, brief, canon_examples)
    prompt_hash = hashlib.sha256((system_prompt + user_prompt).encode()).hexdigest()[:16]

    variants = []
    for i in range(variant_count):
        body = await _call_model(system_prompt, user_prompt + f"\n\nVariant {i + 1} of {variant_count}.")
        body_text = _body_to_text(body)
        policy = run_policy_checks(body_text, banned_phrases=banned_phrases, claims_policy=claims_policy)

        variants.append({
            "body": body,
            "model_used": f"{settings.default_model_provider}/{settings.default_external_model}",
            "prompt_hash": prompt_hash,
            "banned_phrase_flags": policy["banned_phrase_flags"],
            "claim_warnings": policy["claim_warnings"],
            "quality_score": _estimate_quality(body, asset_type),
        })

    return variants


async def _call_model(system: str, user: str) -> dict[str, Any]:
    if settings.default_model_provider == "anthropic":
        return await _call_anthropic(system, user)
    if settings.default_model_provider == "moonshot":
        return await _call_moonshot(system, user)
    return await _call_openai(system, user)


async def _call_anthropic(system: str, user: str) -> dict[str, Any]:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.default_external_model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = message.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"content": raw}


async def _call_moonshot(system: str, user: str) -> dict[str, Any]:
    client = openai.AsyncOpenAI(
        api_key=settings.moonshot_api_key,
        base_url=settings.moonshot_base_url,
    )
    response = await client.chat.completions.create(
        model=settings.default_external_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"content": raw}


async def _call_openai(system: str, user: str) -> dict[str, Any]:
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"content": raw}


def _estimate_quality(body: dict[str, Any], asset_type: str) -> float:
    """Simple heuristic quality score 0–10."""
    text = _body_to_text(body)
    score = 5.0
    if len(text) > 50:
        score += 1.0
    if len(text) > 200:
        score += 1.0
    if asset_type == "email" and "subject" in body and body["subject"]:
        score += 1.0
    if asset_type == "email" and "html_body" in body and len(body.get("html_body", "")) > 100:
        score += 1.0
    return min(score, 10.0)
