import logging
import sys
import os
from typing import Any, Dict, Tuple

from concurrent.futures import ThreadPoolExecutor, as_completed

from services.transaction_service import TransactionService
from services.suggestions_service import SuggestionsService
from services.fraud_service import FraudService

logger = logging.getLogger(__name__)


FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
models_path = os.path.abspath(os.path.join(FILE, "../../../../../../utils/models"))
sys.path.insert(0, models_path)

from bookstore_models import OrderInfo, UserInfo, BillingInfo, CreditCardInfo


class OrderOrchestratorService:
    """Orchestrates the checkout process across multiple microservices."""

    def __init__(self, grpc_factory, order_event_tracker):
        self.order_event_tracker = order_event_tracker
        self.transaction_service = TransactionService(grpc_factory, order_event_tracker)
        self.fraud_service = FraudService(grpc_factory, order_event_tracker)
        self.suggestions_service = SuggestionsService(grpc_factory, order_event_tracker)

    def initialize_services(
        self,
        order: OrderInfo,
        user: UserInfo,
        credit_card: CreditCardInfo,
        billing: BillingInfo,
    ) -> bool:
        """Initialize all required services before final processing."""

        # first initialize the vector clock
        self.order_event_tracker.initialize_order(order.order_id)
        self.order_event_tracker.record_event(
            order.order_id, "orchestrator", "initialize_order"
        )

        tx_init_ok = self.transaction_service.initialize_order(
            order.order_id, credit_card, billing
        )

        fraud_init_ok = self.fraud_service.initialize_order(order, user, billing)

        sugg_init_ok = self.suggestions_service.initialize_order(
            order.order_id, order.book_tokens, user.user_id
        )

        return tx_init_ok and fraud_init_ok and sugg_init_ok

    def process_order(
        self,
        order: OrderInfo,
        user: UserInfo,
        credit_card: CreditCardInfo,
        billing: BillingInfo,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process the order concurrently across all microservices."""
        # Results containers
        results = {"verification": None, "fraud": None, "suggestions": None}
        errors = []

        # Worker functions for each microservice
        def verification_worker():
            try:
                print(
                    f"[Orchestrator] Starting final VerifyTransaction for card: {credit_card.number}"
                )
                results["verification"] = self.transaction_service.verify_transaction(
                    order.order_id, credit_card, billing
                )
                print(
                    f"[Orchestrator] Verification final result: {results['verification'].success}"
                )
            except Exception as e:
                errors.append(f"Transaction verification error: {str(e)}")

        def fraud_worker():
            try:
                print("[Orchestrator] Starting final fraud_detection analysis")
                results["fraud"] = self.fraud_service.check_fraud(order, user, billing)
                print(
                    f"[Orchestrator] Fraud detection final result: {results['fraud'].success}"
                )
            except Exception as e:
                errors.append(f"Fraud detection error: {str(e)}")

        def suggestions_worker():
            try:
                print("[Orchestrator] Starting final suggestions retrieval")
                results["suggestions"] = self.suggestions_service.get_suggestions(
                    order.order_id, order.book_tokens, user.user_id
                )
                count = (
                    len(results["suggestions"].data)
                    if results["suggestions"].data
                    else 0
                )
                print(f"[Orchestrator] Retrieved {count} suggestions")
            except Exception as e:
                errors.append(f"Suggestions error: {str(e)}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(verification_worker),
                executor.submit(fraud_worker),
                executor.submit(suggestions_worker),
            ]

            for _ in as_completed(futures):
                pass  # Wait for all to complete

        # errors (?)
        if errors:
            return False, {
                "error": {"code": "ORDER_REJECTED", "message": " / ".join(errors)}
            }

        # validation of results
        if not results["fraud"] or not results["fraud"].success:
            error_msg = (
                results["fraud"].error
                if results["fraud"]
                else "Fraud detection not completed"
            )
            return False, {"error": {"code": "ORDER_REJECTED", "message": error_msg}}

        if not results["verification"] or not results["verification"].success:
            error_msg = (
                results["verification"].error
                if results["verification"]
                else "Transaction verification failed"
            )
            return False, {"error": {"code": "ORDER_REJECTED", "message": error_msg}}

        logger.info(
            f"[Orchestrator] Order {order.order_id} approved. Final vector clock. {self.order_event_tracker.get_clock(order.order_id, 'orchestrator')}"
        )
        # Success response
        return True, {
            "orderId": order.order_id,
            "status": "Order Approved",
            "suggestedBooks": results["suggestions"].data
            if results["suggestions"]
            else [],
        }
