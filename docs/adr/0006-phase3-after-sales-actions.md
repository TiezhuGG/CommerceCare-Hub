# ADR-0006: Phase 3 after-sales action boundary and conservative approvals

**Status:** Accepted  
**Date:** 2026-08-05

## Context

The MVP must demonstrate safe refunds, returns, address changes, and damaged-item handling before the policy and risk agents exist. The earlier PRD describes threshold-based approval, but Phase 3 has no reliable policy-confidence or duplicate-refund-risk evaluator yet.

## Decision

Use `AfterSalesActionService` as the only creator of a durable after-sales action. It validates order ownership and action-specific fields, creates ticket/workflow/audit/outbox records in one transaction, and uses a conservative deterministic rule:

- refunds and address changes always require a Supervisor decision;
- returns require a delivered order and are automatically queued;
- damaged items create an automatically queued carrier inquiry;
- address data is represented only by a fingerprinted reference, never by raw address text.

Outbox dispatch is responsible for mock-provider writes. It records attempts, retries deterministic timeout failures up to three times, and never replays a successfully completed action.

## Consequences

The demo is intentionally safer than the eventual threshold-based policy: low-value refunds wait for approval. Phase 4 may replace the simple rule with versioned policy evidence and structured risk output, but must retain the same domain-service, idempotency, audit, approval, and outbox boundaries.
