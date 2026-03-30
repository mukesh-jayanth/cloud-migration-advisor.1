import joblib
import pandas as pd
from sklearn.tree import _tree

# ─────────────────────────────────────────────
#  ML Prediction Engine + Explainable AI Layer
#  Phase 4 — Cloud Migration ML Model
#
#  Capabilities:
#    • Input validation
#    • Strategy prediction
#    • Confidence score
#    • Feature importance (global XAI)
#    • Decision path tracing (local XAI)
#    • Human-readable explanations
# ─────────────────────────────────────────────

# ── Load Model & Encoder ──────────────────────
model   = joblib.load("models/decision_tree.pkl")
encoder = joblib.load("models/label_encoder.pkl")

# ── Feature Definitions ───────────────────────
feature_names = [
    "server_count",
    "avg_cpu_util",
    "storage_tb",
    "downtime_tolerance",
    "compliance_level",
    "growth_rate",
    "budget_sensitivity"
]

# Human-readable labels
feature_labels = {
    "server_count"      : "Number of Servers",
    "avg_cpu_util"      : "CPU Utilization (%)",
    "storage_tb"        : "Storage Size (TB)",
    "downtime_tolerance": "Downtime Tolerance (hrs)",
    "compliance_level"  : "Compliance Level",
    "growth_rate"       : "Growth Rate (%)",
    "budget_sensitivity": "Budget Flexibility"
}

# Valid input ranges — mirrors generate_dataset.py
FEATURE_RANGES = {
    "server_count"      : (5,   500),
    "avg_cpu_util"      : (10,  90),
    "storage_tb"        : (1,   100),
    "downtime_tolerance": (0.5, 24),
    "compliance_level"  : (1,   3),
    "growth_rate"       : (0,   40),
    "budget_sensitivity": (1,   3)
}


# ── Input Validation ──────────────────────────
def validate_features(features: dict) -> None:
    """
    Validates that all required features are present and within
    the expected range. Raises ValueError with a clear message
    if any check fails.
    """
    missing = [f for f in feature_names if f not in features]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    errors = []
    for feature, (min_val, max_val) in FEATURE_RANGES.items():
        val = features[feature]
        if not isinstance(val, (int, float)):
            errors.append(f"  • {feature_labels[feature]}: must be a number (got {type(val).__name__})")
        elif not (min_val <= val <= max_val):
            errors.append(
                f"  • {feature_labels[feature]}: {val} is out of range "
                f"[{min_val} – {max_val}]"
            )

    if errors:
        raise ValueError("Input validation failed:\n" + "\n".join(errors))


# ── Decision Path (Local XAI) ─────────────────
def get_decision_path(sample: pd.DataFrame) -> list:
    """
    Traces the exact decision path the tree took for this sample.
    Returns a list of human-readable rule strings.
    """
    tree      = model.tree_
    feature   = tree.feature
    threshold = tree.threshold

    node_indicator = model.decision_path(sample)
    node_index     = node_indicator.indices

    rules = []
    for node_id in node_index:
        if feature[node_id] != _tree.TREE_UNDEFINED:
            feature_name = feature_names[feature[node_id]]
            label        = feature_labels[feature_name]
            thresh_val   = round(threshold[node_id], 2)

            # Determine which branch was taken
            actual_val = sample[feature_name].values[0]
            direction  = "≤" if actual_val <= thresh_val else ">"

            rules.append(
                f"{label} {direction} {thresh_val}  "
                f"(your value: {round(actual_val, 2)})"
            )

    return rules


# ── Main Prediction Function ──────────────────
def predict_strategy(features: dict) -> dict:
    """
    Accepts a dict of enterprise features, validates them,
    predicts the migration strategy, and returns full XAI output.

    Returns:
        {
            "strategy"      : str,
            "confidence"    : str,   e.g. "91.5%"
            "top_factors"   : list,  top 3 feature labels by importance
            "decision_path" : list,  step-by-step rules used
        }
    """
    # 1. Validate
    validate_features(features)

    # 2. Build DataFrame
    df = pd.DataFrame([features], columns=feature_names)

    # 3. Predict strategy + confidence
    prediction    = model.predict(df)
    probabilities = model.predict_proba(df)[0]
    confidence    = round(max(probabilities) * 100, 1)
    strategy      = encoder.inverse_transform(prediction)[0]

    # 4. Feature importance — global XAI (top 3)
    ranked_features = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True
    )
    top_factors = [feature_labels[f[0]] for f in ranked_features[:3]]

    # 5. Decision path — local XAI
    path = get_decision_path(df)

    return {
        "strategy"      : strategy,
        "confidence"    : f"{confidence}%",
        "top_factors"   : top_factors,
        "decision_path" : path
    }


# ── Formatted Output Helper ───────────────────
def print_prediction(result: dict) -> None:
    print("\n" + "=" * 52)
    print("  ML Prediction Engine — Phase 4")
    print("=" * 52)
    print(f"\n  Recommended Strategy : {result['strategy']}")
    print(f"  Confidence           : {result['confidence']}")
    print("\n  Top Influencing Factors (Global XAI):")
    for i, factor in enumerate(result["top_factors"], 1):
        print(f"    {i}. {factor}")
    print("\n  Decision Path (Local XAI):")
    for step in result["decision_path"]:
        print(f"    → {step}")
    print("\n" + "=" * 52)


# ── Standalone Demo ───────────────────────────
if __name__ == "__main__":

    # Sample enterprise profile
    sample_input = {
        "server_count"      : 120,
        "avg_cpu_util"      : 65,
        "storage_tb"        : 30.5,
        "downtime_tolerance": 1.5,    # Very low → likely Hybrid
        "compliance_level"  : 3,      # High compliance
        "growth_rate"       : 30,     # High growth
        "budget_sensitivity": 2       # Medium budget
    }

    print("\n  Input Features:")
    for key, val in sample_input.items():
        label = feature_labels[key]
        print(f"    {label:<28} : {val}")

    try:
        result = predict_strategy(sample_input)
        print_prediction(result)

    except ValueError as e:
        print(f"\n  [Validation Error]\n{e}")