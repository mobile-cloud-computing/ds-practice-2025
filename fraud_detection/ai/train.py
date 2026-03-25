import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_class_weight

import joblib

# Load dataset (example: credit card transactions)
df = pd.read_csv("./fraud_detection/ai/transactions.csv")

# Features and label
X = df.drop("is_fraud", axis=1)
y = df["is_fraud"]

# Train/test split (stratified for imbalance)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# Handle class imbalance via class weights
class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(y_train),
    y=y_train
)
weights = {0: class_weights[0], 1: class_weights[1]}

# Model
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    class_weight=weights,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# Predictions
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_proba))

joblib.dump(model, "./fraud_detection/ai/fraud_model.joblib")

