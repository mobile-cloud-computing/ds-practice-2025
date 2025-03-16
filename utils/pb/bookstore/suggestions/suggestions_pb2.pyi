from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class BookRequest(_message.Message):
    __slots__ = ("book_name",)
    BOOK_NAME_FIELD_NUMBER: _ClassVar[int]
    book_name: str
    def __init__(self, book_name: _Optional[str] = ...) -> None: ...

class SuggestionsResponse(_message.Message):
    __slots__ = ("suggestions",)
    SUGGESTIONS_FIELD_NUMBER: _ClassVar[int]
    suggestions: str
    def __init__(self, suggestions: _Optional[str] = ...) -> None: ...
