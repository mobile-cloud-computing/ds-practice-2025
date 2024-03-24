from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TransactionVerificationRequest(_message.Message):
    __slots__ = ("user", "creditCard", "item", "vectorClock")
    USER_FIELD_NUMBER: _ClassVar[int]
    CREDITCARD_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    VECTORCLOCK_FIELD_NUMBER: _ClassVar[int]
    user: User
    creditCard: CreditCard
    item: Item
    vectorClock: VectorClock
    def __init__(self, user: _Optional[_Union[User, _Mapping]] = ..., creditCard: _Optional[_Union[CreditCard, _Mapping]] = ..., item: _Optional[_Union[Item, _Mapping]] = ..., vectorClock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ("name", "contact")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    name: str
    contact: str
    def __init__(self, name: _Optional[str] = ..., contact: _Optional[str] = ...) -> None: ...

class CreditCard(_message.Message):
    __slots__ = ("number", "expirationDate", "cvv")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    CVV_FIELD_NUMBER: _ClassVar[int]
    number: str
    expirationDate: str
    cvv: str
    def __init__(self, number: _Optional[str] = ..., expirationDate: _Optional[str] = ..., cvv: _Optional[str] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("name", "quantity")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantity: int
    def __init__(self, name: _Optional[str] = ..., quantity: _Optional[int] = ...) -> None: ...

class VectorClock(_message.Message):
    __slots__ = ("vcArray", "timestamp")
    VCARRAY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    vcArray: _containers.RepeatedScalarFieldContainer[int]
    timestamp: float
    def __init__(self, vcArray: _Optional[_Iterable[int]] = ..., timestamp: _Optional[float] = ...) -> None: ...

class TransactionVerificationResponse(_message.Message):
    __slots__ = ("is_valid",)
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    is_valid: bool
    def __init__(self, is_valid: bool = ...) -> None: ...
