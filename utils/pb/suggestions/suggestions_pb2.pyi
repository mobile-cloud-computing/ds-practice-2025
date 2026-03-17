from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class InitOrderRequest(_message.Message):
    __slots__ = ("order_id", "order_payload_json", "vector_clock")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_PAYLOAD_JSON_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    order_payload_json: str
    vector_clock: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, order_id: _Optional[str] = ..., order_payload_json: _Optional[str] = ..., vector_clock: _Optional[_Iterable[int]] = ...) -> None: ...

class InitOrderResponse(_message.Message):
    __slots__ = ("acknowledged",)
    ACKNOWLEDGED_FIELD_NUMBER: _ClassVar[int]
    acknowledged: bool
    def __init__(self, acknowledged: bool = ...) -> None: ...

class Ack(_message.Message):
    __slots__ = ("ok",)
    OK_FIELD_NUMBER: _ClassVar[int]
    ok: bool
    def __init__(self, ok: bool = ...) -> None: ...

class DependencyNotificationRequest(_message.Message):
    __slots__ = ("order_id", "event_name", "vector_clock")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_NAME_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    event_name: str
    vector_clock: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, order_id: _Optional[str] = ..., event_name: _Optional[str] = ..., vector_clock: _Optional[_Iterable[int]] = ...) -> None: ...

class CleanupOrderRequest(_message.Message):
    __slots__ = ("order_id", "final_vector_clock")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    FINAL_VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    final_vector_clock: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, order_id: _Optional[str] = ..., final_vector_clock: _Optional[_Iterable[int]] = ...) -> None: ...

class CleanupOrderResponse(_message.Message):
    __slots__ = ("cleaned", "vc_valid", "message", "local_vector_clock")
    CLEANED_FIELD_NUMBER: _ClassVar[int]
    VC_VALID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    LOCAL_VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    cleaned: bool
    vc_valid: bool
    message: str
    local_vector_clock: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, cleaned: bool = ..., vc_valid: bool = ..., message: _Optional[str] = ..., local_vector_clock: _Optional[_Iterable[int]] = ...) -> None: ...
