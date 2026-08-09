# Known Limitations

## Demo scope

- All commerce, shipping, refund, return, and carrier integrations are deterministic local mock providers. No real payment or carrier system is called.
- Natural-language workflow execution is intentionally limited to read-only order status and delivery-delay support. Refunds, returns, address changes, and damaged-item requests use the explicit, guarded after-sales form.
- The OpenAI-compatible structured provider is optional and unconfigured by default. The deterministic provider is the supported local demo path.
- Coze exposes only the signed, stateless customer-intake contract. The remaining workflow contracts are documented but not enabled for direct business mutation.

## Production hardening beyond this repository

- Replace demo credentials and development secrets with managed secret storage and short-lived identity integration.
- Add provider-specific retries, rate limits, distributed tracing, retention controls, and external alert delivery.
- Broaden semantic evaluation beyond the deterministic suite and add accessibility review with assistive-technology users.
