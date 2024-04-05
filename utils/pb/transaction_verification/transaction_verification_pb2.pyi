from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TransactionRequest(_message.Message):
    __slots__ = ("cardNumber", "expirationDate", "cvv", "vector_clock")
    CARDNUMBER_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    CVV_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    cardNumber: str
    expirationDate: str
    cvv: str
    vector_clock: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, cardNumber: _Optional[str] = ..., expirationDate: _Optional[str] = ..., cvv: _Optional[str] = ..., vector_clock: _Optional[_Iterable[int]] = ...) -> None: ...

class TransactionResponse(_message.Message):
    __slots__ = ("transactionId", "vector_clock")
    TRANSACTIONID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    transactionId: str
    vector_clock: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, transactionId: _Optional[str] = ..., vector_clock: _Optional[_Iterable[int]] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: str
    def __init__(self, status: _Optional[str] = ...) -> None: ...
