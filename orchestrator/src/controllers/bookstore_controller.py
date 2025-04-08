import os
import sys
import uuid
import requests
import grpc
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from google.protobuf.json_format import MessageToDict
from sqlalchemy.orm import sessionmaker

from schema import (
    CheckoutRequestSchema,
    OrderStatusResponseSchema,
)

from utils.grpc_config import GrpcConfig
from services.order_orchestrator_service import OrderOrchestratorService

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

# models path
models_path = os.path.abspath(os.path.join(FILE, "../../../../utils/models"))
sys.path.insert(0, models_path)

# import book model
from book import Book, engine
from bookstore_models import (
    UserInfo,
    CreditCardInfo,
    BillingInfo,
    OrderInfo,
)

bookstore_bp = Blueprint("bookstore", __name__)


# -----------------------------------------------------------------------------
#  checkout route
# -----------------------------------------------------------------------------
@bookstore_bp.route("/checkout", methods=["POST"])
def checkout():
    """Handle book checkout process."""
    order_id = str(uuid.uuid4())
    grpc_factory = current_app.grpc_factory
    order_event_tracker = current_app.order_event_tracker

    try:
        # 1) Validate the request
        schema = CheckoutRequestSchema()
        data = schema.load(request.json)

        if not data["termsAndConditionsAccepted"]:
            return jsonify(
                {
                    "error": {
                        "code": "TERMS_NOT_ACCEPTED",
                        "message": "Terms and conditions must be accepted",
                    }
                }
            ), 400

        # 2) Extract all required information
        books = data.get("items", [])
        book_tokens = [b["name"] for b in books]
        amount = sum(b.get("price", 10) for b in books)

        # Create dataclass instances
        user = UserInfo(
            user_id=data.get("user", {}).get("name", "guest"),
            email=data.get("user", {}).get("contact", ""),
            ip_address=request.remote_addr or "",
        )

        credit_card = CreditCardInfo(
            number=data.get("creditCard", {}).get("number"),
            expiry_date=data.get("creditCard", {}).get("expirationDate"),
        )

        billing = BillingInfo(
            city=data["billingAddress"]["city"],
            country=data["billingAddress"]["country"],
        )

        order = OrderInfo(order_id=order_id, book_tokens=book_tokens, amount=amount)

        # 3) Create orchestrator and process order
        orchestrator = OrderOrchestratorService(grpc_factory, order_event_tracker)

        # Initialize services [grpc calls]
        if not orchestrator.initialize_services(order, user, credit_card, billing):
            return jsonify(
                {
                    "error": {
                        "code": "ORDER_REJECTED",
                        "message": "Initialization failed for one or more services",
                    }
                }
            ), 400

        # Process order
        success, result = orchestrator.process_order(order, user, credit_card, billing)
        if not success:
            return jsonify(result), 400

        # success response
        return jsonify(OrderStatusResponseSchema().dump(result))

    except ValidationError as err:
        return jsonify(
            {
                "error": {
                    "code": "ORDER_REJECTED",
                    "message": ", ".join(
                        f"{field}: {msg}"
                        for field, messages in err.messages.items()
                        for msg in messages
                    ),
                }
            }
        ), 400

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify(
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                }
            }
        ), 500


@bookstore_bp.route("/books", methods=["GET"])
def list_books():
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)

        genre = request.args.get("genre")
        author = request.args.get("author")

        query = session.query(Book).with_entities(
            Book.id,
            Book.title,
            Book.author,
            Book.genre,
            Book.subgenre,
            Book.height,
            Book.publisher,
        )

        # Apply filters if provided
        if genre:
            query = query.filter(Book.genres.contains([genre]))
        if author:
            query = query.filter(Book.author.ilike(f"%{author}%"))

        # Get total count for pagination
        total = query.count()

        # Apply pagination
        books = query.offset((page - 1) * limit).limit(limit).all()

        # Convert to dictionary for JSON response
        books_data = [book._asdict() for book in books]

        response = {
            "books": books_data,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit,
            },
        }

        return jsonify(response)
    except Exception as e:
        print(e)
        return jsonify(
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                }
            }
        ), 500
    finally:
        session.close()
