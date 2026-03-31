# Cloud Migration Decision Support System (CMDSS)

Welcome to the **Cloud Migration Decision Support System**, an end-to-end infrastructure analysis, total cost of ownership (TCO) modeling, risk assessment, and AI strategy recommendation tool.

## 🌟 Overview
The CMDSS evaluates existing on-premise application logic, infrastructure, and costs against modern cloud equivalents to generate comprehensive, data-driven migration recommendations. By integrating rule-based logic with Machine Learning prediction models, it outputs clear financial and strategic guidance.

## 🚀 Getting Started

### Prerequisites
Make sure you have Python 3.9+ installed. 

### Installation
1. Clone the repository and navigate to the project root.
2. Install the required dependencies using pip:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```

### Quick UI Preview
*The system features a polished, dark-mode Streamlit interface out of the box.*
> *(Add screenshots here! e.g., `![Phase 1 UI](docs/screens/phase1.png)`)*

## 🏗️ Application Architecture 

The codebase is highly modular, with core logic decoupled from the UI:
- **`app.py`**: The Streamlit user interface encompassing all 5 decision phases.
- **`engines/`**:
  - `cost_engine.py`: Computes CapEx/OpEx and models TCO with a configurable financial model.
  - `cloud_cost_engine.py`: Prices instances across top providers (AWS, Azure, GCP), adjusting for pricing models (On-Demand, Reserved).
  - `risk_engine.py` & `rule_engine.py`: Handle risk-adjustment for specific business scenarios.
- **`ml/predict_strategy.py`**: An Explainable AI (XAI) engine utilizing scikit-learn's decision paths to outline *why* a cloud strategy was recommended.

## 🧭 The 5 Phases (Tabs)

1. **Phase 1 — Infrastructure & TCO**: Input current on-premise infrastructure via Excel upload, preset, or manual entry. Calculates multi-year TCO and rightsizes based on real resource utilization.
2. **Phase 2 — Cost Analysis**: Compare right-sized on-prem vs Cloud costs. Recommends the best provider and visualizes the 5-year TCO trajectory under varying cost commitments.
3. **Phase 3 — Risk Analysis**: Models the financial impact of migration risks (Downtime, Compliance, Skill Gaps) against theoretical cloud savings.
4. **Phase 4 — Strategy & Rules**: Pure rule-based engine logic to propose Lift-and-Shift, Hybrid, or Cloud-Native solutions based on specific business conditions (like compliance level).
5. **Phase 5 — ML Prediction & Reports**: A decision-tree algorithm infers your ideal migration strategy automatically. Explains the result using clear, local XAI techniques. Includes an option in Tab 6 to export HTML and CSV reports.

## 🐳 Docker Deployment
To launch the app within a structured Docker environment:
```bash
docker build -t cmdss-app .
docker run -p 8501:8501 cmdss-app
```
Access the application at `http://localhost:8501`.
