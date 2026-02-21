import sys
import os
import json
import pytest

# Setup path to import the service
FILE = __file__
pb_root = os.path.abspath(os.path.join(FILE, "../../../../utils/pb"))
sys.path.insert(0, pb_root)

from fraud_detection import fraud_detection_pb2 as fd_pb2
from fraud_detection import fraud_detection_pb2_grpc as fd_grpc

# Import the service implementation
sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../src")))
from app import FraudDetectionService


class TestFraudDetectionService:
    """Test suite for FraudDetectionService"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = FraudDetectionService()
        self.context = None  # Mock context (not needed for these tests)

    def test_valid_order_no_fraud(self):
        """Test that a valid order passes fraud checks"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == False
        assert response.reason == "OK"

    def test_fraud_too_many_items(self):
        """Test fraud detection for orders with quantity >= 50"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 50}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == True
        assert response.reason == "Too many items"

    def test_fraud_missing_user_name(self):
        """Test fraud detection for missing user name"""
        order = {
            "user": {"contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == True
        assert response.reason == "Missing user info"

    def test_fraud_missing_user_contact(self):
        """Test fraud detection for missing user contact"""
        order = {
            "user": {"name": "John Doe"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == True
        assert response.reason == "Missing user info"

    def test_fraud_suspicious_card_number(self):
        """Test fraud detection for invalid card number format"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "1234-5678-9012-3456", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == True
        assert response.reason == "Suspicious card number"

    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        request = fd_pb2.OrderRequest(order_json="invalid json{{{")
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == True
        assert response.reason == "Invalid JSON"

    def test_multiple_items_total_quantity(self):
        """Test that quantities are summed across multiple items"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [
                {"name": "Book A", "quantity": 25},
                {"name": "Book B", "quantity": 25}
            ]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == True
        assert response.reason == "Too many items"

    def test_edge_case_quantity_49(self):
        """Test edge case: quantity 49 should pass"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 49}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == False
        assert response.reason == "OK"

    def test_empty_items_list(self):
        """Test handling of empty items list"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": []
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == False
        assert response.reason == "OK"

    def test_null_user(self):
        """Test handling of null user object"""
        order = {
            "user": None,
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == True
        assert response.reason == "Missing user info"

    def test_valid_card_13_digits(self):
        """Test valid card with 13 digits (minimum)"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "1234567890123", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == False
        assert response.reason == "OK"

    def test_valid_card_19_digits(self):
        """Test valid card with 19 digits (maximum)"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "1234567890123456789", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        request = fd_pb2.OrderRequest(order_json=json.dumps(order))
        response = self.service.CheckFraud(request, self.context)
        
        assert response.fraud_detected == False
        assert response.reason == "OK"
