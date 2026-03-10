import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score


df = pd.read_csv("data/synthetic_data.csv")

X = df.drop("strategy", axis=1)
y = df["strategy"]

feature_names = X.columns


encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)


X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)


model = DecisionTreeClassifier(
    max_depth=4,
    min_samples_leaf=10,
    random_state=42
)

model.fit(X_train, y_train)


predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("Model Accuracy:", accuracy)


# Print feature importance
print("\nFeature Importance:")

for name, importance in zip(feature_names, model.feature_importances_):
    print(name, ":", round(importance, 3))


joblib.dump(model, "models/decision_tree.pkl")
joblib.dump(encoder, "models/label_encoder.pkl")