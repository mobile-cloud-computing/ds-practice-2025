from faker import Faker
import pandas as pd

seed_value = 42


fake = Faker()
Faker.seed(seed_value)

num_rows = 1000

book_data = {
    'name': [fake.sentence()[:-1] for _ in range(num_rows)],  
    'author': [fake.name() for _ in range(num_rows)],
}

books_df = pd.DataFrame(book_data)

csv_filename = 'synthetic_books_data.csv'
books_df.to_csv(csv_filename, index=False)