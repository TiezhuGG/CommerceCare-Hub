# Demo Script

## Before the interview

1. Start the local environment with `docker compose up --build` and wait for API and Web to be healthy.
2. Open `http://localhost:3000`. Demo identities and scope are in [DEMO_ACCOUNTS.md](DEMO_ACCOUNTS.md).
3. Keep [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) and [ROADMAP.md](ROADMAP.md) ready for closing questions.

## Seven-minute walkthrough

1. **Customer Chat** — log in as `customer1@demo.local`; submit the prefilled delayed-delivery message for `CC-1001`. Show the grounded reply, workflow status, ticket ID and trace ID. Explain that the deterministic mock may classify, but only the domain workflow records business state.
2. **Customer Chat** — submit the default refund request. Its pending status demonstrates that a high-risk action does not auto-execute.
3. **Supervisor Approvals** — sign in with the prefilled supervisor identity, load the queue, and approve or reject the request. Explain idempotency, the durable outbox, and the recorded reason code.
4. **Agent Workspace** — load the operator queue and open a ticket. Point out the read-only state-event timeline and the deliberate absence of raw customer content.
5. **Ticket Timeline** — open the same ticket as Supervisor and show each explicit domain transition. This is a projection of audited state events, not an LLM narrative.
6. **Trace & Audit** — paste a trace ID from the earlier step, then load audit summaries. Explain that evidence/tool names and state transitions are available while prompts, full PII and private reasoning are intentionally unavailable.
7. **Reliability Metrics** — run the 100-case synthetic suite as Admin. Show the `healthy` SLO and explain that critical safety regressions block the release gate.

## Close

State the core architectural boundary: “Models produce validated understanding and suggestions; typed domain services, rules, approvals, idempotency and audit logs control every business write.” Then refer to the known limitations and roadmap rather than presenting roadmap items as implemented behavior.

## Repeatable rehearsal

Run `npm --prefix frontend run test:e2e` after Compose is ready. It proves the customer delivery-delay workflow and the 100-case `healthy` SLO path without using a paid external provider.
