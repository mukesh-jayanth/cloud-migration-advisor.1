import pandas as pd
import joblib
import os
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay
)

# ─────────────────────────────────────────────
#  ML Training Engine
#  Phase 4 — Cloud Migration ML Model
#  Trains a Decision Tree classifier and
#  evaluates with full metrics + XAI outputs
# ─────────────────────────────────────────────

# ── Load Dataset ─────────────────────────────
df = pd.read_csv("data/synthetic_data.csv")

X = df.drop("strategy", axis=1)
y = df["strategy"]

feature_names = list(X.columns)

# ── Encode Labels ────────────────────────────
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

print("=" * 50)
print("  ML Training Engine — Phase 4")
print("=" * 50)
print(f"\n  Dataset loaded: {len(df)} records")
print(f"  Features      : {len(feature_names)}")
print(f"  Classes       : {list(encoder.classes_)}")

# ── Train / Test Split ───────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

print(f"\n  Train size    : {len(X_train)}")
print(f"  Test size     : {len(X_test)}")

# ── Train Model ──────────────────────────────
model = DecisionTreeClassifier(
    max_depth=5,          # Slightly deeper than before for richer rules
    min_samples_leaf=10,
    random_state=42
)

model.fit(X_train, y_train)

# ── Evaluate — Accuracy ──────────────────────
predictions = model.predict(X_test)
accuracy    = accuracy_score(y_test, predictions)

print("\n" + "=" * 50)
print("  Model Evaluation")
print("=" * 50)
print(f"\n  Test Accuracy : {round(accuracy * 100, 2)}%")

# ── Evaluate — Cross Validation ──────────────
cv_scores = cross_val_score(model, X, y_encoded, cv=5, scoring="accuracy")

print(f"\n  Cross-Validation (5-fold):")
print(f"    Mean Accuracy : {round(cv_scores.mean() * 100, 2)}%")
print(f"    Std Dev       : ± {round(cv_scores.std() * 100, 2)}%")
print(f"    All Folds     : {[round(s * 100, 2) for s in cv_scores]}")

# ── Evaluate — Classification Report ─────────
print("\n  Classification Report:")
print(
    classification_report(
        y_test,
        predictions,
        target_names=encoder.classes_
    )
)

# ── Evaluate — Confusion Matrix ───────────────
cm = confusion_matrix(y_test, predictions)

print("  Confusion Matrix:")
print(f"  Classes: {list(encoder.classes_)}")
print(f"  {cm}\n")

# ── Feature Importance ────────────────────────
print("=" * 50)
print("  Feature Importance (Global XAI)")
print("=" * 50)

feature_labels = {
    "server_count"      : "Number of Servers",
    "avg_cpu_util"      : "CPU Utilization",
    "storage_tb"        : "Storage Size",
    "downtime_tolerance": "Downtime Tolerance",
    "compliance_level"  : "Compliance Level",
    "growth_rate"       : "Growth Rate",
    "budget_sensitivity": "Budget Flexibility"
}

ranked = sorted(
    zip(feature_names, model.feature_importances_),
    key=lambda x: x[1],
    reverse=True
)

for i, (name, importance) in enumerate(ranked, 1):
    bar = "█" * int(importance * 40)
    label = feature_labels.get(name, name)
    print(f"  {i}. {label:<22} {round(importance, 4):>6}  {bar}")

# ── Save Model & Encoder ──────────────────────
os.makedirs("models", exist_ok=True)

joblib.dump(model,   "models/decision_tree.pkl")
joblib.dump(encoder, "models/label_encoder.pkl")

print("\n  Model   saved → models/decision_tree.pkl")
print("  Encoder saved → models/label_encoder.pkl")

# ── Save Confusion Matrix Plot ────────────────
fig, ax = plt.subplots(figsize=(7, 5))

disp = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=encoder.classes_
)
disp.plot(ax=ax, cmap="Blues", colorbar=False)

ax.set_title("Confusion Matrix — Cloud Migration Strategy", fontsize=13, pad=12)
plt.tight_layout()
plt.savefig("models/confusion_matrix.png", dpi=150)
plt.close()

print("  Confusion matrix plot saved → models/confusion_matrix.png")

# ── Save Decision Tree Visualization ─────────
fig, ax = plt.subplots(figsize=(24, 10))

plot_tree(
    model,
    feature_names=feature_names,
    class_names=encoder.classes_,
    filled=True,
    rounded=True,
    fontsize=9,
    ax=ax
)

ax.set_title("Decision Tree — Cloud Migration Strategy Classifier", fontsize=14, pad=14)
plt.tight_layout()
plt.savefig("models/decision_tree_visual.png", dpi=150)
plt.close()

print("  Decision tree visual saved → models/decision_tree_visual.png")

print("\n" + "=" * 50)
print("  Training complete.")
print("=" * 50)