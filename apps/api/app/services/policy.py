"""
Policy checker — enforces brand, claims, PII, and link rules on generated content.
Phase 1: rule-based. Phase 3: pluggable OPA integration.
"""

import re
from typing import Any


def check_banned_phrases(text: str, banned_phrases: list[str]) -> list[str]:
    """Return list of banned phrases found in text (case-insensitive)."""
    found = []
    lower = text.lower()
    for phrase in banned_phrases:
        if phrase.lower() in lower:
            found.append(phrase)
    return found


_PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email_address"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone_number"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
]


def check_pii(text: str) -> list[dict[str, str]]:
    """Detect obvious PII patterns in generated content."""
    hits = []
    for pattern, label in _PII_PATTERNS:
        if re.search(pattern, text):
            hits.append({"type": label, "pattern": pattern})
    return hits


def check_claims(text: str, claims_policy: dict[str, Any]) -> list[str]:
    """Flag content that uses forbidden claims."""
    forbidden: list[str] = claims_policy.get("forbidden_claims", [])
    warnings = []
    lower = text.lower()
    for claim in forbidden:
        if claim.lower() in lower:
            warnings.append(claim)
    return warnings


def run_policy_checks(
    body_text: str,
    *,
    banned_phrases: list[str],
    claims_policy: dict[str, Any],
) -> dict[str, Any]:
    banned_hits = check_banned_phrases(body_text, banned_phrases)
    pii_hits = check_pii(body_text)
    claim_hits = check_claims(body_text, claims_policy)

    return {
        "brand": "fail" if banned_hits else "pass",
        "pii": "fail" if pii_hits else "pass",
        "claims": "fail" if claim_hits else "pass",
        "banned_phrase_flags": banned_hits,
        "pii_flags": pii_hits,
        "claim_warnings": claim_hits,
        "passed": not (banned_hits or pii_hits or claim_hits),
    }
