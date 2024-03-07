from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class FraudRequest(_message.Message):
    __slots__ = ("name", "email", "address", "phone", "ssn")
    NAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    PHONE_FIELD_NUMBER: _ClassVar[int]
    SSN_FIELD_NUMBER: _ClassVar[int]
    name: str
    email: str
    address: str
    phone: str
    ssn: str
    def __init__(self, name: _Optional[str] = ..., email: _Optional[str] = ..., address: _Optional[str] = ..., phone: _Optional[str] = ..., ssn: _Optional[str] = ...) -> None: ...

class FraudResponse(_message.Message):
    __slots__ = ("isFraud", "message")
    ISFRAUD_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    isFraud: bool
    message: str
    def __init__(self, isFraud: bool = ..., message: _Optional[str] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: str
    def __init__(self, status: _Optional[str] = ...) -> None: ...
