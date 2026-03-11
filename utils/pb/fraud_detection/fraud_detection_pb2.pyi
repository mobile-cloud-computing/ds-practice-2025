from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class InitOrderRequest(_message.Message):
    __slots__ = ("order_id", "order_payload_json", "vector_clock")
    class VectorClockEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    order_payload_json: str
    vector_clock: _containers.ScalarMap[str, int]
    def __init__(self, order_id: _Optional[str] = ..., order_payload_json: _Optional[str] = ..., vector_clock: _Optional[_Mapping[str, int]] = ...) -> None: ...

class InitOrderResponse(_message.Message):
    __slots__ = ("acknowledged",)
    ACKNOWLEDGED_FIELD_NUMBER: _ClassVar[int]
    acknowledged: bool
    def __init__(self, acknowledged: bool = ...) -> None: ...

class FraudDetectionRequest(_message.Message):
    __slots__ = ("card_number", "order_amount", "order_id")
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ORDER_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    card_number: str
    order_amount: float
    order_id: str
    def __init__(self, card_number: _Optional[str] = ..., order_amount: _Optional[float] = ..., order_id: _Optional[str] = ...) -> None: ...

class FraudDetectionResponse(_message.Message):
    __slots__ = ("is_fraud",)
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    is_fraud: bool
    def __init__(self, is_fraud: bool = ...) -> None: ...
