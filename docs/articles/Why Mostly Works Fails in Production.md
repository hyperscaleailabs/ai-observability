# Why "Mostly Works" Fails in Production

---

Author: Constantine (Kostyantyn) Gurnov
Org: Hyperscale.AI
Version: 1.0 Apr 30, 2026

---

## A project management perspective on why AI systems that pass user acceptance need reliability controls before they can pass production acceptance

"Mostly works" is not a definition.

In software project management, a feature either meets its acceptance criteria or it does not. There is no shipping threshold called "mostly."

But AI systems introduce a new challenge: outputs that are semantically useful are not necessarily operationally reliable. A model that produces good answers most of the time can still fail production requirements systematically.

That gap — between "works in testing" and "works in production" — is a project management problem as much as an engineering one.

---

## The Acceptance Criteria Problem

Traditional software acceptance criteria are binary.

The login form accepts valid credentials: pass or fail. The report exports in the correct format: pass or fail. The API returns the expected response: pass or fail.

AI system acceptance criteria are different by nature.

The model returns a useful summary: sometimes. The model returns valid JSON: usually. The model includes all required fields: mostly.

"Mostly" is not an acceptance criterion. It is a deferred incident report.

When AI outputs feed downstream systems — automation pipelines, integrations, reports — the failures hidden inside "mostly" surface as production incidents. They do not surface in user acceptance testing, because human reviewers compensate for inconsistencies that automated systems cannot.

---

## The Hidden Cost of Manual Compensation

Every AI pilot that "mostly works" contains a hidden labor cost.

Someone reviews outputs before they reach the customer. Someone reruns prompts when the result looks wrong. Someone manually corrects malformed data before it enters the next system. Someone knows which use cases to avoid.

This manual compensation is invisible in demos and invisible in project reports. It appears in headcount, in delayed timelines, and in the slow erosion of team confidence in the AI system.

A project that appears on track because outputs "mostly work" may actually be accumulating manual labor debt that is not captured in any project metric.

The right project question is not: does the AI produce good outputs?

It is: does the AI produce good outputs without human intervention at a rate that justifies the automation?

---

## What "Production Ready" Means for AI Systems

For a traditional software feature, production readiness has standard definitions:

* meets acceptance criteria
* passes QA
* has rollback plan
* has monitoring in place

For an AI system, production readiness requires additional criteria:

* output validation rate meets defined threshold (e.g., 95%+ of outputs pass schema validation)
* failure recovery is bounded and observable
* telemetry exists to detect behavior changes
* human review escalation path is defined and staffed
* cost per validated output is understood
* rollback to previous prompt version is possible

A prototype applying these controls moved output success rate from 71% baseline to 100% with validation and recovery. The difference between 71% and 100% is the difference between a system that requires constant human intervention and one that can operate autonomously.

Without explicit production readiness criteria, AI projects are shipped when they "look good" in demos, not when they are safe for automation.

---

## Risk Classification for AI Deliverables

Not all AI outputs carry equal risk.

Project managers should classify AI use cases by consequence of failure.

### Low Risk

* internal summaries for human review
* draft content with mandatory human editing
* exploratory analysis with non-binding outputs

Failure is an inconvenience. "Mostly works" may be acceptable here.

### Medium Risk

* automated reports distributed to stakeholders
* customer-facing content generated without individual review
* data enrichment fed into downstream analytics

Failure affects quality and trust. Explicit validation thresholds are required.

### High Risk

* outputs that trigger automated actions
* outputs fed into financial or legal workflows
* outputs that affect customer decisions without human review

Failure has operational or legal consequence. Validation gates, bounded recovery, and escalation paths are required before production.

Risk classification should happen before development begins, not after an incident surfaces the gap.

---

## Milestones That Account for AI Reliability

Standard project milestones do not capture AI reliability progression.

A more accurate milestone model for AI projects:

**Milestone 1 — Prototype**
Model produces useful outputs in controlled conditions. Human review in loop. No production dependencies.

**Milestone 2 — Instrumented Pilot**
Structured telemetry in place. Validation rules defined. Success rate baseline established. Limited workflow integration with human oversight.

**Milestone 3 — Controlled Production**
Validation gate in place. Bounded recovery defined. Schema contracts established. Alerting configured. Output success rate meets defined threshold. Rollback procedure tested.

**Milestone 4 — Autonomous Operation**
System operates without routine human intervention. Monitoring surfaces exceptions for human review. Continuous improvement loop via telemetry-driven prompt tuning.

Projects that jump from Milestone 1 to Milestone 4 skip the engineering work that makes Milestone 4 safe.

---

## Communicating AI Risk to Stakeholders

AI reliability failures create a specific communication problem.

When a traditional feature fails, the failure is usually binary and visible: the button doesn't work, the data doesn't load, the export fails.

When an AI system fails quietly — returning structurally invalid outputs that downstream systems silently drop, or producing subtly wrong data that nobody reviews — the failure may not surface for days or weeks.

By then, the project appears complete. The AI "works." The problem is invisible until someone looks at downstream data quality or traces an incident back to an AI output that failed validation six weeks ago.

Project managers need to build visibility into AI reliability explicitly:

* weekly output validation rate as a project health metric
* failure class tracking visible to the team, not buried in logs
* incident definition that includes AI output quality failures, not just service outages
* retrospective reviews that include reliability data alongside delivery metrics

---

## Project Manager Takeaway

"Mostly works" is a project risk, not a project status.

AI systems that pass user acceptance without explicit reliability criteria are not production-ready. They are demo-ready.

The gap between demo-ready and production-ready is filled by:

* defined output validation thresholds as acceptance criteria
* telemetry that makes failure visible to the team
* recovery logic that handles failures without manual intervention
* staged production readiness milestones that include reliability gates
* risk classification that determines what level of reliability each use case requires

These are project management responsibilities, not just engineering ones.

The definition of done for an AI deliverable must include the word reliable.

---

[5]: https://sre.google/sre-book/monitoring-distributed-systems/ "Chapter 6 - Monitoring Distributed Systems"
[6]: https://opentelemetry.io/docs/ "OpenTelemetry Documentation"
[10]: https://learn.microsoft.com/en-us/azure/machine-learning/prompt-flow/how-to-monitor-generative-ai-applications "Model monitoring for generative AI applications"
[13]: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence "Artificial Intelligence Risk Management Framework"
[14]: https://www.nist.gov/itl/ai-risk-management-framework "AI Risk Management Framework | NIST"

---

Author: Constantine (Kostyantyn) Gurnov
Org: Hyperscale.AI
Version: 1.0 Apr 30, 2026
License: CC BY-NC

---
