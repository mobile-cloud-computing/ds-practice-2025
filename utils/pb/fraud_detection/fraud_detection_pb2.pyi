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
    __slots__ = ("user_name", "card_number", "item_count")
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ITEM_COUNT_FIELD_NUMBER: _ClassVar[int]
    user_name: str
    card_number: str
    item_count: int
    def __init__(self, user_name: _Optional[str] = ..., card_number: _Optional[str] = ..., item_count: _Optional[int] = ...) -> None: ...

class FraudCheckResponse(_message.Message):
    __slots__ = ("is_fraud", "message")
    IS_FRAUD_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    is_fraud: bool
    message: str
    def __init__(self, is_fraud: bool = ..., message: _Optional[str] = ...) -> None: ...
