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

class FraudRequest(_message.Message):
    __slots__ = ("order_id", "credit_card", "order_amount")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CREDIT_CARD_FIELD_NUMBER: _ClassVar[int]
    ORDER_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    credit_card: str
    order_amount: float
    def __init__(self, order_id: _Optional[str] = ..., credit_card: _Optional[str] = ..., order_amount: _Optional[float] = ...) -> None: ...

class FraudResponse(_message.Message):
    __slots__ = ("is_fraud",)
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    is_fraud: bool
    def __init__(self, is_fraud: bool = ...) -> None: ...
