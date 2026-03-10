from ml.predict_strategy import predict_strategy

features = [200,60,20,1.5,3,30,2]

result = predict_strategy(features)

print("ML Prediction:", result["strategy"])

print("\nKey Influencing Factors:")
for factor in result["top_factors"]:
    print("-", factor)

print("\nDecision Path:")
for step in result["decision_path"]:
    print("-", step)