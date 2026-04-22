# ☁️ Cloud Migration Decision Support System (CMDSS)

Welcome to the Cloud Migration Decision Support System, an end-to-end infrastructure analysis, total cost of ownership (TCO) modeling, risk assessment, and Failure prediction tool.

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-ff4b4b.svg)](https://streamlit.io)
[![Tests](https://img.shields.io/badge/tests-138%20passing-brightgreen.svg)](tests/)

## 🚀 Quick Start

### Prerequisites
Python 3.9 or higher.

### Local Setup
```bash
git clone https://github.com/<your-username>/cloud-migration-advisor.git
cd cloud-migration-advisor
pip install -r requirements.txt
streamlit run app.py
```
The app opens at **http://localhost:8501**.

---

## 🐳 Docker

```bash
docker build -t cmdss .
docker run -p 8501:8501 cmdss
```
Access at **http://localhost:8501**.

---

> **A Glass-Box infrastructure advisor** — every recommendation is traceable to a specific rule, formula, or risk factor. No black-box outputs, no opaque ML predictions.

---

## 🌟 What It Does

CMDSS evaluates your on-premise infrastructure and produces explainable, auditable cloud migration guidance across six sequential phases:

| Phase | Tab | What you get |
|-------|-----|-------------|
| 1 | Infrastructure & TCO | On-prem CapEx/OpEx breakdown + Zombie server detection |
| 2 | Cost Analysis | AWS / Azure / GCP annual cost comparison (right-sized) |
| 3 | Risk Analysis | Financial impact model for downtime, compliance & skill-gap risks |
| 4 | Strategy & Rules | Rule-based engine → Lift-and-Shift / Hybrid / Cloud-Native recommendation |
| 5 | Friction & Failure Predictor | NLP concern classifier + failure probability estimator |
| 6 | Export Report | Download full HTML or CSV report |

---

## 🏗️ Architecture

```
├── app.py                  # Streamlit UI — all 6 phases
├── engines/
│   ├── cost_engine.py      # On-prem CapEx / OpEx / TCO
│   ├── cloud_cost_engine.py # AWS / Azure / GCP pricing + right-sizing
│   ├── risk_engine.py      # Risk-adjusted TCO (downtime, compliance, skills)
│   ├── rule_engine.py      # Rule-based strategy recommendation + DR tiers
│   ├── decision_engine.py  # Financial comparison + ROI timeline + fragility
│   └── instance_selector.py # Cloud instance matching
├── ml/
│   ├── zombie_detector.py  # Idle/over-provisioned server flagging
│   ├── risk_nlp.py         # Keyword-based migration concern classifier
│   └── predict_strategy.py # Failure probability estimator
├── report_generator.py     # HTML + CSV export
├── pipeline.py             # End-to-end batch pipeline (non-UI)
├── config.yaml             # All financial assumptions (edit without touching code)
├── data/
│   ├── cloud_instances.csv           # Instance catalogue (AWS/Azure/GCP)
│   └── sample_infrastructure.xlsx   # Ready-to-use upload template
└── tests/
    └── test_phase6.py      # 138 tests — all passing
```

---

## 🧪 Running Tests

```bash
pytest tests/
```

Expected output: **138 passed** across Cost, Risk, Cloud Cost, Rule, Decision, Zombie, NLP, Integration, and Report Generator test classes.

---

## ⚙️ Configuration

All financial assumptions live in **`config.yaml`** — no Python changes needed:

```yaml
cost_engine:
  server_unit_cost: 5000        # $/server hardware CapEx
  admin_salary: 80000           # $/year per IT admin
  facilities_overhead_rate: 0.12 # 12% Legacy Tax (PUE, cooling, security)

cloud_cost:
  egress_and_iops_rate: 0.065   # 6.5% connectivity overhead
  managed_services_premium: 0.20 # 20% managed-services layer
```

> All costs are internally denominated in **USD** and displayed in **₹ INR** (at ₹84/USD).

---

## 📖 Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for the full design rationale — why an interpretability-first, rule-based approach was chosen over a pure ML model.
