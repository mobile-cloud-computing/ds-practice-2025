import sys
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import grpc


# Create a mock RpcError class with code() and details() methods
class MockRpcError(grpc.RpcError):
    def __init__(self, code=grpc.StatusCode.UNAVAILABLE, details="Service unavailable"):
        self._code = code
        self._details = details
    
    def code(self):
        return self._code
    
    def details(self):
        return self._details


# Setup path to import the service
FILE = __file__
pb_root = os.path.abspath(os.path.join(FILE, "../../../../utils/pb"))
sys.path.insert(0, pb_root)

# Import the orchestrator app
sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../src")))
from app import app, mask_sensitive_data


@pytest.fixture
def client():
    """Create Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def valid_order():
    """Sample valid order for testing"""
    return {
        "user": {"name": "John Doe", "contact": "john@example.com"},
        "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
        "items": [{"name": "Book A", "quantity": 2}]
    }


class TestHealthCheck:
    """Test suite for health check endpoint"""

    def test_index_endpoint(self, client):
        """Test that index endpoint returns 200"""
        response = client.get('/')
        assert response.status_code == 200
        assert b"Orchestrator is running" in response.data


class TestMaskSensitiveData:
    """Test suite for data masking utility"""

    def test_mask_credit_card_number(self):
        """Test that credit card number is masked"""
        data = {
            "creditCard": {
                "number": "4532015112830366",
                "cvv": "123"
            }
        }
        masked = mask_sensitive_data(data)
        assert masked['creditCard']['number'] == '****0366'
        assert masked['creditCard']['cvv'] == '***'

    def test_mask_short_card_number(self):
        """Test masking of short card numbers"""
        data = {
            "creditCard": {
                "number": "123",
                "cvv": "456"
            }
        }
        masked = mask_sensitive_data(data)
        assert masked['creditCard']['number'] == '****'
        assert masked['creditCard']['cvv'] == '***'

    def test_mask_preserves_other_fields(self):
        """Test that other fields are not modified"""
        data = {
            "user": {"name": "John", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 2}]
        }
        masked = mask_sensitive_data(data)
        assert masked['user'] == data['user']
        assert masked['items'] == data['items']

    def test_mask_handles_missing_credit_card(self):
        """Test masking when credit card is missing"""
        data = {"user": {"name": "John"}}
        masked = mask_sensitive_data(data)
        assert masked == data

    def test_mask_handles_non_dict(self):
        """Test masking returns non-dict as-is"""
        assert mask_sensitive_data("string") == "string"
        assert mask_sensitive_data(123) == 123
        assert mask_sensitive_data(None) == None


class TestCheckoutValidation:
    """Test suite for checkout request validation"""

    def test_missing_json_body(self, client):
        """Test rejection of request without JSON body"""
        response = client.post('/checkout', data='not json', content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_JSON'

    def test_empty_items_list(self, client, valid_order):
        """Test rejection when items list is empty"""
        valid_order['items'] = []
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_ITEMS'

    def test_missing_items(self, client, valid_order):
        """Test rejection when items field is missing"""
        del valid_order['items']
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_ITEMS'

    def test_missing_user(self, client, valid_order):
        """Test rejection when user field is missing"""
        del valid_order['user']
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'MISSING_USER'

    def test_null_user(self, client, valid_order):
        """Test rejection when user is null"""
        valid_order['user'] = None
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'MISSING_USER'

    def test_missing_credit_card(self, client, valid_order):
        """Test rejection when creditCard field is missing"""
        del valid_order['creditCard']
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'MISSING_CREDIT_CARD'

    def test_null_credit_card(self, client, valid_order):
        """Test rejection when creditCard is null"""
        valid_order['creditCard'] = None
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'MISSING_CREDIT_CARD'


class TestCheckoutBusinessLogic:
    """Test suite for checkout business logic with mocked services"""

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_approved_order(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test successful order approval when all checks pass"""
        # Mock service responses
        mock_fraud.return_value = (False, "OK")
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.return_value = [
            {"bookId": "101", "title": "Book 1", "author": "Author 1"},
            {"bookId": "102", "title": "Book 2", "author": "Author 2"}
        ]
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'Order Approved'
        assert data['orderId'] == '12345'
        assert len(data['suggestedBooks']) == 2

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_rejected_by_fraud(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test order rejection due to fraud detection"""
        mock_fraud.return_value = (True, "Too many items")
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'Order Rejected'
        assert data['suggestedBooks'] == []

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_rejected_by_transaction(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test order rejection due to invalid transaction"""
        mock_fraud.return_value = (False, "OK")
        mock_transaction.return_value = (False, "Invalid credit card format")
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'Order Rejected'
        assert data['suggestedBooks'] == []

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_rejected_by_both(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test order rejection when both fraud and transaction fail"""
        mock_fraud.return_value = (True, "Suspicious card")
        mock_transaction.return_value = (False, "Missing user info")
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'Order Rejected'
        assert data['suggestedBooks'] == []


class TestServiceUnavailability:
    """Test suite for handling service failures"""

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_fraud_service_unavailable(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test 503 response when fraud detection service is unavailable"""
        mock_fraud.side_effect = MockRpcError()
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 503
        
        data = json.loads(response.data)
        assert data['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'fraud_detection' in data['error']['message']

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_transaction_service_unavailable(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test 503 response when transaction verification service is unavailable"""
        mock_fraud.return_value = (False, "OK")
        mock_transaction.side_effect = MockRpcError()
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 503
        
        data = json.loads(response.data)
        assert data['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'transaction_verification' in data['error']['message']

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_both_critical_services_unavailable(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test 503 response when both critical services are unavailable"""
        mock_fraud.side_effect = MockRpcError()
        mock_transaction.side_effect = MockRpcError()
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 503
        
        data = json.loads(response.data)
        assert data['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'fraud_detection' in data['error']['message']
        assert 'transaction_verification' in data['error']['message']

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_suggestions_service_unavailable_not_critical(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test that suggestions service failure doesn't cause 503"""
        mock_fraud.return_value = (False, "OK")
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.side_effect = MockRpcError()
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'Order Approved'
        assert data['suggestedBooks'] == []


class TestThreadSafety:
    """Test suite for multithreading functionality"""

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_all_services_called(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test that all three services are called"""
        mock_fraud.return_value = (False, "OK")
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.return_value = [{"bookId": "101", "title": "Book", "author": "Author"}]
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 200
        
        # Verify all services were called
        mock_fraud.assert_called_once()
        mock_transaction.assert_called_once()
        mock_suggestions.assert_called_once()

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_services_receive_correct_order_data(self, mock_suggestions, mock_transaction, mock_fraud, client, valid_order):
        """Test that services receive the correct order data"""
        mock_fraud.return_value = (False, "OK")
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=valid_order)
        assert response.status_code == 200
        
        # Verify each service received the order data
        mock_fraud.assert_called_with(valid_order)
        mock_transaction.assert_called_with(valid_order)
        mock_suggestions.assert_called_with(valid_order)


class TestEdgeCases:
    """Test suite for edge cases"""

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_multiple_items(self, mock_suggestions, mock_transaction, mock_fraud, client):
        """Test order with multiple items"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [
                {"name": "Book A", "quantity": 2},
                {"name": "Book B", "quantity": 3},
                {"name": "Book C", "quantity": 1}
            ]
        }
        mock_fraud.return_value = (False, "OK")
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=order)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'Order Approved'

    @patch('app.call_fraud_detection')
    @patch('app.call_transaction_verification')
    @patch('app.call_suggestions')
    def test_large_quantity(self, mock_suggestions, mock_transaction, mock_fraud, client):
        """Test order with large quantity"""
        order = {
            "user": {"name": "John Doe", "contact": "john@example.com"},
            "creditCard": {"number": "4532015112830366", "expirationDate": "12/25", "cvv": "123"},
            "items": [{"name": "Book A", "quantity": 1000}]
        }
        mock_fraud.return_value = (True, "Too many items")
        mock_transaction.return_value = (True, "Transaction valid")
        mock_suggestions.return_value = []
        
        response = client.post('/checkout', json=order)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'Order Rejected'
