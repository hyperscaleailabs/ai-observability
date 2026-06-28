# Observability for Non-Deterministic Services

---

Author: Constantine (Kostyantyn) Gurnov
Org: Hyperscale.AI
Version: 1.0 Apr 30, 2026

---

## An infrastructure engineering perspective on extending production monitoring to systems where identical inputs produce variable outputs

Infrastructure engineers know how to monitor services.

Health checks confirm availability. Latency metrics track response time. Error rates surface failures. Dashboards give operators visibility into system behavior.

This toolkit works well for deterministic services. A function that takes input X always produces output Y. Monitoring answers: is the function running, and is it running fast enough?

LLM services are different. The same input does not always produce the same output. Behavior is probabilistic. Outputs vary in structure, content, length, and format across identical calls.

The existing monitoring toolkit is necessary but not sufficient. Infrastructure engineers need an extended model.

---

## What Changes With Non-Deterministic Outputs

Traditional service monitoring assumes behavioral consistency.

If an API endpoint returns JSON today, it returns JSON tomorrow. If a field is present in one response, it is present in all responses. Deviations from expected behavior are bugs, and bugs produce errors that monitoring catches.

LLM services break this assumption.

The service may respond successfully — HTTP 200, normal latency — while returning:

* invalid JSON on one in five calls
* a required field absent from one in ten responses
* a markdown-wrapped payload that breaks the downstream parser
* a response that was 200 tokens yesterday and 800 tokens today for the same input

None of these produce an HTTP error. None of them trigger a traditional alert.

From the infrastructure monitoring layer, the service looks healthy. From the application layer, it is failing.

The gap between infrastructure health and output quality is the core challenge of observability for non-deterministic services.

---

## Extending the Telemetry Model

OpenTelemetry defines three pillars of observability: traces, metrics, and logs. ([OpenTelemetry][6]) Each applies to LLM workloads, but each requires extension.

### Traces

Standard traces capture request duration and service call graph.

For LLM workloads, traces should additionally capture:

* prompt version used
* model and provider identifier
* validation result per span
* normalization steps applied
* retry count and retry outcomes

This extends trace data from "how long did it take" to "what happened inside the call."

### Metrics

Standard metrics capture throughput, latency, and error rate.

For LLM workloads, add:

* `llm_output_validation_rate` — ratio of outputs passing validation
* `llm_validation_failure_class` — histogram by failure type (json_error, schema_drift, markdown_wrapper, etc.)
* `llm_normalization_rate` — how often post-processing is needed before outputs are usable
* `llm_retry_rate` — how often recovery is triggered
* `llm_retry_success_rate` — how often retries resolve the failure
* `llm_tokens_per_request` — input + output token distribution

These metrics make output quality visible at the infrastructure layer, not just at the application layer.

### Logs

Standard structured logs capture request metadata and error messages.

For LLM workloads, each log event should include:

```json
{
  "request_id": "req-4471",
  "timestamp": "2026-04-30T09:15:00Z",
  "prompt_version": "v3.0",
  "model": "gpt-4o",
  "latency_ms": 2103,
  "token_count": 412,
  "validation_status": "fail",
  "validation_errors": ["schema_drift", "missing_required_field"],
  "normalization_applied": false,
  "retry_count": 1,
  "final_status": "success"
}
```

Structured logs at this level make aggregation, alerting, and incident investigation tractable.

OpenTelemetry's observability primer defines this kind of structured telemetry as the foundation for understanding system behavior from the outside. ([OpenTelemetry][7]) For LLM services, "from the outside" must include output content, not just response codes.

---

## Latency for Probabilistic Services

Latency monitoring for LLM workloads requires percentile-level visibility.

Average latency is misleading for probabilistic services. A service that responds in 0.5s for 90% of calls and 15s for 10% of calls has an "average" latency that hides the user-facing tail.

Monitor:

* p50 — typical case latency
* p95 — elevated but common case
* p99 — edge case that users will encounter

