from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class SuggestRequest(_message.Message):
    __slots__ = ("ordered_books",)
    ORDERED_BOOKS_FIELD_NUMBER: _ClassVar[int]
    ordered_books: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ordered_books: _Optional[_Iterable[str]] = ...) -> None: ...

class SuggestResponse(_message.Message):
    __slots__ = ("suggested_books",)
    SUGGESTED_BOOKS_FIELD_NUMBER: _ClassVar[int]
    suggested_books: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, suggested_books: _Optional[_Iterable[str]] = ...) -> None: ...
