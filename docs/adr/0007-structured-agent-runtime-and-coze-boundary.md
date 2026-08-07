# ADR-0007: Structured Agent runtime and restricted Coze boundary

**Status:** Accepted  
**Date:** 2026-08-08

## Context

Phase 4 introduces model-backed analysis into workflows that already contain durable tickets, audit logs, provider ports, and human approvals. Raw text generation would weaken those audit and safety boundaries, and an external workflow system must not gain database or provider-write privileges.

## Decision

- Every Agent calls a `StructuredOutputProvider` and validates a Pydantic result.
- The runtime retries a validation error once; a second error, unsafe injection signal, or conflicting policy evidence yields an auditable escalation.
- Agent records retain only redacted input/output summaries, provider/model metadata, prompt key/version, attempt count, latency, and token usage.
- The deterministic mock provider is the default local implementation. An OpenAI-compatible adapter remains optional and is behind the same interface.
- Coze is treated as an untrusted caller. The executable Phase 4 endpoint is HMAC-signed, versioned, stateless `wf_customer_intake`; it returns Router analysis only and has no domain write capability.

## Consequences

The workflow gains reproducible agent behavior and failure tests without letting an LLM or external orchestrator mutate business state. Future Coze sub-flows can be enabled only after their schemas, authorization scope, and audit behavior are individually reviewed.
