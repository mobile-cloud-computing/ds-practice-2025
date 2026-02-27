from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class HelloRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class HelloResponse(_message.Message):
    __slots__ = ("greeting",)
    GREETING_FIELD_NUMBER: _ClassVar[int]
    greeting: str
    def __init__(self, greeting: _Optional[str] = ...) -> None: ...

class FraudDetectionRequest(_message.Message):
    __slots__ = ("transaction_id", "purchaser_name", "purchaser_email", "credit_card_number", "billing_street", "billing_city", "billing_state", "billing_zip", "billing_country")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    PURCHASER_NAME_FIELD_NUMBER: _ClassVar[int]
    PURCHASER_EMAIL_FIELD_NUMBER: _ClassVar[int]
    CREDIT_CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    BILLING_STREET_FIELD_NUMBER: _ClassVar[int]
    BILLING_CITY_FIELD_NUMBER: _ClassVar[int]
    BILLING_STATE_FIELD_NUMBER: _ClassVar[int]
    BILLING_ZIP_FIELD_NUMBER: _ClassVar[int]
    BILLING_COUNTRY_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    purchaser_name: str
    purchaser_email: str
    credit_card_number: str
    billing_street: str
    billing_city: str
    billing_state: str
    billing_zip: str
    billing_country: str
    def __init__(self, transaction_id: _Optional[str] = ..., purchaser_name: _Optional[str] = ..., purchaser_email: _Optional[str] = ..., credit_card_number: _Optional[str] = ..., billing_street: _Optional[str] = ..., billing_city: _Optional[str] = ..., billing_state: _Optional[str] = ..., billing_zip: _Optional[str] = ..., billing_country: _Optional[str] = ...) -> None: ...

class FraudDetectionResponse(_message.Message):
    __slots__ = ("is_fraud", "reasons")
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    REASONS_FIELD_NUMBER: _ClassVar[int]
    is_fraud: bool
    reasons: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, is_fraud: bool = ..., reasons: _Optional[_Iterable[str]] = ...) -> None: ...
