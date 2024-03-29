from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CheckoutRequest(_message.Message):
    __slots__ = ("priority", "creditcard")
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    CREDITCARD_FIELD_NUMBER: _ClassVar[int]
    priority: int
    creditcard: CreditCard
    def __init__(self, priority: _Optional[int] = ..., creditcard: _Optional[_Union[CreditCard, _Mapping]] = ...) -> None: ...

class CreditCard(_message.Message):
    __slots__ = ("number", "expirationDate", "cvv")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    CVV_FIELD_NUMBER: _ClassVar[int]
    number: str
    expirationDate: str
    cvv: str
    def __init__(self, number: _Optional[str] = ..., expirationDate: _Optional[str] = ..., cvv: _Optional[str] = ...) -> None: ...

class QueueStatus(_message.Message):
    __slots__ = ("length", "queue")
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    QUEUE_FIELD_NUMBER: _ClassVar[int]
    length: int
    queue: str
    def __init__(self, length: _Optional[int] = ..., queue: _Optional[str] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ("error", "error_message")
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    error: bool
    error_message: str
    def __init__(self, error: bool = ..., error_message: _Optional[str] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
