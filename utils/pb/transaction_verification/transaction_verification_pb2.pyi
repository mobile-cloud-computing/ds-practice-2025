from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class PayRequest(_message.Message):
    __slots__ = ("card_nr", "order_id", "money")
    CARD_NR_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    MONEY_FIELD_NUMBER: _ClassVar[int]
    card_nr: str
    order_id: int
    money: float
    def __init__(self, card_nr: _Optional[str] = ..., order_id: _Optional[int] = ..., money: _Optional[float] = ...) -> None: ...

class PayResponse(_message.Message):
    __slots__ = ("verified", "order_id")
    VERIFIED_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    verified: bool
    order_id: int
    def __init__(self, verified: bool = ..., order_id: _Optional[int] = ...) -> None: ...
