from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class FraudRequest(_message.Message):
    __slots__ = ("card_nr", "order_ammount")
    CARD_NR_FIELD_NUMBER: _ClassVar[int]
    ORDER_AMMOUNT_FIELD_NUMBER: _ClassVar[int]
    card_nr: str
    order_ammount: float
    def __init__(self, card_nr: _Optional[str] = ..., order_ammount: _Optional[float] = ...) -> None: ...

class FraudResponse(_message.Message):
    __slots__ = ("is_fraud",)
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    is_fraud: bool
    def __init__(self, is_fraud: bool = ...) -> None: ...
