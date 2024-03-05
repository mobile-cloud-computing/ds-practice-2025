import pandas as pd
from faker import Faker
import random

fake = Faker()

def generate_synthetic_data():
    data = []

    for _ in range(1000):
        user_data = {
            "name": fake.name(),
            "contact": fake.phone_number()
        }

        credit_card_data = {
            "number": fake.credit_card_number(card_type='mastercard'),
            "expirationDate": fake.credit_card_expire(),
            "cvv": fake.credit_card_security_code(card_type='mastercard')
        }

        billing_address_data = {
            "street": fake.street_address(),
            "city": fake.city(),
            "state": fake.state(),
            "zip": fake.zipcode(),
            "country": fake.country()
        }

        device_data = {
            "type": fake.word(),
            "model": fake.word(),
            "os": fake.word()
        }

        browser_data = {
            "name": fake.word(),
            "version": fake.random_number(1, 10)
        }

        items_data = [{
            "name": fake.word(),
            "quantity": random.randint(1, 5)
        }]

        referrer_data = fake.url()

        is_fraudulent = random.choice([True, False])

        row = {
            "name": user_data["name"],
            "contact": user_data["contact"],
            "creditCard_number": credit_card_data["number"],
            "creditCard_expirationDate": credit_card_data["expirationDate"],
            "creditCard_cvv": credit_card_data["cvv"],
            "billingAddress_street": billing_address_data["street"],
            "billingAddress_city": billing_address_data["city"],
            "billingAddress_state": billing_address_data["state"],
            "billingAddress_zip": billing_address_data["zip"],
            "billingAddress_country": billing_address_data["country"],
            "device_type": device_data["type"],
            "device_model": device_data["model"],
            "device_os": device_data["os"],
            "browser_name": browser_data["name"],
            "browser_version": browser_data["version"],
            "items_name": items_data[0]["name"],
            "items_quantity": items_data[0]["quantity"],
            "referrer": referrer_data,
            "isFraudulent": is_fraudulent
        }

        data.append(row)

    return data

if __name__ == "__main__":
    synthetic_data = generate_synthetic_data()
    df = pd.DataFrame(synthetic_data)
    df.to_csv("synthetic_data.csv", index=False)