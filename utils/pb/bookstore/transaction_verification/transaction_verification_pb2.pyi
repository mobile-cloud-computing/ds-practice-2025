from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VerificationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VERIFICATION_STATUS_UNSPECIFIED: _ClassVar[VerificationStatus]
    VERIFICATION_STATUS_APPROVED: _ClassVar[VerificationStatus]
    VERIFICATION_STATUS_REJECTED: _ClassVar[VerificationStatus]
VERIFICATION_STATUS_UNSPECIFIED: VerificationStatus
VERIFICATION_STATUS_APPROVED: VerificationStatus
VERIFICATION_STATUS_REJECTED: VerificationStatus

class OrderInfo(_message.Message):
    __slots__ = ("order_id", "user_id")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    user_id: str
    def __init__(self, order_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class TransactionVerificationResponse(_message.Message):
    __slots__ = ("verification_id", "is_verified", "status", "verified_at", "rejection_reason", "risk_score")
    VERIFICATION_ID_FIELD_NUMBER: _ClassVar[int]
    IS_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERIFIED_AT_FIELD_NUMBER: _ClassVar[int]
    REJECTION_REASON_FIELD_NUMBER: _ClassVar[int]
    RISK_SCORE_FIELD_NUMBER: _ClassVar[int]
    verification_id: str
    is_verified: bool
    status: VerificationStatus
    verified_at: _timestamp_pb2.Timestamp
    rejection_reason: str
    risk_score: float
    def __init__(self, verification_id: _Optional[str] = ..., is_verified: bool = ..., status: _Optional[_Union[VerificationStatus, str]] = ..., verified_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., rejection_reason: _Optional[str] = ..., risk_score: _Optional[float] = ...) -> None: ...
