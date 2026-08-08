# ADR-0008: Persisted deterministic evaluation runs and release gates

**Status:** Accepted  
**Date:** 2026-08-08

## Context

The application already has deterministic mock providers, schema-bound agents, and security failure paths. Phase 5 needs repeatable evidence that these controls remain intact, rather than an unversioned script result or a model-judged score that cannot be reproduced locally.

## Decision

- Seed exactly 100 active, versioned synthetic cases with the documented category distribution.
- Store each run and each case result in durable evaluation tables, then create a redacted audit event.
- Grade structured results with `deterministic-v1`; critical safety failures block the run, while lower non-critical quality produces attention.
- The evaluator is read-only with respect to business state: it has no write-provider, domain-action, approval, outbox, or customer-message capability.
- Metrics aggregate durable records and surface local SLO states; external alert delivery is intentionally outside the local demo scope.

## Consequences

Evaluation results are explainable, comparable and safe to run in the local demo. The suite measures the currently supported workflow contract rather than pretending unsupported natural-language actions were executed. Broader semantic judging and production alert integrations remain future work.
