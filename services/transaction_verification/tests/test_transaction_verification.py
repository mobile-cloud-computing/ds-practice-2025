import sys
import os
import json
import pytest

# Setup path to import the service
FILE = __file__
pb_root = os.path.abspath(os.path.join(FILE, "../../../../utils/pb"))
sys.path.insert(0, pb_root)

from transaction_verification import transaction_verification_pb2 as tv_pb2
from transaction_verification import transaction_verification_pb2_grpc as tv_grpc

# Import the service implementation
sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../src")))
from app import TransactionVerificationService


class TestTransactionVerificationService:
    """Test suite for TransactionVerificationService"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = TransactionVerificationService()
        self.context = None

    def test_valid_transaction(self):
        """Test that a valid transaction passes all checks"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == True
        assert response.reason == "Transaction valid"

    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        request = tv_pb2.TransactionRequest(order_json="not valid json{{")
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid JSON"

    def test_empty_items_list(self):
        """Test rejection when items list is empty"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": []
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "No items in order"

    def test_missing_user_name(self):
        """Test rejection when user name is missing"""
        order = {
            "user": {"contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Missing user name"

    def test_missing_user_contact(self):
        """Test rejection when user contact is missing"""
        order = {
            "user": {"name": "John Doe"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Missing user contact"

    def test_missing_credit_card_number(self):
        """Test rejection when credit card number is missing"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Missing credit card number"

    def test_missing_expiration_date(self):
        """Test rejection when expiration date is missing"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Missing expiration date"

    def test_missing_cvv(self):
        """Test rejection when CVV is missing"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Missing CVV"

    def test_invalid_card_format_with_dashes(self):
        """Test rejection of card number with dashes"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532-0151-1283-0366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid credit card format"

    def test_invalid_card_too_short(self):
        """Test rejection of card number with less than 13 digits"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "123456789012", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid credit card format"

    def test_invalid_card_too_long(self):
        """Test rejection of card number with more than 19 digits"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "12345678901234567890", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid credit card format"

    def test_invalid_cvv_too_short(self):
        """Test rejection of CVV with less than 3 digits"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "12"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid CVV format"

    def test_invalid_cvv_too_long(self):
        """Test rejection of CVV with more than 4 digits"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "12345"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid CVV format"

    def test_valid_cvv_4_digits(self):
        """Test valid CVV with 4 digits (AMEX format)"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "1234"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == True
        assert response.reason == "Transaction valid"

    def test_item_missing_name(self):
        """Test rejection when item name is missing"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Item missing name"

    def test_item_zero_quantity(self):
        """Test rejection when item quantity is zero"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 0}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid item quantity"

    def test_item_negative_quantity(self):
        """Test rejection when item quantity is negative"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": -1}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Invalid item quantity"

    def test_multiple_valid_items(self):
        """Test valid transaction with multiple items"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [
                {"name": "Book A", "quantity": 2},
                {"name": "Book B", "quantity": 3},
                {"name": "Book C", "quantity": 1}
            ]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == True
        assert response.reason == "Transaction valid"

    def test_null_user_object(self):
        """Test rejection when user object is null"""
        order = {
            "user": None,
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Missing user name"

    def test_null_credit_card_object(self):
        """Test rejection when credit card object is null"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": None,
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = tv_pb2.TransactionRequest(order_json=json.dumps(order))
        response = self.service.VerifyTransaction(request, self.context)
        
        assert response.is_valid == False
        assert response.reason == "Missing credit card number"
