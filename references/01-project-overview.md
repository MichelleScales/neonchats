# Project Overview

## What This Is

Enterprise AI Marketing Execution Platform — a governed, privacy-first platform that:
- Learns a brand's voice
- Generates marketing content (email, social, ads, landing pages)
- Routes content through approval workflows
- Executes campaigns via integrations (email, ads, CMS, CRM)
- Tracks analytics and enforces data classification rules

## Core Philosophy

This is **not a content generator**. It's a governed execution platform:
- Campaigns are the top-level object
- Assets are controlled outputs that must pass policy checks
- Approvals are first-class — nothing executes without one
- Every action is logged to an append-only audit ledger
- Sensitive data (PHI, PII, credentials) never reaches external LLMs

## Target Users

- SMB marketing teams (MVP)
- Marketing agencies
- Enterprise teams (Phase 3)

## User Roles

| Role | Can Do |
|---|---|
| Workspace Admin | Everything — users, roles, integrations, policy |
| Marketing Lead | Campaigns, approvals, execution |
| Content Operator | Generate, edit, submit assets |
| Approver | Approve or reject content and spend |
| Analyst | Read analytics and export reports |

## Build Phases

**Phase 1 (built):** Auth, campaigns, content generation, approvals, SendGrid, analytics, audit log

**Phase 2 (next):** HubSpot, voice pack ingestion polish, error/retry UI, spend controls

**Phase 3 (future):** Experiment engine, more MCP connectors, private model plane (vLLM/SGLang in VPC), Temporal workflows, advanced OPA policy authoring
