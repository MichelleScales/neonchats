import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.models.analytics import AnalyticsEvent
from app.routers.deps import DB, CurrentUser
from app.schemas.analytics import AnalyticsSummary, ChannelMetrics, EventIngest

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/events", status_code=201)
async def ingest_event(payload: EventIngest, db: DB, user: CurrentUser):
    event = AnalyticsEvent(
        tenant_id=user.tenant_id,
        campaign_id=payload.campaign_id,
        asset_id=payload.asset_id,
        execution_run_id=payload.execution_run_id,
        event_type=payload.event_type,
        channel=payload.channel,
        value=payload.value,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        properties=payload.properties,
    )
    db.add(event)
    return {"status": "ok"}


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    db: DB,
    user: CurrentUser,
    campaign_id: uuid.UUID | None = None,
):
    q = select(AnalyticsEvent).where(AnalyticsEvent.tenant_id == user.tenant_id)
    if campaign_id:
        q = q.where(AnalyticsEvent.campaign_id == campaign_id)
    result = await db.execute(q)
    events = result.scalars().all()

    def count(et: str) -> int:
        return sum(1 for e in events if e.event_type == et)

    total_spend = sum(float(e.value or 0) for e in events if e.event_type == "spend")
    sends = count("send")
    opens = count("open")
    clicks = count("click")
    conversions = count("conversion")

    # Per-channel breakdown
    channels: dict[str, dict] = {}
    for e in events:
        ch = e.channel or "unknown"
        if ch not in channels:
            channels[ch] = {"sends": 0, "opens": 0, "clicks": 0, "conversions": 0, "spend": 0.0}
        if e.event_type in channels[ch]:
            channels[ch][e.event_type] += 1
        if e.event_type == "spend":
            channels[ch]["spend"] += float(e.value or 0)

    channel_metrics = []
    for ch, m in channels.items():
        s = m["sends"] or 1
        channel_metrics.append(ChannelMetrics(
            channel=ch,
            sends=m["sends"],
            opens=m["opens"],
            clicks=m["clicks"],
            conversions=m["conversions"],
            spend=m["spend"],
            open_rate=round(m["opens"] / s, 4),
            click_rate=round(m["clicks"] / s, 4),
            conversion_rate=round(m["conversions"] / s, 4),
        ))

    return AnalyticsSummary(
        campaign_id=campaign_id,
        total_sends=sends,
        total_opens=opens,
        total_clicks=clicks,
        total_conversions=conversions,
        total_spend=total_spend,
        avg_open_rate=round(opens / (sends or 1), 4),
        avg_click_rate=round(clicks / (sends or 1), 4),
        by_channel=channel_metrics,
    )