Track these by:

* model identifier (different models have different latency profiles)
* prompt version (some prompts produce longer outputs and longer latency)
* time of day (provider capacity affects latency)

Latency spikes at p95 that do not appear at p50 indicate provider capacity issues or prompt-driven token growth.

---

## Alerting on Output Quality

Alert thresholds for LLM workloads should target output quality, not just service availability.

Recommended alerts:

| Signal | Condition | Severity |
|--------|-----------|----------|
| Validation success rate | < 90% over 5 min window | Warning |
| Validation success rate | < 75% over 5 min window | Critical |
| Retry rate | > 20% over 5 min window | Warning |
| p95 latency | > 5000ms | Warning |
| p99 latency | > 10000ms | Critical |
| Markdown wrapper rate | > 25% | Warning |
| Schema drift rate | > 10% | Warning |
| Consecutive validation failures | > 5 | Critical |

These thresholds should be calibrated against baseline telemetry for each workload. A prompt that historically validates at 95% should alert at a tighter threshold than one that historically validates at 80%.

Google's SRE approach to monitoring emphasizes that alerts should be tied to user-impacting conditions, not internal implementation details. ([sre.google][5]) For LLM workloads, user impact includes receiving invalid, malformed, or missing outputs — which traditional uptime monitoring does not capture.

---

## Rate Limiting and Provider Behavior

LLM providers apply rate limits that manifest differently than traditional service rate limits.

Traditional rate limits: request count per minute or per second.

LLM provider rate limits may include:

* requests per minute (RPM)
* tokens per minute (TPM)
* tokens per day (TPD)
* per-model limits independent of global limits

Infrastructure teams need visibility into which dimension is being constrained when rate limits trigger.

Monitor:

* rate limit errors by type
* token consumption rate trends
* time-of-day capacity patterns
* provider-specific latency degradation windows

This visibility allows capacity planning and routing decisions to be data-driven rather than reactive.

---

## Multi-Provider Routing

Production LLM workloads should not depend on a single provider.

Infrastructure design for provider resilience:

* abstract provider selection behind a routing layer
* track success rate and latency per provider in telemetry
* define automatic fallback triggers (latency threshold, error rate threshold)
* avoid hardcoding provider-specific output format assumptions

When a primary provider degrades, routing to a fallback provider should be automatic, observable, and reversible.

Microsoft's production GenAI monitoring guidance covers exactly this operational pattern — tracking per-provider metrics to support routing and capacity decisions. ([Microsoft Learn][11])

---

## Infrastructure Engineer Takeaway

Non-deterministic services require a monitoring model that extends beyond availability and latency.

The infrastructure layer needs to answer:

* Are outputs structurally valid?
* What fraction require intervention before use?
* Which failure classes appear most frequently?
* Is latency degrading at the tail?
* Which provider is performing better right now?
* Are retry rates increasing?

These questions cannot be answered by HTTP error rates and uptime dashboards alone.

The extension is not complex. Structured logs with validation outcomes. Metrics for output quality rates. Alerts on quality thresholds, not just error codes. Traces that capture what happened inside the call, not just how long it took.

That is the observability model for non-deterministic services.

---

[5]: https://sre.google/sre-book/monitoring-distributed-systems/ "Chapter 6 - Monitoring Distributed Systems"
[6]: https://opentelemetry.io/docs/ "OpenTelemetry Documentation"
[7]: https://opentelemetry.io/docs/concepts/observability-primer/ "Observability primer"
[11]: https://learn.microsoft.com/en-us/azure/foundry/concepts/observability "Observability in Generative AI - Microsoft Foundry"
[12]: https://learn.microsoft.com/en-us/azure/databricks/mlflow3/genai/eval-monitor/production-monitoring "Monitor GenAI apps in production - Azure Databricks"

---

Author: Constantine (Kostyantyn) Gurnov
Org: Hyperscale.AI
Version: 1.0 Apr 30, 2026
License: CC BY-NC

---
