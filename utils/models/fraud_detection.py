import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import ipaddress

# Set random seed for reproducibility
np.random.seed(42)


# Function to generate synthetic IP addresses for specific countries
def generate_country_ips(country, count):
    if country == "Russia":
        # Russian IP ranges (examples)
        ranges = [
            "5.45.192.0/18",
            "31.13.144.0/21",
            "46.8.0.0/17",
            "77.73.0.0/21",
            "95.167.0.0/17",
        ]
    elif country == "North Korea":
        # North Korean IP ranges (examples)
        ranges = ["175.45.176.0/22"]
    elif country == "Syria":
        # Syrian IP ranges (examples)
        ranges = ["5.0.0.0/16", "31.9.0.0/16", "46.53.0.0/17"]
    elif country == "USA":
        # USA IP ranges (examples)
        ranges = ["3.0.0.0/8", "16.0.0.0/8", "32.0.0.0/8", "52.0.0.0/8", "54.0.0.0/8"]
    elif country == "UK":
        # UK IP ranges (examples)
        ranges = ["2.24.0.0/16", "3.11.0.0/16", "5.148.0.0/16", "5.150.0.0/16"]
    elif country == "India":
        # India IP ranges (examples)
        ranges = ["1.6.0.0/16", "1.22.0.0/16", "14.96.0.0/16", "27.0.0.0/16"]
    else:
        # Default range
        ranges = ["0.0.0.0/8"]

    result = []
    for _ in range(count):
        # Choose a random IP range
        ip_range = np.random.choice(ranges)
        network = ipaddress.IPv4Network(ip_range)
        # Generate a random IP from the range
        random_ip = str(network[np.random.randint(0, network.num_addresses - 1)])
        result.append(random_ip)

    return result


# Generate synthetic data with more fraud cases from Russia
data_size = 10000

# Create basic data first
countries = ["USA", "UK", "India", "North Korea", "Syria", "Russia"]
# Adjust country distribution to include Russia
country_dist = np.random.choice(
    countries, data_size, p=[0.3, 0.2, 0.2, 0.05, 0.05, 0.2]
)

# Generate payment methods
payment_methods = np.random.choice(
    ["Credit Card", "PayPal", "Crypto", "Bank Transfer"], data_size
)

# Generate cities based on countries
cities = []
for country in country_dist:
    if country == "USA":
        cities.append(
            np.random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Miami"])
        )
    elif country == "UK":
        cities.append(
            np.random.choice(
                ["London", "Manchester", "Birmingham", "Liverpool", "Glasgow"]
            )
        )
    elif country == "India":
        cities.append(
            np.random.choice(["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"])
        )
    elif country == "Russia":
        cities.append(
            np.random.choice(
                ["Moscow", "Saint Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan"]
            )
        )
    elif country == "North Korea":
        cities.append(
            np.random.choice(["Pyongyang", "Wonsan", "Chongjin", "Hamhung", "Nampo"])
        )
    elif country == "Syria":
        cities.append(
            np.random.choice(["Damascus", "Aleppo", "Homs", "Latakia", "Hama"])
        )

# Generate transaction amounts
amounts = np.random.uniform(1, 10000, data_size)

# Generate IP addresses based on countries
ip_addresses = []
for country in country_dist:
    ip_addresses.append(generate_country_ips(country, 1)[0])

# Generate fraudulent flags - with higher probability for Russia, North Korea, and Syria
fraudulent = []
for i in range(data_size):
    country = country_dist[i]
    payment = payment_methods[i]

    # Base fraud probability
    fraud_prob = 0.01  # 1% base fraud rate

    # Adjust based on country
    if country == "Russia":
        fraud_prob += 0.54  # 55% total fraud rate for Russia
    elif country == "North Korea":
        fraud_prob += 0.19  # 10% total fraud rate
    elif country == "Syria":
        fraud_prob += 0.04  # 5% total fraud rate

    # Adjust based on payment method
    if payment == "Crypto":
        fraud_prob += 0.05  # Higher fraud rate for crypto

    # Determine if fraudulent
    fraudulent.append(1 if np.random.random() < fraud_prob else 0)

# Create the DataFrame
df = pd.DataFrame(
    {
        "billing_city": cities,
        "billing_country": country_dist,
        "amount": amounts,
        "payment_method": payment_methods,
        "ip_address": ip_addresses,
        "fraudulent": fraudulent,
    }
)

# Print fraud distribution by country
print("Fraud distribution by country:")
print(df.groupby("billing_country")["fraudulent"].mean().sort_values(ascending=False))

# Process the data for model training
label_encoders = {
    "billing_city": LabelEncoder(),
    "billing_country": LabelEncoder(),
    "payment_method": LabelEncoder(),
}

for col, le in label_encoders.items():
    df[col] = le.fit_transform(df[col])


# Function to extract country from IP (to be used in production)
def get_country_from_ip(ip_address, reader):
    try:
        response = reader.country(ip_address)
        return response.country.name
    except:
        return "Unknown"


# Note: In this synthetic data, we already have billing_country
# In production, you'd use the IP to confirm/extract the country

# Select features for the model
X = df[["billing_city", "billing_country", "amount", "payment_method"]]
y = df["fraudulent"]

# Split the data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train the model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate the model
train_accuracy = model.score(X_train, y_train)
test_accuracy = model.score(X_test, y_test)
print(f"Train accuracy: {train_accuracy:.4f}")
print(f"Test accuracy: {test_accuracy:.4f}")

# Save the model and encoders
joblib.dump(model, "fraud_model.pkl")
joblib.dump(label_encoders, "label_encoders.pkl")

print("Model trained and saved!")
