from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BookSuggestionRequest(_message.Message):
    __slots__ = ("item", "vectorClock")
    ITEM_FIELD_NUMBER: _ClassVar[int]
    VECTORCLOCK_FIELD_NUMBER: _ClassVar[int]
    item: Item
    vectorClock: VectorClock
    def __init__(self, item: _Optional[_Union[Item, _Mapping]] = ..., vectorClock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class VectorClock(_message.Message):
    __slots__ = ("vcArray", "timestamp")
    VCARRAY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    vcArray: _containers.RepeatedScalarFieldContainer[int]
    timestamp: float
    def __init__(self, vcArray: _Optional[_Iterable[int]] = ..., timestamp: _Optional[float] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("name", "quantity")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantity: int
    def __init__(self, name: _Optional[str] = ..., quantity: _Optional[int] = ...) -> None: ...

class BookSuggestionResponse(_message.Message):
    __slots__ = ("books",)
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...

class Book(_message.Message):
    __slots__ = ("id", "title", "author", "description", "copies", "copiesAvailable", "category", "img", "price")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    COPIES_FIELD_NUMBER: _ClassVar[int]
    COPIESAVAILABLE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    IMG_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    author: str
    description: str
    copies: int
    copiesAvailable: int
    category: str
    img: str
    price: float
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., description: _Optional[str] = ..., copies: _Optional[int] = ..., copiesAvailable: _Optional[int] = ..., category: _Optional[str] = ..., img: _Optional[str] = ..., price: _Optional[float] = ...) -> None: ...
