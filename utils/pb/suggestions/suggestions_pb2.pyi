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

class OrderData(_message.Message):
    __slots__ = ("order_id", "user_name", "user_contact", "card_number", "expiration_date", "cvv", "item_count", "terms_accepted")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_CONTACT_FIELD_NUMBER: _ClassVar[int]
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    EXPIRATION_DATE_FIELD_NUMBER: _ClassVar[int]
    CVV_FIELD_NUMBER: _ClassVar[int]
    ITEM_COUNT_FIELD_NUMBER: _ClassVar[int]
    TERMS_ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    user_name: str
    user_contact: str
    card_number: str
    expiration_date: str
    cvv: str
    item_count: int
    terms_accepted: bool
    def __init__(self, order_id: _Optional[str] = ..., user_name: _Optional[str] = ..., user_contact: _Optional[str] = ..., card_number: _Optional[str] = ..., expiration_date: _Optional[str] = ..., cvv: _Optional[str] = ..., item_count: _Optional[int] = ..., terms_accepted: bool = ...) -> None: ...

class InitOrderRequest(_message.Message):
    __slots__ = ("order",)
    ORDER_FIELD_NUMBER: _ClassVar[int]
    order: OrderData
    def __init__(self, order: _Optional[_Union[OrderData, _Mapping]] = ...) -> None: ...

class EventRequest(_message.Message):
    __slots__ = ("order_id", "vc")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    VC_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    vc: VectorClock
    def __init__(self, order_id: _Optional[str] = ..., vc: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class EventResponse(_message.Message):
    __slots__ = ("success", "message", "vc")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    VC_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    vc: VectorClock
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., vc: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class SuggestedBook(_message.Message):
    __slots__ = ("bookId", "title", "author")
    BOOKID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    bookId: str
    title: str
    author: str
    def __init__(self, bookId: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ...) -> None: ...

class SuggestionsEventResponse(_message.Message):
    __slots__ = ("success", "message", "vc", "books")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    VC_FIELD_NUMBER: _ClassVar[int]
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    vc: VectorClock
    books: _containers.RepeatedCompositeFieldContainer[SuggestedBook]
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., vc: _Optional[_Union[VectorClock, _Mapping]] = ..., books: _Optional[_Iterable[_Union[SuggestedBook, _Mapping]]] = ...) -> None: ...

class ClearOrderRequest(_message.Message):
    __slots__ = ("order_id", "final_vc")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    final_vc: VectorClock
    def __init__(self, order_id: _Optional[str] = ..., final_vc: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...
