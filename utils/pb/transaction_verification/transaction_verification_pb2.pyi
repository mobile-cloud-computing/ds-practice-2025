from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class InitOrderRequest(_message.Message):
    __slots__ = ("order_id", "order_payload_json", "vector_clock")
    class VectorClockEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    order_payload_json: str
    vector_clock: _containers.ScalarMap[str, int]
    def __init__(self, order_id: _Optional[str] = ..., order_payload_json: _Optional[str] = ..., vector_clock: _Optional[_Mapping[str, int]] = ...) -> None: ...

class InitOrderResponse(_message.Message):
    __slots__ = ("acknowledged",)
    ACKNOWLEDGED_FIELD_NUMBER: _ClassVar[int]
    acknowledged: bool
    def __init__(self, acknowledged: bool = ...) -> None: ...

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
    __slots__ = ("user", "items", "card_number", "card_expiry", "card_cvv", "order_amount", "order_id")
    USER_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CARD_EXPIRY_FIELD_NUMBER: _ClassVar[int]
    CARD_CVV_FIELD_NUMBER: _ClassVar[int]
    ORDER_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    user: UserData
    items: _containers.RepeatedCompositeFieldContainer[Item]
    card_number: str
    card_expiry: str
    card_cvv: str
    order_amount: float
    order_id: str
    def __init__(self, user: _Optional[_Union[UserData, _Mapping]] = ..., items: _Optional[_Iterable[_Union[Item, _Mapping]]] = ..., card_number: _Optional[str] = ..., card_expiry: _Optional[str] = ..., card_cvv: _Optional[str] = ..., order_amount: _Optional[float] = ..., order_id: _Optional[str] = ...) -> None: ...

class TransactionVerificationResponse(_message.Message):
    __slots__ = ("is_verified",)
    IS_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    is_verified: bool
    def __init__(self, is_verified: bool = ...) -> None: ...
