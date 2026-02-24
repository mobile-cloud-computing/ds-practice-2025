import sys
import os
import json
import pytest
from unittest.mock import patch

# Setup path to import the service
FILE = __file__
pb_root = os.path.abspath(os.path.join(FILE, "../../../../utils/pb"))
sys.path.insert(0, pb_root)

from suggestions import suggestions_pb2 as sg_pb2
from suggestions import suggestions_pb2_grpc as sg_grpc

# Import the service implementation
sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../src")))
from app import SuggestionsService, BOOK_CATALOG


class TestSuggestionsService:
    """Test suite for SuggestionsService"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = SuggestionsService()
        self.context = None

    def test_valid_request_returns_three_books(self):
        """Test that valid request returns exactly 3 book suggestions"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        response = self.service.GetSuggestions(request, self.context)
        
        assert len(response.books) == 3

    def test_returned_books_have_required_fields(self):
        """Test that returned books have all required fields"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        response = self.service.GetSuggestions(request, self.context)
        
        for book in response.books:
            assert book.book_id != ""
            assert book.title != ""
            assert book.author != ""

    def test_returned_books_are_from_catalog(self):
        """Test that all returned books are from the BOOK_CATALOG"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        response = self.service.GetSuggestions(request, self.context)
        
        catalog_ids = {book["book_id"] for book in BOOK_CATALOG}
        for book in response.books:
            assert book.book_id in catalog_ids

    def test_returned_books_are_unique(self):
        """Test that returned books don't contain duplicates"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        response = self.service.GetSuggestions(request, self.context)
        
        book_ids = [book.book_id for book in response.books]
        assert len(book_ids) == len(set(book_ids)), "Duplicate books returned"

    def test_invalid_json_returns_empty_list(self):
        """Test that invalid JSON returns empty suggestions list"""
        request = sg_pb2.SuggestionsRequest(order_json="invalid json{{{")
        response = self.service.GetSuggestions(request, self.context)
        
        assert len(response.books) == 0

    def test_empty_order_still_returns_suggestions(self):
        """Test that even empty order returns suggestions"""
        order = {}
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        response = self.service.GetSuggestions(request, self.context)
        
        assert len(response.books) == 3

    def test_multiple_calls_may_return_different_books(self):
        """Test that suggestions use random.sample for randomization"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        
        # Mock random.sample to return predictable results
        with patch('app.random.sample') as mock_sample:
            # Configure mock to return different sets of books on each call
            mock_sample.side_effect = [
                [BOOK_CATALOG[0], BOOK_CATALOG[1], BOOK_CATALOG[2]],  # First call
                [BOOK_CATALOG[3], BOOK_CATALOG[4], BOOK_CATALOG[5]],  # Second call
            ]
            
            # First call
            response1 = self.service.GetSuggestions(request, self.context)
            assert len(response1.books) == 3
            assert response1.books[0].book_id == "101"
            
            # Second call
            response2 = self.service.GetSuggestions(request, self.context)
            assert len(response2.books) == 3
            assert response2.books[0].book_id == "104"
            
            # Verify random.sample was called with correct arguments
            assert mock_sample.call_count == 2
            mock_sample.assert_called_with(BOOK_CATALOG, 3)

    def test_book_catalog_has_expected_size(self):
        """Test that BOOK_CATALOG contains expected number of books"""
        assert len(BOOK_CATALOG) == 10

    def test_book_catalog_integrity(self):
        """Test that all books in catalog have required fields"""
        for book in BOOK_CATALOG:
            assert "book_id" in book
            assert "title" in book
            assert "author" in book
            assert book["book_id"] != ""
            assert book["title"] != ""
            assert book["author"] != ""

    def test_suggestions_with_fraud_order(self):
        """Test that suggestions work even for potentially fraudulent orders"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 100}]
        }
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        response = self.service.GetSuggestions(request, self.context)
        
        # Suggestions should still work regardless of order validity
        assert len(response.books) == 3

    def test_suggestions_with_missing_fields(self):
        """Test that suggestions work even when order has missing fields"""
        order = {
            "items": [{"name": "Book A"}]
        }
        request = sg_pb2.SuggestionsRequest(order_json=json.dumps(order))
        response = self.service.GetSuggestions(request, self.context)
        
        assert len(response.books) == 3

    def test_specific_book_ids_format(self):
        """Test that book IDs are in expected format (101-110)"""
        expected_ids = {str(i) for i in range(101, 111)}
        catalog_ids = {book["book_id"] for book in BOOK_CATALOG}
        
        assert catalog_ids == expected_ids

    def test_known_books_in_catalog(self):
        """Test that certain well-known books are in the catalog"""
        catalog_titles = {book["title"] for book in BOOK_CATALOG}
        
        assert "1984" in catalog_titles
        assert "The Great Gatsby" in catalog_titles
        assert "The Hobbit" in catalog_titles
