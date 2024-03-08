_BOOKS_ = [
    {
        "id": "1",
        "title": "Learning Python",
        "author": "John Smith",
        "description": "An in-depth guide to Python programming.",
        "copies": 10,
        "copiesAvailable": 7,
        "category": "Programming",
        "image_url": "https://m.media-amazon.com/images/W/MEDIAX_792452-T1/images/I/51FD3C3kLiL.jpg",
        "price": 3,
        "tags": ["python", "programming", "beginner"],
    },
    {
        "id": "2",
        "title": "JavaScript - The Good Parts",
        "author": "Jane Doe",
        "description": "Unearthing the excellence in JavaScript.",
        "copies": 15,
        "copiesAvailable": 15,
        "category": "Web Development",
        "image_url": "https://m.media-amazon.com/images/W/MEDIAX_792452-T1/images/I/91YlBt-bCHL._SL1500_.jpg",
        "price": 3,
        "tags": ["javascript", "web", "development"],
    },
    {
        "id": "3",
        "title": "Domain-Driven Design: Tackling Complexity in the Heart of Software",
        "author": "Eric Evans",
        "description": "The book is a little more technical and challenging than the others, but if you get familiar with these concepts, you'll be very well off in understanding how today's largest companies keep their code bases manageable and scalable.",
        "copies": 15,
        "copiesAvailable": 15,
        "category": "Web Development",
        "image_url": "https://media.licdn.com/dms/image/D4E12AQELjZvz4dvfPQ/article-cover_image-shrink_720_1280/0/1658570085436?e=1709769600&v=beta&t=4YlnaK_7lu8cDX4EeOnLk-d-EtbgQg_hbduqKGFjnfY",
        "price": 3,
        "tags": ["domain-driven", "design", "software"],
    },
    {
        "id": "4",
        "title": "Design Patterns: Elements of Reusable Object-Oriented Software",
        "author": "Erich Gamma, Richard Helm, Ralph Johnson, & John Vlissides",
        "description": "Useminal book on Design Patterns.",
        "copies": 15,
        "copiesAvailable": 15,
        "category": "Software Development",
        "image_url": "https://prodimage.images-bn.com/lf?set=key%5Bresolve.pixelRatio%5D,value%5B1%5D&set=key%5Bresolve.width%5D,value%5B600%5D&set=key%5Bresolve.height%5D,value%5B10000%5D&set=key%5Bresolve.imageFit%5D,value%5Bcontainerwidth%5D&set=key%5Bresolve.allowImageUpscaling%5D,value%5B0%5D&set=key%5Bresolve.format%5D,value%5Bwebp%5D&source=url%5Bhttps://prodimage.images-bn.com/pimages/9780201633610_p0_v5_s600x595.jpg%5D&scale=options%5Blimit%5D,size%5B600x10000%5D&sink=format%5Bwebp%5D",
        "price": 3,
        "tags": ["design", "patterns", "object-oriented", "software"],
    },
]


def get_books():
    return _BOOKS_[:]


def get_book_by_id(book_id):
    for book in _BOOKS_:
        if book["id"] == book_id:
            return book
    return None


def get_books_by_titles(book_titles):
    return [book for book in _BOOKS_ if book["title"] in book_titles]


def filter_books(author=None, title=None):
    books = _BOOKS_[:]
    if author:
        books = [book for book in books if book["author"] == author]
    if title:
        books = [book for book in books if book["title"] == title]
    return books
