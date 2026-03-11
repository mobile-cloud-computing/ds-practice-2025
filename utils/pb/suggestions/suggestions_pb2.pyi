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

class SuggestRequest(_message.Message):
    __slots__ = ("order_id",)
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    def __init__(self, order_id: _Optional[str] = ...) -> None: ...

class Book(_message.Message):
    __slots__ = ("title", "author")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    title: str
    author: str
    def __init__(self, title: _Optional[str] = ..., author: _Optional[str] = ...) -> None: ...

class SuggestResponse(_message.Message):
    __slots__ = ("suggested_books",)
    SUGGESTED_BOOKS_FIELD_NUMBER: _ClassVar[int]
    suggested_books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, suggested_books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...
