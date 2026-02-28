from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TransactionRequest(_message.Message):
    __slots__ = ("card_number", "card_expiration", "card_cvv", "items", "user_name", "user_contact")
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CARD_EXPIRATION_FIELD_NUMBER: _ClassVar[int]
    CARD_CVV_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_CONTACT_FIELD_NUMBER: _ClassVar[int]
    card_number: str
    card_expiration: str
    card_cvv: str
    items: _containers.RepeatedCompositeFieldContainer[Item]
    user_name: str
    user_contact: str
    def __init__(self, card_number: _Optional[str] = ..., card_expiration: _Optional[str] = ..., card_cvv: _Optional[str] = ..., items: _Optional[_Iterable[_Union[Item, _Mapping]]] = ..., user_name: _Optional[str] = ..., user_contact: _Optional[str] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("name", "quantity")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantity: int
    def __init__(self, name: _Optional[str] = ..., quantity: _Optional[int] = ...) -> None: ...

class TransactionResponse(_message.Message):
    __slots__ = ("is_valid", "reason")
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    is_valid: bool
    reason: str
    def __init__(self, is_valid: bool = ..., reason: _Optional[str] = ...) -> None: ...
