"""
MCP Gateway — Connector base class.

Every provider adapter inherits from ConnectorAdapter and implements:
  - validate(credentials) → ConnectorStatus
  - publish(payload, credentials) → ConnectorResult
  - get_job_status(provider_job_id, credentials) → str

ConnectorPayload is the normalised input the gateway builds from a ContentVariant.
ConnectorResult is the normalised output the gateway records on ConnectorJob.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConnectorPayload:
    """Normalised dispatch payload — built by the gateway from variant body + campaign context."""
    provider: str
    channel: str
    campaign_id: str
    asset_id: str
    execution_run_id: str
    # Content fields — subset used depends on channel
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    headline: str = ""
    description: str = ""
    cta: str = ""
    image_url: str = ""
    to_emails: list[str] = field(default_factory=list)
    # Provider-specific overrides
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorResult:
    """Normalised result from a provider dispatch call."""
    success: bool
    provider_job_id: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    # Final status string written to connector_jobs
    status: str = "delivered"   # delivered | failed


@dataclass
class ConnectorStatus:
    """Result of validate() — connection health check."""
    connected: bool
    provider: str
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ConnectorAdapter(ABC):
    """
    Abstract base for every MCP connector.
    Subclasses receive credentials as a plain dict (decrypted at call time).
    """

    provider: str = ""
    supported_channels: list[str] = []

    @abstractmethod
    async def validate(self, credentials: dict[str, Any]) -> ConnectorStatus:
        """Verify the credentials work by hitting the provider's auth/account endpoint."""
        ...

    @abstractmethod
    async def publish(self, payload: ConnectorPayload, credentials: dict[str, Any]) -> ConnectorResult:
        """Dispatch content to the provider. Must be idempotent where possible."""
        ...

    async def get_job_status(self, provider_job_id: str, credentials: dict[str, Any]) -> str:
        """
        Poll the provider for final status of an async job.
        Return one of: queued | dispatched | delivered | failed
        Default implementation returns 'delivered' for providers with sync APIs.
        """
        return "delivered"
