from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SuggestionInitRequest(_message.Message):
    __slots__ = ("order_id", "book_tokens", "user_id")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    BOOK_TOKENS_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    book_tokens: _containers.RepeatedScalarFieldContainer[str]
    user_id: str
    def __init__(self, order_id: _Optional[str] = ..., book_tokens: _Optional[_Iterable[str]] = ..., user_id: _Optional[str] = ...) -> None: ...

class SuggestionInitResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class RecommendationRequest(_message.Message):
    __slots__ = ("user_id", "limit", "book_tokens", "order_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    BOOK_TOKENS_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    limit: int
    book_tokens: _containers.RepeatedScalarFieldContainer[str]
    order_id: str
    def __init__(self, user_id: _Optional[str] = ..., limit: _Optional[int] = ..., book_tokens: _Optional[_Iterable[str]] = ..., order_id: _Optional[str] = ...) -> None: ...

class RecommendationResponse(_message.Message):
    __slots__ = ("recommendations",)
    RECOMMENDATIONS_FIELD_NUMBER: _ClassVar[int]
    recommendations: _containers.RepeatedCompositeFieldContainer[Recommendation]
    def __init__(self, recommendations: _Optional[_Iterable[_Union[Recommendation, _Mapping]]] = ...) -> None: ...

class Recommendation(_message.Message):
    __slots__ = ("book", "confidence_score", "reason")
    BOOK_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_SCORE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    book: Book
    confidence_score: float
    reason: str
    def __init__(self, book: _Optional[_Union[Book, _Mapping]] = ..., confidence_score: _Optional[float] = ..., reason: _Optional[str] = ...) -> None: ...

class Book(_message.Message):
    __slots__ = ("id", "title", "author", "description", "genres", "publish_date")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    GENRES_FIELD_NUMBER: _ClassVar[int]
    PUBLISH_DATE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    author: str
    description: str
    genres: _containers.RepeatedScalarFieldContainer[str]
    publish_date: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., description: _Optional[str] = ..., genres: _Optional[_Iterable[str]] = ..., publish_date: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
