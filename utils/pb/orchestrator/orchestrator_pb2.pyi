from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class VectorClock(_message.Message):
    __slots__ = ("values",)
    class ValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.ScalarMap[str, int]
    def __init__(self, values: _Optional[_Mapping[str, int]] = ...) -> None: ...

class fraudDoneRequest(_message.Message):
    __slots__ = ("order_id", "is_fraud")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    is_fraud: bool
    def __init__(self, order_id: _Optional[int] = ..., is_fraud: bool = ...) -> None: ...

class verificationDoneRequest(_message.Message):
    __slots__ = ("order_id", "payment_completed")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    PAYMENT_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    payment_completed: bool
    def __init__(self, order_id: _Optional[int] = ..., payment_completed: bool = ...) -> None: ...

class suggestionsDoneRequest(_message.Message):
    __slots__ = ("order_id", "suggestions")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    SUGGESTIONS_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    suggestions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, order_id: _Optional[int] = ..., suggestions: _Optional[_Iterable[str]] = ...) -> None: ...
