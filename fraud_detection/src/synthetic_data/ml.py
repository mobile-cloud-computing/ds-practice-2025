import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder
import pickle

df = pd.read_csv("synthetic_data.csv")

features = [
    'name', 'contact', 'creditCard_number', 'creditCard_expirationDate', 'creditCard_cvv',
    'billingAddress_street', 'billingAddress_city', 'billingAddress_state', 'billingAddress_zip', 'billingAddress_country',
    'device_type', 'device_model', 'device_os',
    'browser_name', 'browser_version',
    'items_name', 'items_quantity',
    'referrer'
]

X = df[features]
y = df['isFraudulent']

label_encoder = LabelEncoder()
X_encoded = X.apply(label_encoder.fit_transform)

X_train, X_test, y_train, y_test = train_test_split(X_encoded, y, test_size=0.2, random_state=42)

clf = RandomForestClassifier(random_state=42)
clf.fit(X_train, y_train)

with open('random_forest_model.pkl', 'wb') as model_file:
    pickle.dump(clf, model_file)

with open('random_forest_model.pkl', 'rb') as model_file:
    loaded_model = pickle.load(model_file)