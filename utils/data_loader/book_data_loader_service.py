import pandas as pd
from dotenv import load_dotenv

from sqlalchemy.orm import sessionmaker
from utils.models.book import Book, engine, Base

from sentence_transformers import SentenceTransformer

load_dotenv()


class BookDataLoaderService:
    def __init__(self, path, model_name="all-MiniLM-L6-v2"):
        self.path = path
        self.model = SentenceTransformer(model_name)

    def call(self):
        # Create the table if it doesn't exist
        Base.metadata.create_all(engine)

        data = pd.read_csv(self.path)

        for _, row in data.iterrows():
            book_data = {
                "title": row["Title"],
                "author": row["Author"],
                "genre": row["Genre"],
                "subgenre": row["SubGenre"],
                "height": row["Height"],
                "publisher": row["Publisher"],
            }
            text_to_embed = " ".join(
                [
                    str(row["Title"]),
                    str(row["Author"]),
                    str(row["Genre"]),
                    str(row["SubGenre"]),
                    str(row["Publisher"]),
                ]
            )

            # Generate the embedding vector
            embedding = self.model.encode(text_to_embed)

            # Ensure the embedding is in the format expected by pgvector
            # pgvector expects a list or array of floats
            embedding_list = embedding.tolist()
            book_data["embedding"] = embedding_list
            self._insert_book(book_data)

        print(f"Inserted {len(data)} books into the database with its embedding.")

    def _insert_book(_, book_data):
        """
        Insert a book into the database
        """

        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            book = Book(
                title=book_data["title"],
                author=book_data["author"],
                genre=book_data["genre"],
                subgenre=book_data["subgenre"],
                height=book_data["height"],
                publisher=book_data["publisher"],
                embedding=book_data["embedding"],
            )

            session.add(book)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error inserting book {book_data['title']}: {str(e)}")
        finally:
            session.close()


data_loader = BookDataLoaderService("data/books.csv")

data_loader.call()
