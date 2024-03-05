from surprise import Dataset, Reader, KNNBasic
import pandas as pd

books_df = pd.read_csv('suggestions_service/synthetic data/synthetic_books_data.csv')


books_df['Rating'] = 1  

reader = Reader(rating_scale=(1, 5))
data = Dataset.load_from_df(books_df[['name', 'author', 'Rating']], reader)


sim_options = {
    'name': 'cosine',
    'user_based': False,
    'min_k': 5,  
    'k': 30  
}

model = KNNBasic(sim_options=sim_options)


trainset = data.build_full_trainset()
model.fit(trainset)

def recommend_books(user_input, num_recommendations=2):
    book_index = books_df.index[books_df['name'] == user_input].tolist()[0]
    sim_books = model.get_neighbors(book_index, k=num_recommendations)


    recommendations = books_df.loc[books_df.index.isin(sim_books)][['name', 'author']]
    return recommendations


user_input = 'Agent every development say'
recommended_books = recommend_books(user_input)


print(f"Books similar to '{user_input}':")
print(recommended_books)