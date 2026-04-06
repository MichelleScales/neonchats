"""
Experiment service — weighted variant selection and statistical significance.

Uses a two-proportion z-test to compare conversion rates between a control
variant (lowest version number) and each treatment variant. No external deps
required — standard library math only.
"""

import math
import random
import uuid
from typing import Any

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession


# ── Variant selection ─────────────────────────────────────────────────────────

def select_variant(variants: list[Any]) -> Any:
    """
    Weighted random selection by traffic_weight.
    Variants with higher weights are proportionally more likely to be chosen.
    """
    if not variants:
        raise ValueError("No variants to select from")
    if len(variants) == 1:
        return variants[0]

    weights = [float(v.traffic_weight or 1.0) for v in variants]
    total = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0.0
    for variant, weight in zip(variants, weights):
        cumulative += weight
        if r <= cumulative:
            return variant
    return variants[-1]


# ── Statistical significance ──────────────────────────────────────────────────

def _normal_cdf(z: float) -> float:
    """Standard normal CDF via the math.erfc approximation."""
    return 0.5 * math.erfc(-z / math.sqrt(2))


def two_prop_z_test(n1: int, k1: int, n2: int, k2: int) -> float:
    """
    Two-proportion z-test (two-tailed).

    Args:
        n1: impressions for variant 1 (control)
        k1: conversions for variant 1 (control)
        n2: impressions for variant 2 (treatment)
        k2: conversions for variant 2 (treatment)

    Returns:
        Confidence as a float 0.0–1.0 (e.g. 0.95 = 95% confident the
        difference is not due to chance).
    """
    if n1 < 1 or n2 < 1:
        return 0.0

    p1 = k1 / n1
    p2 = k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)

    if p_pool <= 0 or p_pool >= 1:
        return 0.0

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0

    z = abs(p1 - p2) / se
    p_value = 2 * (1 - _normal_cdf(z))
    confidence = max(0.0, min(1.0, 1 - p_value))
    return round(confidence, 4)


# ── Stats computation ─────────────────────────────────────────────────────────

async def compute_experiment_stats(
    db: AsyncSession,
    *,
    asset_id: uuid.UUID,
    tenant_id: uuid.UUID,
    variant_ids: list[uuid.UUID],
) -> dict[str, dict[str, Any]]:
    """
    Query analytics_events for all variants in this experiment and return
    per-variant stats: impressions, clicks, conversions, CTR, CVR.
    """
    if not variant_ids:
        return {}

    result = await db.execute(
        text("""
            SELECT
                variant_id,
                event_type,
                COUNT(*) AS cnt
            FROM analytics_events
            WHERE tenant_id = :tenant_id
              AND asset_id   = :asset_id
              AND variant_id = ANY(:variant_ids)
              AND event_type IN ('impression', 'click', 'conversion')
            GROUP BY variant_id, event_type
        """),
        {
            "tenant_id": str(tenant_id),
            "asset_id": str(asset_id),
            "variant_ids": [str(v) for v in variant_ids],
        },
    )
    rows = result.fetchall()

    stats: dict[str, dict[str, Any]] = {
        str(v): {"impressions": 0, "clicks": 0, "conversions": 0}
        for v in variant_ids
    }

    for row in rows:
        vid = str(row.variant_id)
        if vid in stats:
            stats[vid][row.event_type + "s" if row.event_type != "impression" else "impressions"] = int(row.cnt)
            # normalise: "click" → "clicks", "conversion" → "conversions"

    # Fix plural keys
    for vid, s in stats.items():
        imp = s.get("impressions", 0)
        clk = s.get("clicks", 0) or s.get("clicks", 0)
        cvr_cnt = s.get("conversions", 0)
        stats[vid]["ctr"] = round(clk / imp, 4) if imp else 0.0
        stats[vid]["cvr"] = round(cvr_cnt / imp, 4) if imp else 0.0

    return stats


async def compute_variant_stats_raw(
    db: AsyncSession,
    *,
    asset_id: uuid.UUID,
    tenant_id: uuid.UUID,
    variant_ids: list[uuid.UUID],
) -> dict[str, dict[str, int]]:
    """
    Returns raw counts per variant: {variant_id_str: {impressions, clicks, conversions}}.
    """
    if not variant_ids:
        return {}

    result = await db.execute(
        text("""
            SELECT
                variant_id::text,
                SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END) AS impressions,
                SUM(CASE WHEN event_type = 'click'      THEN 1 ELSE 0 END) AS clicks,
                SUM(CASE WHEN event_type = 'conversion' THEN 1 ELSE 0 END) AS conversions
            FROM analytics_events
            WHERE tenant_id  = :tenant_id
              AND asset_id    = :asset_id
              AND variant_id  = ANY(:variant_ids::uuid[])
            GROUP BY variant_id
        """),
        {
            "tenant_id": str(tenant_id),
            "asset_id": str(asset_id),
            "variant_ids": [str(v) for v in variant_ids],
        },
    )
    rows = result.fetchall()

    out: dict[str, dict[str, int]] = {str(v): {"impressions": 0, "clicks": 0, "conversions": 0} for v in variant_ids}
    for row in rows:
        out[row.variant_id] = {
            "impressions": int(row.impressions or 0),
            "clicks": int(row.clicks or 0),
            "conversions": int(row.conversions or 0),
        }
    return out


def enrich_stats_with_significance(
    raw: dict[str, dict[str, int]],
    control_variant_id: str,
) -> dict[str, dict[str, Any]]:
    """
    Adds CTR, CVR, and confidence (vs. control) to each variant's stats dict.
    """
    control = raw.get(control_variant_id, {"impressions": 0, "clicks": 0, "conversions": 0})
    n_ctrl = control["impressions"]
    k_ctrl = control["conversions"]

    enriched: dict[str, dict[str, Any]] = {}
    for vid, s in raw.items():
        n = s["impressions"]
        k = s["conversions"]
        clk = s["clicks"]
        enriched[vid] = {
            **s,
            "ctr": round(clk / n, 4) if n else 0.0,
            "cvr": round(k / n, 4) if n else 0.0,
            "confidence": (
                1.0 if vid == control_variant_id
                else two_prop_z_test(n_ctrl, k_ctrl, n, k)
            ),
            "is_control": vid == control_variant_id,
        }
    return enriched
