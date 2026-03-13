from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class HelloRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class HelloResponse(_message.Message):
    __slots__ = ("greeting",)
    GREETING_FIELD_NUMBER: _ClassVar[int]
    greeting: str
    def __init__(self, greeting: _Optional[str] = ...) -> None: ...

class FraudCheckRequest(_message.Message):
    __slots__ = ("order_id", "user_name", "card_number", "item_count")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ITEM_COUNT_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    user_name: str
    card_number: str
    item_count: int
    def __init__(self, order_id: _Optional[str] = ..., user_name: _Optional[str] = ..., card_number: _Optional[str] = ..., item_count: _Optional[int] = ...) -> None: ...

class FraudCheckResponse(_message.Message):
    __slots__ = ("is_fraud", "message", "failed")
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    FAILED_FIELD_NUMBER: _ClassVar[int]
    is_fraud: bool
    message: str
    failed: bool
    def __init__(self, is_fraud: bool = ..., message: _Optional[str] = ..., failed: bool = ...) -> None: ...

class TriggerRequest(_message.Message):
    __slots__ = ("order_id", "event_type")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    event_type: str
    def __init__(self, order_id: _Optional[str] = ..., event_type: _Optional[str] = ...) -> None: ...

class VectorClockRequest(_message.Message):
    __slots__ = ("order_id",)
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    def __init__(self, order_id: _Optional[str] = ...) -> None: ...

class VectorClockResponse(_message.Message):
    __slots__ = ("fraud_detection", "fd_event_d", "fd_event_e", "transaction_verification", "tv_event_a", "tv_event_b", "tv_event_c", "suggestions")
    FRAUD_DETECTION_FIELD_NUMBER: _ClassVar[int]
    FD_EVENT_D_FIELD_NUMBER: _ClassVar[int]
    FD_EVENT_E_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_VERIFICATION_FIELD_NUMBER: _ClassVar[int]
    TV_EVENT_A_FIELD_NUMBER: _ClassVar[int]
    TV_EVENT_B_FIELD_NUMBER: _ClassVar[int]
    TV_EVENT_C_FIELD_NUMBER: _ClassVar[int]
    SUGGESTIONS_FIELD_NUMBER: _ClassVar[int]
    fraud_detection: int
    fd_event_d: int
    fd_event_e: int
    transaction_verification: int
    tv_event_a: int
    tv_event_b: int
    tv_event_c: int
    suggestions: int
    def __init__(self, fraud_detection: _Optional[int] = ..., fd_event_d: _Optional[int] = ..., fd_event_e: _Optional[int] = ..., transaction_verification: _Optional[int] = ..., tv_event_a: _Optional[int] = ..., tv_event_b: _Optional[int] = ..., tv_event_c: _Optional[int] = ..., suggestions: _Optional[int] = ...) -> None: ...

class ClearOrderRequest(_message.Message):
    __slots__ = ("order_id", "final_vc_fraud_detection", "final_vc_fd_event_d", "final_vc_fd_event_e", "final_vc_transaction_verification", "final_vc_tv_event_a", "final_vc_tv_event_b", "final_vc_tv_event_c", "final_vc_suggestions")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_FRAUD_DETECTION_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_FD_EVENT_D_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_FD_EVENT_E_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_TRANSACTION_VERIFICATION_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_TV_EVENT_A_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_TV_EVENT_B_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_TV_EVENT_C_FIELD_NUMBER: _ClassVar[int]
    FINAL_VC_SUGGESTIONS_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    final_vc_fraud_detection: int
    final_vc_fd_event_d: int
    final_vc_fd_event_e: int
    final_vc_transaction_verification: int
    final_vc_tv_event_a: int
    final_vc_tv_event_b: int
    final_vc_tv_event_c: int
    final_vc_suggestions: int
    def __init__(self, order_id: _Optional[str] = ..., final_vc_fraud_detection: _Optional[int] = ..., final_vc_fd_event_d: _Optional[int] = ..., final_vc_fd_event_e: _Optional[int] = ..., final_vc_transaction_verification: _Optional[int] = ..., final_vc_tv_event_a: _Optional[int] = ..., final_vc_tv_event_b: _Optional[int] = ..., final_vc_tv_event_c: _Optional[int] = ..., final_vc_suggestions: _Optional[int] = ...) -> None: ...

class ClearOrderResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...
