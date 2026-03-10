from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class VerifyRequest(_message.Message):
    __slots__ = ("user_name", "contact", "card_number", "street", "city", "state", "zip_code", "country", "shipping_method", "terms_accepted")
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    CARD_NUMBER_FIELD_NUMBER: _ClassVar[int]
    STREET_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ZIP_CODE_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    SHIPPING_METHOD_FIELD_NUMBER: _ClassVar[int]
    TERMS_ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    user_name: str
    contact: str
    card_number: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str
    shipping_method: str
    terms_accepted: bool
    def __init__(self, user_name: _Optional[str] = ..., contact: _Optional[str] = ..., card_number: _Optional[str] = ..., street: _Optional[str] = ..., city: _Optional[str] = ..., state: _Optional[str] = ..., zip_code: _Optional[str] = ..., country: _Optional[str] = ..., shipping_method: _Optional[str] = ..., terms_accepted: bool = ...) -> None: ...

class VerifyResponse(_message.Message):
    __slots__ = ("is_valid",)
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    is_valid: bool
    def __init__(self, is_valid: bool = ...) -> None: ...
