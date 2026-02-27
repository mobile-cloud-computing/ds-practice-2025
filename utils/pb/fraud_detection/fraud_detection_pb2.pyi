from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class FraudDetectionRequest(_message.Message):
    __slots__ = ("transaction_id", "purchaser_email", "credit_card_number")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    PURCHASER_EMAIL_FIELD_NUMBER: _ClassVar[int]
    CREDIT_CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    purchaser_email: str
    credit_card_number: str
    def __init__(self, transaction_id: _Optional[str] = ..., purchaser_email: _Optional[str] = ..., credit_card_number: _Optional[str] = ...) -> None: ...

class FraudDetectionResponse(_message.Message):
    __slots__ = ("is_fraud", "reason")
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    is_fraud: bool
    reason: str
    def __init__(self, is_fraud: bool = ..., reason: _Optional[str] = ...) -> None: ...
