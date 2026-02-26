from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UserData(_message.Message):
    __slots__ = ("name", "email", "address")
    NAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    name: str
    email: str
    address: str
    def __init__(self, name: _Optional[str] = ..., email: _Optional[str] = ..., address: _Optional[str] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("name", "quantity")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantity: float
    def __init__(self, name: _Optional[str] = ..., quantity: _Optional[float] = ...) -> None: ...

class TransactionVerificationRequest(_message.Message):
    __slots__ = ("user", "items", "card_number", "card_expiry", "card_cvv", "order_amount")
    USER_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CARD_EXPIRY_FIELD_NUMBER: _ClassVar[int]
    CARD_CVV_FIELD_NUMBER: _ClassVar[int]
    ORDER_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    user: UserData
    items: _containers.RepeatedCompositeFieldContainer[Item]
    card_number: str
    card_expiry: str
    card_cvv: str
    order_amount: float
    def __init__(self, user: _Optional[_Union[UserData, _Mapping]] = ..., items: _Optional[_Iterable[_Union[Item, _Mapping]]] = ..., card_number: _Optional[str] = ..., card_expiry: _Optional[str] = ..., card_cvv: _Optional[str] = ..., order_amount: _Optional[float] = ...) -> None: ...

class TransactionVerificationResponse(_message.Message):
    __slots__ = ("is_verified",)
    IS_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    is_verified: bool
    def __init__(self, is_verified: bool = ...) -> None: ...
