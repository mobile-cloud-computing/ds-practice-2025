import pandas as pd
import numpy as np
import random

np.random.seed(42)
random.seed(42)

n_samples = 1000

data = []

for _ in range(n_samples):
    price = round(np.random.uniform(10, 2000), 2)

    # Random credit card number (some intentionally start with 999)
    if np.random.rand() < 0.05:
        credit_card = "999" + "".join([str(np.random.randint(0, 10)) for _ in range(13)])
    else:
        credit_card = "".join([str(np.random.randint(0, 10)) for _ in range(16)])

    # Fraud rule
    is_fraud = 1 if (price > 1000 or credit_card.startswith("999")) else 0

    data.append([
        price,
        credit_card,
        is_fraud
    ])

df = pd.DataFrame(data, columns=[
    "price",
    "credit_card",
    "is_fraud"
])

df.to_csv("./fraud_detection/ai/transactions.csv", index=False)

print("transactions.csv created successfully.")
print(df.head())