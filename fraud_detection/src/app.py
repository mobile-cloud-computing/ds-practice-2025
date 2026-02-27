import sys
import os
import hashlib
import logging
import time

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
from concurrent import futures

logging.basicConfig(
    level=logging.INFO,
    format="===LOG=== %(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("fraud_detection")

# Card BIN prefixes associated with high-fraud prepaid/gift card ranges
_SUSPICIOUS_BIN_PREFIXES = {"400000", "411111", "520000", "530000", "601100"}

# Disposable / temporary email domains
_DISPOSABLE_EMAIL_DOMAINS = {
    "tempmail.com", "throwaway.email", "guerrillamail.com",
    "mailinator.com", "fakeinbox.com", "yopmail.com",
}


def _mask_card(card_number):
    digits = "".join(ch for ch in str(card_number or "") if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return f"****{digits[-4:]}"


def _check_card_blocklist(card_number):
    """Flag if the card BIN (first 6 digits) is in a known-suspicious set."""
    digits = "".join(ch for ch in card_number if ch.isdigit())
    if len(digits) >= 6 and digits[:6] in _SUSPICIOUS_BIN_PREFIXES:
        return "Credit card BIN is in a high-risk range"
    return None


def _check_disposable_email(email):
    """Flag if the purchaser uses a known disposable email provider."""
    email = (email or "").strip().lower()
    if "@" in email:
        domain = email.rsplit("@", 1)[1]
        if domain in _DISPOSABLE_EMAIL_DOMAINS:
            return "Purchaser email uses a disposable email provider"
    return None


def _check_risk_score(transaction_id, card_number, email):
    """Deterministic risk score derived from a hash of transaction fields.

    If the score exceeds a threshold, flag as suspicious.  This simulates
    a model score without any external calls.
    """
    payload = f"{transaction_id}:{card_number}:{email}"
    digest = hashlib.sha256(payload.encode()).hexdigest()
    # Use last 4 hex chars as a 0-65535 score
    score = int(digest[-4:], 16)
    # ~1.5 % of transactions will exceed the threshold (score >= 64000)
    if score >= 64000:
        return f"Transaction risk score is elevated ({score})"
    return None


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def DetectFraud(self, request, context):
        started = time.perf_counter()
        metadata = dict(context.invocation_metadata())
        correlation_id = metadata.get("x-correlation-id", request.transaction_id or "unknown")

        logger.info(
            "cid=%s event=fraud_check_received transaction_id=%s card=%s",
            correlation_id,
            request.transaction_id,
            _mask_card(request.credit_card_number),
        )

        try:
            checks = [
                _check_card_blocklist(request.credit_card_number),
                _check_disposable_email(request.purchaser_email),
                _check_risk_score(
                    request.transaction_id,
                    request.credit_card_number,
                    request.purchaser_email,
                ),
            ]
            reasons = [r for r in checks if r is not None]

            is_fraud = len(reasons) > 0
            latency_ms = (time.perf_counter() - started) * 1000
            if is_fraud:
                logger.warning(
                    "cid=%s event=fraud_check_completed is_fraud=true reason_count=%s latency_ms=%.2f reasons=%s",
                    correlation_id,
                    len(reasons),
                    latency_ms,
                    reasons,
                )
            else:
                logger.info(
                    "cid=%s event=fraud_check_completed is_fraud=false reason_count=0 latency_ms=%.2f",
                    correlation_id,
                    latency_ms,
                )

            return fraud_detection.FraudDetectionResponse(
                is_fraud=is_fraud,
                reasons=reasons,
            )
        except Exception:
            latency_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "cid=%s event=fraud_check_exception latency_ms=%.2f",
                correlation_id,
                latency_ms,
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal error during fraud detection")
            return fraud_detection.FraudDetectionResponse(
                is_fraud=False,
                reasons=["Internal fraud detection error"],
            )


def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    # Listen on port 50051
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logger.info("Server started. Listening on port %s.", port)
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
