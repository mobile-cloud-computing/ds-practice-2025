from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SuggestionsRequest(_message.Message):
    __slots__ = ("user_name", "item_count")
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    ITEM_COUNT_FIELD_NUMBER: _ClassVar[int]
    user_name: str
    item_count: int
    def __init__(self, user_name: _Optional[str] = ..., item_count: _Optional[int] = ...) -> None: ...

class SuggestedBook(_message.Message):
    __slots__ = ("bookId", "title", "author")
    BOOKID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    bookId: str
    title: str
    author: str
    def __init__(self, bookId: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ...) -> None: ...

class SuggestionsResponse(_message.Message):
    __slots__ = ("books",)
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    books: _containers.RepeatedCompositeFieldContainer[SuggestedBook]
    def __init__(self, books: _Optional[_Iterable[_Union[SuggestedBook, _Mapping]]] = ...) -> None: ...
