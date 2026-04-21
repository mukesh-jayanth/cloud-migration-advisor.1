# AI Methodology: The Glass-Box Approach to Cloud Migration Advisory

## Overview

The Cloud Migration Decision Support System (CMDSS) makes consequential financial and infrastructure recommendations to enterprise teams. This document explains *why* we deliberately chose a **Glass-Box (Interpretability-First)** design over a conventional Black-Box machine learning model.

---

## The Core Argument: Trust Over Accuracy

In consumer AI applications (image classification, music recommendations), a 5% accuracy improvement from a complex neural network is clearly valuable. The user does not need to understand *why* the system recommended a song.

**Enterprise decision support is fundamentally different.**

When a system tells an enterprise team to move 500 servers to the cloud at a cost of ₹4.2 Crore, the team *must* understand why. They need to:

- Justify the decision to their CFO.
- Audit the inputs for errors before committing.
- Validate that the model's "reasoning" aligns with their specific operational context.

A Black-Box model that outputs a prediction with 87% confidence but no explanation is **useless** in this context — or worse, dangerous.

> **Our position:** In enterprise decision support, a traceable, honest "B" recommendation beats an unexplainable "A" prediction every time.

---

## Glass-Box vs. Black-Box: A Direct Comparison

| Dimension | Black-Box ML (e.g., Decision Tree on Synthetic Data) | Glass-Box Rules (Our Approach) |
|---|---|---|
| **Accuracy** | High on training data, unknown on real data | Directly reflects domain expertise |
| **Explainability** | Post-hoc XAI approximations (SHAP, LIME) | Every recommendation links to a specific rule |
| **Trust** | Low — "The model said so" | High — "Your 3% CPU utilisation triggered this" |
| **Auditability** | Requires ML expertise to audit weights | Any engineer can read and verify the logic |
| **Data dependency** | Requires labelled training data (often synthetic) | Requires domain expert knowledge |
| **Failure mode** | Silent, confident, wrong | Explicit, traceable, correctable |
| **Regulatory** | Difficult to justify to auditors | Fully auditable rule chain |

---

## Our Architecture: The AI System Auditor

Rather than training a model to predict *what strategy to use* (a question already answered by simple business rules), we focused the AI on what humans genuinely *cannot* compute manually at scale:

### 1. Zombie Server Anomaly Detection (Phase 1)
- **What it does:** Scans server inventory for machines with large resource allocations but near-zero CPU utilization.
- **Why it matters:** Prevents the migration of "waste." An enterprise migrating 128 GB RAM servers at 1% utilization directly to the cloud is not migrating — they are paying cloud prices for a data centre problem.
- **Explainability:** Every flagged server has a severity score derived from exactly three metrics: RAM, vCPU count, and CPU utilisation %. The score is visible and auditable.

### 2. NLP Risk Classifier (Phase 3)
- **What it does:** Uses keyword-intent matching (a transparent NLP technique) to extract migration concerns from free-text input.
- **Why it matters:** Structured risk sliders cannot capture nuanced concerns like "our team has never used Kubernetes." Natural language can.
- **Explainability:** Every detected risk category shows the exact matched keywords and the probability adjustments applied.

### 3. Friction & Failure Probability Engine (Phase 5)
- **What it does:** Calculates a project failure probability using an additive, weighted penalty model. Each risk factor (strategy complexity, budget sensitivity, zombie debt, NLP risk score, team capability) applies a named, documented penalty.
- **Why it matters:** It acts as an "honest brake." Even if the financial analysis says "migrate," the Friction Engine may say "your team profile and timeline make this a High-Risk project."
- **Explainability:** A waterfall chart shows every penalty factor as a named, quantified bar. The user can see exactly which factors drove the final risk tier.

---

## The AI Ethics Angle: Interpretability as a Feature

The AI research community increasingly recognises that interpretability is not just a nice-to-have — it is an ethical obligation in high-stakes domains.

Our design aligns with three key principles from the EU AI Act (2024) High-Risk System guidelines:

1. **Transparency**: Users must be able to understand the system's logic.
2. **Human Oversight**: Recommendations must be challengeable by domain experts.
3. **Accountability**: There must be a clear audit trail from input to output.

A Black-Box model trained on synthetic data would fail all three. Our Glass-Box engine satisfies all three by design.

---

## Audit Trail

Every engine decision is logged to `logs/audit.log`. A sample entry looks like:

```
2026-04-21 14:30:11 INFO  [cost_engine]    TCO calculated: 20 servers | ₹83.3L annual OpEx | ₹2.49Cr 3-Year TCO
2026-04-21 14:30:12 INFO  [cloud_engine]   Best provider: GCP (on_demand) | ₹61.2L/yr | Saves 26.5% vs on-prem
2026-04-21 14:30:12 INFO  [zombie_detector] 1 zombie detected: server-pool [High] — 64GB RAM @ 2% CPU
2026-04-21 14:30:13 INFO  [rule_engine]    Strategy: Lift-and-Shift | DR: Cold DR | Inputs: compliance=low, downtime=high, growth=low
2026-04-21 14:30:14 INFO  [predict_strategy] Failure probability: 38.5% [High] — Migration Premium Penalty +0.15, Zombie Debt Penalty +0.08
```

This log can be presented to any stakeholder as a complete, deterministic record of the system's reasoning.

---

## Conclusion

We made a deliberate, principled choice to build a Glass-Box system. It is not a limitation — it is a design philosophy. In a domain where the cost of a wrong recommendation is measured in Crores and months of engineering time, the ability to trace, challenge, and validate every output is the most important feature we could build.
