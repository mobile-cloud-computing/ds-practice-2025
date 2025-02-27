from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TransactionRequest(_message.Message):
    __slots__ = ("user_id", "items", "credit_card")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    CREDIT_CARD_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    items: _containers.RepeatedScalarFieldContainer[str]
    credit_card: str
    def __init__(self, user_id: _Optional[str] = ..., items: _Optional[_Iterable[str]] = ..., credit_card: _Optional[str] = ...) -> None: ...

class TransactionResponse(_message.Message):
    __slots__ = ("valid", "message")
    VALID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    valid: bool
    message: str
    def __init__(self, valid: bool = ..., message: _Optional[str] = ...) -> None: ...
