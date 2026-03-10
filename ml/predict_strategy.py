import joblib
import pandas as pd
from sklearn.tree import _tree


model = joblib.load("models/decision_tree.pkl")
encoder = joblib.load("models/label_encoder.pkl")


feature_names = [
    "server_count",
    "avg_cpu_util",
    "storage_tb",
    "downtime_tolerance",
    "compliance_level",
    "growth_rate",
    "budget_sensitivity"
]


# Human readable names
feature_labels = {
    "server_count": "Number of Servers",
    "avg_cpu_util": "CPU Utilization",
    "storage_tb": "Storage Size",
    "downtime_tolerance": "Downtime Tolerance",
    "compliance_level": "Compliance Level",
    "growth_rate": "Growth Rate",
    "budget_sensitivity": "Budget Flexibility"
}


def get_decision_path(sample):

    tree = model.tree_
    feature = tree.feature
    threshold = tree.threshold

    node_indicator = model.decision_path(sample)
    node_index = node_indicator.indices

    rules = []

    for node_id in node_index:

        if feature[node_id] != _tree.TREE_UNDEFINED:

            feature_name = feature_names[feature[node_id]]
            label = feature_labels[feature_name]

            threshold_value = round(threshold[node_id], 2)

            rules.append(
                f"{label} compared with threshold {threshold_value}"
            )

    return rules


def predict_strategy(features):

    df = pd.DataFrame([features], columns=feature_names)

    prediction = model.predict(df)
    strategy = encoder.inverse_transform(prediction)[0]


    # Feature importance
    importance = model.feature_importances_

    ranked_features = sorted(
        zip(feature_names, importance),
        key=lambda x: x[1],
        reverse=True
    )

    top_factors = [
        feature_labels[f[0]] for f in ranked_features[:3]
    ]


    # Decision path explanation
    path = get_decision_path(df)


    return {
        "strategy": strategy,
        "top_factors": top_factors,
        "decision_path": path
    }