import os

import requests
import logging

logger = logging.getLogger(__name__)

# API_KEY=os.environ.get("api_key")

def get_book_suggestions(book_ordered_by_customer, number_of_books = 5):

    #TODO: get from ENV
    payload = {
        'api-key': 'c59ecdfb8fa34bab97dac34162e9a098',
        'query': book_ordered_by_customer,
        'number': 10,
        'group-results': 'true'
    }

    logger.info("Calling BigBookAPI for book: %s", book_ordered_by_customer)

    try:
        r = requests.get('https://api.bigbookapi.com/search-books?', params=payload, timeout=4)
        logger.info(f"Successfully retrieved books")
    except requests.RequestException as e:
        logger.error(f"API call failed  for book: {book_ordered_by_customer}. Error: {e}")
        return []

    if r.status_code != 200:
        logger.error(f"Response code was {r.status_code} when getting book: {book_ordered_by_customer}")
        return []

    r = r.json()

    book_id = -1
    for book in r["books"]:
        # the book is a list that contains another list so there fore book[0]
        if book[0]["title"] == payload["query"]:
            book_id = book[0]["id"]
            logger.info(f"Book: {book_ordered_by_customer} has id: {book_id}")

    if book_id == -1:
        logger.error(f"Could not get bookId for book: {book_ordered_by_customer}")
        return []


    # Get similar book
    payload = {
        'api-key': os.environ["api_key"],
        "id": book_id,
        "number": number_of_books,
    }

    try:
        r = requests.get(f"https://api.bigbookapi.com/{book_id}/similar", params=payload, timeout=4)
        logger.info(f"Successfully retrieved similar books")
    except requests.RequestException as e:
        logger.error(f"API call failed  for book_ID: {book_id}. Error: {e}")
        return []

    if r.status_code != 200:
        logger.error(f"Response code was {r.status_code} when book suggestions. Book id: {book_id}")
        return []
    r = r.json()


    recommended_books_list = []
    for book in r["similar_books"]:
        recommended_books_list.append({"bookId": book["id"],"title": book["title"], "author": "Author123"})

    return recommended_books_list
