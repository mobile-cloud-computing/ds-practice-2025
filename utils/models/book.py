from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import mapped_column
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "")  # XXX: let's assume this is set

engine = create_engine(db_url)
metadata = MetaData()

Base = declarative_base()


class Book(Base):
    __tablename__ = "books"

    embedding = mapped_column(Vector(3))
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    genre = Column(String(100), nullable=True)
    subgenre = Column(String(100), nullable=True)
    height = Column(Integer, nullable=True)
    publisher = Column(String(255), nullable=True)
    embedding = Column(Vector(384), nullable=True)

    def __repr__(self):
        return f"<Book(title='{self.title}', author='{self.author}')>"
