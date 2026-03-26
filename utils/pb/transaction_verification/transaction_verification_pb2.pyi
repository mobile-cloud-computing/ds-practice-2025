from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

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

class OdrerData(_message.Message):
    __slots__ = ("card_nr", "order_ammount")
    CARD_NR_FIELD_NUMBER: _ClassVar[int]
    ORDER_AMMOUNT_FIELD_NUMBER: _ClassVar[int]
    card_nr: str
    order_ammount: float
    def __init__(self, card_nr: _Optional[str] = ..., order_ammount: _Optional[float] = ...) -> None: ...

class InitRequest(_message.Message):
    __slots__ = ("order_id", "orderData")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDERDATA_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    orderData: OdrerData
    def __init__(self, order_id: _Optional[int] = ..., orderData: _Optional[_Union[OdrerData, _Mapping]] = ...) -> None: ...

class CheckCardRequest(_message.Message):
    __slots__ = ("order_id", "clock")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    clock: VectorClock
    def __init__(self, order_id: _Optional[int] = ..., clock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class CheckMoneyRequest(_message.Message):
    __slots__ = ("order_id", "clock")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    clock: VectorClock
    def __init__(self, order_id: _Optional[int] = ..., clock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class StartPaymentRequest(_message.Message):
    __slots__ = ("order_id", "clock")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    clock: VectorClock
    def __init__(self, order_id: _Optional[int] = ..., clock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...
