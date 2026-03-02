from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Book(_message.Message):
    __slots__ = ("bookId", "title", "author")
    BOOKID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    bookId: str
    title: str
    author: str
    def __init__(self, bookId: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ...) -> None: ...

class SuggestRequest(_message.Message):
    __slots__ = ("ordered_books",)
    ORDERED_BOOKS_FIELD_NUMBER: _ClassVar[int]
    ordered_books: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ordered_books: _Optional[_Iterable[str]] = ...) -> None: ...

class SuggestResponse(_message.Message):
    __slots__ = ("suggested_books",)
    SUGGESTED_BOOKS_FIELD_NUMBER: _ClassVar[int]
    suggested_books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, suggested_books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...
