import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# Sample dataset (book titles and descriptions)
books = [
    {'title': 'Book A', 'description': 'A gripping mystery novel about crime and investigation.'},
    {'title': 'Book B', 'description': 'An epic fantasy adventure with magical creatures and brave heroes.'},
    {'title': 'Book C', 'description': 'A heartwarming romance story set in a small town.'},
    # Add more books as needed
]

# Preprocess the dat
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

def preprocess_text(text):
    words = nltk.word_tokenize(text.lower())
    words = [word for word in words if word.salpha() and word not in stop_words]
    return ' '.join(words)

# Apply preprocessing to book descriptions
for book in books:
    book['processed_description'] = preprocess_text(book['description'])

# Create TF-IDF vectorizer
tfidf_vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf_vectorizer.fit_transform([book['processed_description'] for book in books])

# Function to recommend books based on user input
def recommend_books(user_input, num_recommendations=3):
    # Preprocess user input
    processed_user_input = preprocess_text(user_input)

    # Transform user input using the TF-IDF vectorizer
    user_tfidf = tfidf_vectorizer.transform([processed_user_input])

    # Calculate cosine similarity between user input and book descriptions
    cosine_similarities = linear_kernel(user_tfidf, tfidf_matrix).flatten()

    # Get indices of books with highest similarity
    book_indices = cosine_similarities.argsort()[:-num_recommendations-1:-1]

    # Return recommended books
    recommendations = [{'title': books[i]['title'], 'description': books[i]['description']} for i in book_indices]
    return recommendations

# Example usage
user_input = "I enjoyed a thrilling mystery novel with crime and investigation."
recommended_books = recommend_books(user_input)

# Print recommended books
for book in recommended_books:
    print(f"Recommended: {book['title']} - {book['description']}")