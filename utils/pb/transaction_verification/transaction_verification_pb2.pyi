from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VectorClock(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, values: _Optional[_Iterable[int]] = ...) -> None: ...

class InitRequest(_message.Message):
    __slots__ = ("order_id", "item_json")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ITEM_JSON_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    item_json: str
    def __init__(self, order_id: _Optional[str] = ..., item_json: _Optional[str] = ...) -> None: ...

class ClockUpdateRequest(_message.Message):
    __slots__ = ("order_id", "clock")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    clock: VectorClock
    def __init__(self, order_id: _Optional[str] = ..., clock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class VerifyRequest(_message.Message):
    __slots__ = ("order_id", "user_name", "contact", "card_number", "street", "city", "state", "zip_code", "country", "shipping_method", "terms_accepted")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    STREET_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ZIP_CODE_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    SHIPPING_METHOD_FIELD_NUMBER: _ClassVar[int]
    TERMS_ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    user_name: str
    contact: str
    card_number: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str
    shipping_method: str
    terms_accepted: bool
    def __init__(self, order_id: _Optional[str] = ..., user_name: _Optional[str] = ..., contact: _Optional[str] = ..., card_number: _Optional[str] = ..., street: _Optional[str] = ..., city: _Optional[str] = ..., state: _Optional[str] = ..., zip_code: _Optional[str] = ..., country: _Optional[str] = ..., shipping_method: _Optional[str] = ..., terms_accepted: bool = ...) -> None: ...

class VerifyResponse(_message.Message):
    __slots__ = ("is_valid",)
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    is_valid: bool
    def __init__(self, is_valid: bool = ...) -> None: ...
