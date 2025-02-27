from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CheckOrderRequest(_message.Message):
    __slots__ = ("totalAmount",)
    TOTALAMOUNT_FIELD_NUMBER: _ClassVar[int]
    totalAmount: float
    def __init__(self, totalAmount: _Optional[float] = ...) -> None: ...

class CheckOrderResponse(_message.Message):
    __slots__ = ("isFraud", "reason")
    ISFRAUD_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    isFraud: bool
    reason: str
    def __init__(self, isFraud: bool = ..., reason: _Optional[str] = ...) -> None: ...
